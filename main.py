"""
Main Application Server

This Flask application provides an API for document processing and chat functionality.
"""

# Initialize environment and database path
import os
from openai import OpenAI
import tempfile
from flask import Flask, request, jsonify, send_file, redirect, url_for, session, send_from_directory
from flask_cors import CORS
from PyPDF2 import PdfReader
import json
from werkzeug.utils import secure_filename
import dotenv
from utils.document_processor import load_cv, create_db, load_db
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from models import db, User, Chat
from datetime import timedelta
import sqlite3

# Set OAuth 2.0 to work with http://localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Ensure instance directory exists
instance_path = os.path.join(os.getcwd(), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)
    print(f"Created instance directory at {instance_path}")

# Initialize environment
print("Current working directory:", os.getcwd())
print("Looking for .env file in:", os.path.abspath('.env'))
dotenv.load_dotenv()

# Load and validate API keys
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
NEBIUS_API_KEY = os.getenv('NEBIUS_API_KEY')

if not NEBIUS_API_KEY:
    raise ValueError("Missing Nebius API key")

# Configure OpenAI client for Nebius API
client = OpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=NEBIUS_API_KEY
)

app = Flask(__name__, static_folder='frontend/build', static_url_path='')

# Configure CORS with specific origin
CORS(app, 
     resources={r"/*": {
         "origins": "http://localhost:3000",  # String instead of list for specific origin
         "methods": ["GET", "POST", "OPTIONS"],
         "supports_credentials": True,
         "allow_headers": ["Content-Type", "Authorization"],
         "expose_headers": ["Content-Type", "Authorization"],
         "allow_credentials": True  # Explicitly allow credentials
     }},
     supports_credentials=True)

# Configure Flask app
app.config.update(
    SECRET_KEY='dev-secret-key-change-in-production',  # Use a constant key for development
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    SESSION_REFRESH_EACH_REQUEST=True,
    SESSION_COOKIE_DOMAIN=None,  # Allow cookies to be set for all subdomains
    SESSION_COOKIE_PATH='/',
    REMEMBER_COOKIE_DURATION=timedelta(days=1),
    REMEMBER_COOKIE_SECURE=False,  # Set to True in production
    REMEMBER_COOKIE_HTTPONLY=True,
    SQLALCHEMY_DATABASE_URI='sqlite:///app.db',  # Simplified database path
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER='uploads',
    DB_FOLDER='chroma_db'
)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create required folders and database
with app.app_context():
    print("Initializing database and required folders...")
    
    # Ensure instance directory exists with correct permissions
    if not os.path.exists(instance_path):
        try:
            os.makedirs(instance_path, mode=0o755)
            print(f"Created instance directory at {instance_path}")
        except Exception as e:
            print(f"Error creating instance directory: {str(e)}")
            raise

    # Ensure database file exists with correct permissions
    db_path = os.path.join(instance_path, 'app.db')
    if not os.path.exists(db_path):
        try:
            # Create empty file
            open(db_path, 'a').close()
            # Set permissions to 664 (rw-rw-r--)
            os.chmod(db_path, 0o664)
            print(f"Created database file at {db_path}")
        except Exception as e:
            print(f"Error creating database file: {str(e)}")
            raise

    # Create required folders
    for folder in [app.config['UPLOAD_FOLDER'], app.config['DB_FOLDER']]:
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, mode=0o755)
                print(f"Created folder: {folder}")
            except Exception as e:
                print(f"Error creating folder {folder}: {str(e)}")

    # Create database tables
    print("Creating database tables...")
    try:
        # Verify database file is accessible
        if not os.access(db_path, os.W_OK):
            print(f"Warning: No write access to database file: {db_path}")
            # Try to fix permissions
            os.chmod(db_path, 0o664)
            print("Updated database file permissions")

        # Create all tables
        db.create_all()
        print("Database tables created successfully")
        
        # Verify database tables
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print("Existing tables:", tables)
            
    except Exception as e:
        print("Error during database initialization:", str(e))
        print("Exception type:", type(e).__name__)
        print("Database file path:", db_path)
        print("Database file exists:", os.path.exists(db_path))
        print("Database file permissions:", oct(os.stat(db_path).st_mode & 0o777))
        print("Current user/group:", os.getuid(), os.getgid())
        import traceback
        traceback.print_exc()
        raise

# Ensure session is accessible
app.config['SESSION_COOKIE_PATH'] = '/'

ALLOWED_EXTENSIONS = {'pdf'}

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

# Google OAuth routes
@app.route('/login')
def login():
    print("\n=== Login Route Debug ===")
    print("1. Login route accessed")
    
    # Check credentials
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: Missing Google OAuth credentials")
        return redirect('http://localhost:3000?error=missing_credentials')
        
    try:
        # Clear any existing session data
        session.clear()
        print("2. Session cleared")
        
        # Define scopes explicitly with full URLs
        SCOPES = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        
        # Initialize the OAuth 2.0 flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:5000/login/callback"],
                    "javascript_origins": ["http://localhost:3000"]
                }
            },
            scopes=SCOPES
        )
        
        # Set the redirect_uri explicitly
        flow.redirect_uri = "http://localhost:5000/login/callback"
        print("3. Flow initialized with redirect URI:", flow.redirect_uri)
        print("4. Using scopes:", SCOPES)
        
        # Generate the authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state and scopes in session
        session['state'] = state
        session['requested_scopes'] = SCOPES
        print("5. State stored in session:", state)
        print("6. Current session data:", dict(session))
        print("7. Redirecting to:", authorization_url)
        
        return redirect(authorization_url)
        
    except Exception as e:
        print(f"Error in login route: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect('http://localhost:3000?error=login_failed&details=' + str(e))

@app.route('/login/callback')
def callback():
    print("\n=== OAuth Callback Debug ===")
    print("1. Request URL:", request.url)
    print("2. Query Parameters:", dict(request.args))
    print("3. Session before processing:", dict(session))
    print("4. Cookies:", dict(request.cookies))
    
    try:
        # Check for OAuth error response
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', 'No description provided')
            print(f"OAuth Error: {error} - {error_description}")
            return redirect(f'http://localhost:3000?error=oauth_{error}')

        # Get the authorization code
        code = request.args.get('code')
        if not code:
            print("No authorization code received!")
            return redirect('http://localhost:3000?error=no_auth_code')

        # Initialize flow with the same scopes used in login
        SCOPES = session.get('requested_scopes', [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ])

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:5000/login/callback"],
                    "javascript_origins": ["http://localhost:3000"]
                }
            },
            scopes=SCOPES
        )
        
        flow.redirect_uri = "http://localhost:5000/login/callback"
        print("5. Flow initialized with scopes:", SCOPES)

        try:
            # Fetch token with authorization response
            flow.fetch_token(
                authorization_response=request.url,
                include_client_id=True,
                code=code
            )
            print("6. Token fetch successful")
            
            credentials = flow.credentials
            
            # Verify the ID token
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=10
            )
            print("7. Token verified successfully")
            print("8. User Info:", {k: id_info[k] for k in ['sub', 'email', 'name'] if k in id_info})
            
            # Find or create user
            user = User.query.filter_by(google_id=id_info['sub']).first()
            if not user:
                print("9. Creating new user")
                user = User(
                    google_id=id_info['sub'],
                    email=id_info.get('email'),
                    name=id_info.get('name', 'Unknown')
                )
                db.session.add(user)
                db.session.commit()
                print("10. New user created with ID:", user.id)
            else:
                print("9. Found existing user:", user.email)
            
            # Log the user in with remember=True
            login_user(user, remember=True)
            
            # Set session data
            session.permanent = True
            session['user_id'] = user.id
            session['google_id'] = user.google_id
            session['email'] = user.email
            
            print("11. User logged in successfully")
            print("12. Final session state:", dict(session))
            print("13. Current user authenticated:", current_user.is_authenticated)
            print("14. Response cookies will be:", dict(request.cookies))
            
            response = redirect('http://localhost:3000')
            return response
            
        except Exception as e:
            print("Token exchange error:", str(e))
            import traceback
            traceback.print_exc()
            return redirect(f'http://localhost:3000?error=token_exchange_failed&details={str(e)}')
            
    except Exception as e:
        print("Unexpected error in callback:", str(e))
        import traceback
        traceback.print_exc()
        return redirect(f'http://localhost:3000?error=callback_failed&details={str(e)}')

@app.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        session.clear()  # Clear the session
        return redirect('http://localhost:3000')
    except Exception as e:
        print(f"Error during logout: {str(e)}")
        return redirect('http://localhost:3000?error=logout_failed')

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

def query(messages, max_retries=2):
    for attempt in range(max_retries):
        try:
            print(f"Making API request (attempt {attempt + 1}/{max_retries})")
            
            response = client.chat.completions.create(
                model="mistralai/Mistral-Nemo-Instruct-2407",
                messages=messages,
                temperature=0.5,
                max_tokens=600
            )
            
            return response
                
        except Exception as e:
            print(f"API request failed on attempt {attempt + 1}:", str(e))
            if attempt + 1 < max_retries:
                print("Retrying...")
                continue
            raise

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    print("\n=== Chat Endpoint Debug ===")
    print("1. Received chat request")
    print("Request data:", request.json)
    
    try:
        if not request.json:
            return jsonify({"error": "No JSON data provided"}), 400
            
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Create OpenAI client with custom configuration
        client = OpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=NEBIUS_API_KEY
        )
        
        try:
            print("Making API request...")
            response = client.chat.completions.create(
                model="mistralai/Mistral-Nemo-Instruct-2407",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Be concise."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                temperature=0.5,
                max_tokens=600,
                stream=False
            )
            
            print("2. Raw API response:", response)
            
            # Extract the bot response from the completed response
            if hasattr(response, 'choices') and len(response.choices) > 0:
                # Handle OpenAI-style response
                if hasattr(response.choices[0], 'message'):
                    bot_response = response.choices[0].message.content
                # Handle raw text response
                elif hasattr(response.choices[0], 'text'):
                    bot_response = response.choices[0].text
                else:
                    # If response is a string or has unexpected format, try to handle it gracefully
                    bot_response = str(response.choices[0])
                print("3. Extracted bot response:", bot_response)
                
                # Save chat history
                chat = Chat(
                    user_id=current_user.id,
                    job_description=user_message,
                    cv_filename="",  # No file for regular chat
                    ai_response=bot_response
                )
                db.session.add(chat)
                db.session.commit()
                print("4. Saved to chat history")
                
                return jsonify({
                    "response": bot_response
                })
            else:
                print("Error: Invalid API response format:", response)
                return jsonify({"error": "Invalid response format from AI service"}), 500
                
        except Exception as e:
            print("API request failed:", str(e))
            error_message = "Failed to get response from AI service"
            return jsonify({"error": error_message, "details": str(e)}), 500

    except Exception as e:
        print("Error in chat endpoint:", str(e))
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

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
                db = load_db(app.config['DB_FOLDER'])
                print("Adding documents to existing database...")
                db.add_documents(documents)
                print("Documents added successfully")
            except Exception as e:
                print(f"Error loading existing database: {str(e)}")
                print("Creating new database...")
                db = create_db(documents, app.config['DB_FOLDER'])
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

@app.route('/chat-history', methods=['GET'])
@login_required
def get_chat_history():
    try:
        # Get user's chat history
        chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
        
        # Format chat history
        # Get user's chat history with proper cv_filename handling
        history = [{
            'id': chat.id,
            'job_description': chat.job_description,
            'cv_filename': chat.cv_filename if isinstance(chat.cv_filename, list) 
                         else (chat.cv_filename.split(',') if chat.cv_filename else []),
            'ai_response': chat.ai_response or '',  # Ensure ai_response is never null
            'created_at': chat.created_at.isoformat()
        } for chat in chats]
        
        print("Chat history being sent:", history)  # Debug output
        
        return jsonify({"history": history})
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-auth')
def check_auth():
    print("\n=== Check Auth Debug ===")
    print("1. Session data:", dict(session))
    print("2. Current user:", current_user)
    print("3. Is authenticated:", current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else 'No current_user')
    
    if current_user.is_authenticated:
        # Ensure session contains user data
        if 'user_id' not in session:
            session['user_id'] = current_user.id
            session['google_id'] = current_user.google_id
            session.permanent = True
        
        user_data = {
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'name': current_user.name,
                'email': current_user.email
            }
        }
        print("4. Returning authenticated user data:", user_data)
        return jsonify(user_data)
    
    print("4. User not authenticated")
    return jsonify({'authenticated': False})

@app.route('/debug/session')
def debug_session():
    print("\n=== Debug Session ===")
    print("All session data:", dict(session))
    return jsonify({
        'session': dict(session),
        'user_authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'name': current_user.name
        } if current_user.is_authenticated else None
    })

@app.route('/debug/users')
def debug_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'google_id': user.google_id
    } for user in users])

@app.errorhandler(Exception)
def handle_error(error):
    print(f"Error occurred: {str(error)}")
    return f"An error occurred: {str(error)}", 500

@app.before_request
def before_request():
    print("\n=== Request Debug ===")
    print("Request Path:", request.path)
    print("Request Method:", request.method)
    print("Request Cookies:", dict(request.cookies))
    print("Session Data:", dict(session))
    print("Current User:", current_user)
    print("Is Authenticated:", current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False)
    
    # Make session permanent
    session.permanent = True
    
    if request.path.startswith('/static/'):
        return

@app.after_request
def after_request(response):
    print("\n=== Response Debug ===")
    print("Response Status:", response.status)
    print("Response Cookies:", dict(response.headers.getlist('Set-Cookie')))
    return response

if __name__ == '__main__':
    print("\nStarting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)