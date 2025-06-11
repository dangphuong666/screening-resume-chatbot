"""
Main Application Server

This Flask application provides an API for document processing and chat functionality.
It uses a vector database for semantic search and the Nebius API for chat responses.
"""

import os
import requests
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
import dotenv
from utils.document_processor import load_cv, create_db, load_db

# Initialize environment
print("Current working directory:", os.getcwd())
print("Looking for .env file in:", os.path.abspath('.env'))
dotenv.load_dotenv()

# Load and validate API key
print("Environment variables:", os.environ.get('NEBIUS_API_KEY'))

NEBIUS_API_KEY = os.getenv('NEBIUS_API_KEY')
if not NEBIUS_API_KEY:
    raise RuntimeError('NEBIUS_API_KEY environment variable not set. Please add it to your .env file.')

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
DB_FOLDER = 'chroma_db'
ALLOWED_EXTENSIONS = {'pdf'}

for folder in [UPLOAD_FOLDER, DB_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

API_URL = "https://api.studio.nebius.ai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {NEBIUS_API_KEY}",
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return None

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        # Load the vector database
        db = load_db(DB_FOLDER)
        
        # Search for relevant document chunks
        search_results = db.similarity_search(user_message, k=3)
        
        # Track matched files and create context
        context = "\n\nRelevant context from documents:\n"
        matched_files = set()  # Use set to avoid duplicates
        
        for i, doc in enumerate(search_results, 1):
            context += f"\nDocument {i}:\n{doc.page_content}\n"
            if 'filename' in doc.metadata:
                matched_files.add(doc.metadata['filename'])
        
        # Format the prompt with JD and CV structure
        prompt_template = """You are an AI assistant helping recruiters evaluate candidates.

Below is a Job Description (JD) and a Candidate's Resume (CV).

---

[Job Description]
{jd}

---

[Candidate CV]
{cv}

---

Please answer the following:

1. Suitability Score (0–100)
2. Key Strengths
3. Missing or Weak Areas
4. Final Verdict: strong match / possible fit / not a good match

Return output in JSON format with the following structure:
{{
    "suitability_score": number,
    "key_strengths": string[],
    "missing_areas": string[],
    "final_verdict": "strong match" | "possible fit" | "not a good match",
    "explanation": string
}}"""

        # Combine user message (JD) with context (CV)
        full_message = prompt_template.format(
            jd=user_message,
            cv=context
        )
        
        response = query({
            "messages": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are an AI assistant analyzing job descriptions and resumes. Always respond in the requested JSON format."
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": full_message
                        }
                    ]
                }
            ],
            "model": "mistralai/Mistral-Small-3.1-24B-Instruct-2503"
        })

        if "choices" in response:
            bot_response = response["choices"][0]["message"]["content"]
            return jsonify({
                "response": bot_response,
                "matched_files": list(matched_files)  # Convert set to list for JSON serialization
            })
        else:
            return jsonify({"error": "Invalid API response", "details": response}), 500

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    try:
        print("Received upload request")
        # Check if the post request has the file part
        if 'file' not in request.files:
            print("No file found in request.files")
            print("Available files:", list(request.files.keys()))
            print("Request headers:", dict(request.headers))
            return jsonify({"error": "No file found in request"}), 400
        
        file = request.files['file']
        print(f"Received file: {file.filename}")
        print(f"File content type: {file.content_type}")
        
        if file.filename == '':
            print("Empty filename received")
            return jsonify({"error": "No selected file"}), 400
        
        if not allowed_file(file.filename):
            print(f"Invalid file type: {file.filename}")
            return jsonify({"error": f"Invalid file type. Only PDF files are allowed. Received: {file.content_type}"}), 400

        print("Creating temporary file...")
        # Create a temporary file and process it
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            print(f"Temporary file created at: {temp_file.name}")
            file.save(temp_file.name)
            print("File saved to temporary location")
            
            # Save the file to uploads folder
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(upload_path, 'wb') as upload_file:
                with open(temp_file.name, 'rb') as tmp:
                    upload_file.write(tmp.read())
            print(f"File saved to uploads folder: {upload_path}")

            # Load and split the document
            print("Loading and splitting document...")
            documents = load_cv(temp_file.name)
            print(f"Document loaded and split into {len(documents) if documents else 0} chunks")
            
            try:
                # Try to load existing database or create new one
                print("Loading existing database...")
                db = load_db(DB_FOLDER)
                print("Adding documents to existing database...")
                db.add_documents(documents)
                print("Documents added successfully")
            except Exception as e:
                print(f"Error loading existing database: {str(e)}")
                print("Creating new database...")
                db = create_db(documents, DB_FOLDER)
                print("New database created successfully")
            
            # Clean up the temporary file
            print("Cleaning up temporary file...")
            os.unlink(temp_file.name)
            print("Temporary file deleted")
            
            return jsonify({
                "message": "File uploaded and processed successfully",
                "filename": file.filename
            })

    except Exception as e:
        print(f"Error in upload_pdf: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/get-pdf/<filename>', methods=['GET'])
def get_pdf(filename):
    try:
        # Ensure the filename is secure
        filename = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
            
        # Send the file with proper headers
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)