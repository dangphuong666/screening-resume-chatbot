import os
import requests
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
import dotenv

print("Current working directory:", os.getcwd())
print("Looking for .env file in:", os.path.abspath('.env'))
dotenv.load_dotenv()

print("Environment variables:", os.environ.get('NEBIUS_API_KEY'))

NEBIUS_API_KEY = os.getenv('NEBIUS_API_KEY')
#NEBIUS_API_KEY = os.getenv('eyJhbGciOiJIUzI1NiIsImtpZCI6IlV6SXJWd1h0dnprLVRvdzlLZWstc0M1akptWXBvX1VaVkxUZlpnMDRlOFUiLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJnaXRodWJ8MTA4Njc2NjMwIiwic2NvcGUiOiJvcGVuaWQgb2ZmbGluZV9hY2Nlc3MiLCJpc3MiOiJhcGlfa2V5X2lzc3VlciIsImF1ZCI6WyJodHRwczovL25lYml1cy1pbmZlcmVuY2UuZXUuYXV0aDAuY29tL2FwaS92Mi8iXSwiZXhwIjoxOTA3Mjk4MjkzLCJ1dWlkIjoiNWNkZDJiZTktNjI5ZC00N2UxLWI2NjItOGJmZDQxMjA3YzRiIiwibmFtZSI6ImRlbW8xIiwiZXhwaXJlc19hdCI6IjIwMzAtMDYtMTBUMDU6MDQ6NTMrMDAwMCJ9.44FXdIV62YNLRiPvljeeXlc65nLys9njamVbixu_JK4')
if not NEBIUS_API_KEY:
    raise RuntimeError('NEBIUS_API_KEY environment variable not set. Please add it to your .env file.')

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
        pending_files = data.get('pendingFiles', [])
        
        # Prepare context from pending files if any
        files_context = ""
        if pending_files:
            files_context = "\n\nContext from uploaded PDF files:\n"
            for idx, file in enumerate(pending_files, 1):
                files_context += f"\nFile {idx}: {file['name']}\nContent: {file['content']}\n"
        
        # Combine user message with files context
        full_message = f"{user_message}{files_context}"
        
        response = query({
            "messages": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are analyzing user messages and PDF contents. If PDF content is provided, incorporate relevant information from the PDFs in your response."
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
            return jsonify({"response": bot_response})
        else:
            return jsonify({"error": "Invalid API response", "details": response}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            extracted_text = extract_text_from_pdf(temp_file.name)
            os.unlink(temp_file.name)  # Delete the temporary file

        if not extracted_text:
            return jsonify({"error": "Failed to extract text from PDF"}), 500

        # Process the extracted text with the AI model
        response = query({
            "messages": [
                {
                    "role": "system",
                    "content": "You are analyzing a PDF document. Please provide a summary and be ready to answer questions about its content."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Here's the content of the PDF document:\n\n{extracted_text}\n\nPlease provide a brief summary of this document."
                        }
                    ]
                }
            ],
            "model": "mistralai/Mistral-Small-3.1-24B-Instruct-2503"
        })

        if "choices" in response:
            summary = response["choices"][0]["message"]["content"]
            return jsonify({
                "success": True,
                "summary": summary,
                "text": extracted_text
            })
        else:
            return jsonify({"error": "Failed to analyze PDF content"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)