"""
Main Application Server

This Flask application provides an API for document processing and chat functionality.
"""

# Initialize environment and database path
import os
import io
import base64
from datetime import datetime, timedelta
from openai import OpenAI
import tempfile
import pdf2image
from PyPDF2 import PdfReader
from flask import Flask, request, jsonify, send_file, redirect, url_for, session, send_from_directory
from flask_cors import CORS, cross_origin
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from datetime import timedelta
import sqlite3
from dotenv import load_dotenv
from utils.document_processor import load_cv, create_db, load_db, get_processed_pdfs_stats
from flask_session import Session

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
load_dotenv()

# Load and validate API keys
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
HF_TOKEN = os.getenv('HF_TOKEN')

if not HF_TOKEN:
    raise ValueError("Missing Hugging Face API token")

# Configure OpenAI client for Hugging Face Inference API
client = OpenAI(
    base_url="https://router.huggingface.co/nebius/v1",
    api_key=HF_TOKEN
)

app = Flask(__name__, static_folder='frontend/build', static_url_path='')

# Configure Flask app first
app.config.update(
    SECRET_KEY='dev-secret-key-change-in-production',
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR='flask_session',
    SESSION_FILE_THRESHOLD=500,
    SESSION_COOKIE_SECURE=True,  # Required for cross-origin with SameSite=None
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',  # Required for cross-origin
    SESSION_COOKIE_NAME='session',
    SESSION_COOKIE_DOMAIN=None,
    SESSION_COOKIE_PATH='/',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    SESSION_REFRESH_EACH_REQUEST=True,
    REMEMBER_COOKIE_NAME='remember_me',
    REMEMBER_COOKIE_DURATION=timedelta(days=7),
    REMEMBER_COOKIE_SECURE=True,  # Required for cross-origin with SameSite=None
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE='None',  # Required for cross-origin
    REMEMBER_COOKIE_DOMAIN=None,
    REMEMBER_COOKIE_PATH='/',
    SQLALCHEMY_DATABASE_URI='sqlite:///app.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER='uploads',
    DB_FOLDER='chroma_db'
)

# Initialize Flask-Session after config
Session(app)

# Configure CORS with specific origin
CORS(app, 
     resources={
         r"/*": {
             "origins": ["http://localhost:3000"],
             "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin", "Cookie"],
             "expose_headers": ["Content-Type", "Authorization", "Set-Cookie"],
             "supports_credentials": True,
             "send_wildcard": False,
             "max_age": 86400,
             "vary_header": True
         }
     },
     supports_credentials=True)
app.config.update(
    SECRET_KEY='dev-secret-key-change-in-production',
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',  # Required for cross-origin requests
    SESSION_COOKIE_NAME='session',
    SESSION_COOKIE_DOMAIN=None,  # Let browser set the domain
    SESSION_COOKIE_PATH='/',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    SESSION_REFRESH_EACH_REQUEST=True,
    REMEMBER_COOKIE_NAME='remember_token',
    REMEMBER_COOKIE_DURATION=timedelta(days=1),
    REMEMBER_COOKIE_SECURE=False,  # Set to True in production
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE='None',  # Required for cross-origin requests
    SESSION_TYPE='filesystem',  # Use filesystem to store session data
    SESSION_FILE_DIR='flask_session',  # Directory for session files
    SESSION_FILE_THRESHOLD=500,  # Maximum number of sessions stored in the filesystem
    SQLALCHEMY_DATABASE_URI='sqlite:///app.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER='uploads',
    DB_FOLDER='chroma_db'
)

# Initialize SQLAlchemy and login manager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True)

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    cv_filename = db.Column(db.String(255))
    ai_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize the application
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create all database tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

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
@cross_origin(supports_credentials=True)
def login():
    print("\n=== Login Route Debug ===")
    print("1. Login route accessed")
    print("Request headers:", dict(request.headers))
    
    # Check credentials
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: Missing Google OAuth credentials")
        return jsonify({"error": "Missing credentials"}), 500
        
    try:
        # Only clear auth-related session data
        session.pop('_user_id', None)
        session.pop('user_id', None)
        session.pop('google_id', None)
        session.modified = True
        print("2. Auth session data cleared")
        
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
@cross_origin(supports_credentials=True)
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
            return redirect(f'http://localhost:3000?error=oauth_{error}&description={error_description}')

        # Get the authorization code
        code = request.args.get('code')
        if not code:
            print("No authorization code received!")
            return redirect('http://localhost:3000?error=no_auth_code')

        # Initialize flow with the same scopes used in login
        SCOPES = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]

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
            flow.fetch_token(authorization_response=request.url)
            print("6. Token fetch successful")
            
            # Verify the token
            credentials = flow.credentials
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
            
            # Set up session first
            session.clear()  # Clear any existing session data
            session.permanent = True
            
            # Log in the user
            login_user(user, remember=True, duration=timedelta(days=7))
            
            # Set essential session data
            session['_user_id'] = str(user.id)  # Required by Flask-Login
            session['user_id'] = user.id
            session['google_id'] = user.google_id
            session['email'] = user.email
            session.modified = True
            session['email'] = user.email
            session['logged_in'] = True
            session.modified = True
            
            print("11. Session data set:", dict(session))
            print("12. Current user authenticated:", current_user.is_authenticated)
            
            # Create response with proper session handling
            response = redirect('http://localhost:3000')
            
            # Set session cookie explicitly
            session_lifetime = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
            response.set_cookie(
                'session',
                session.sid if hasattr(session, 'sid') else session.get('_id', ''),
                max_age=int(session_lifetime),
                path='/',
                domain=None,
                secure=False,  # Set to True in production
                httponly=True,
                samesite='None'  # Required for cross-origin
            )
            
            print("13. Response cookies being set:", response.headers.getlist('Set-Cookie'))
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
                model="mistralai/Mistral-Small-3.1-24B-Instruct-2503",
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
@cross_origin(supports_credentials=True)
def chat():
    try:
        print("\n=== Starting chat request processing ===")
        
        # Verify user authentication
        if not current_user.is_authenticated:
            print("Error: User not authenticated")
            return jsonify({"error": "Authentication required"}), 401

        # Get and validate request data
        data = request.get_json()
        if not data:
            print("Error: No request data provided")
            return jsonify({"error": "No data provided"}), 400
            
        user_message = data.get('message', '').strip()
        print(f"Received message: {user_message[:100]}...")  # Log first 100 chars
        
        if not user_message:
            print("Error: Empty message received")
            return jsonify({'error': 'Message is required'}), 400

        # Detect if message is a job description
        job_keywords = ['job', 'position', 'hiring', 'looking for', 'requirements', 'qualifications', 
                       'experience', 'skills', 'salary', 'role', 'responsibilities']
        is_job_description = any(keyword in user_message.lower() for keyword in job_keywords)
        print(f"Message classified as job description: {is_job_description}")

        if is_job_description:
            print("Processing as job description...")
            try:
                # Load the vector database
                print("Loading vector database...")
                db = load_db(app.config['DB_FOLDER'])
                print("Vector database loaded successfully")
                
                # Perform semantic search
                print("Performing semantic search...")
                search_results = db.similarity_search_with_score(
                    user_message,
                    k=5
                )
                print(f"Found {len(search_results)} matching documents")
                
                # Process matched CVs
                matched_cvs = []
                for i, (doc, score) in enumerate(search_results):
                    print(f"\nProcessing match {i+1}:")
                    print(f"Score: {score}")
                    print(f"Filename: {doc.metadata.get('filename', 'unknown')}")
                    
                    if score < 0.8:
                        cv_content = doc.page_content.strip()
                        if len(cv_content) > 1000:
                            cv_content = cv_content[:1000] + "..."
                        
                        # Get filename with fallback for missing metadata
                        filename = doc.metadata.get('filename')
                        if not filename:
                            print(f"Warning: Document missing filename metadata. Full metadata: {doc.metadata}")
                            continue
                            
                        matched_cv = {
                            'filename': filename,
                            'relevance_score': float(score),
                            'content': cv_content,
                            'source': doc.metadata.get('source', 'pdf'),
                            'page': doc.metadata.get('page', 1)
                        }
                        matched_cvs.append(matched_cv)
                        print(f"Added to matched CVs. Total matches: {len(matched_cvs)}")
                    else:
                        print(f"Skipped due to low relevance score: {score}")

                if matched_cvs:
                    print(f"\nProcessing {len(matched_cvs)} matched CVs...")
                    # Continue with existing matched CV processing...
                    
                    # Add CV images to messages
                    messages = [
                        {"role": "system", "content": """You are an expert HR assistant specializing in CV analysis and job matching. 
                        Analyze the provided CV images along with the job description, and provide:
                        1. Overall Match Score (1-10)
                        2. Key Strengths that align with the job requirements
                        3. Potential Gaps or areas for improvement
                        4. Specific skills and experiences that make the candidate suitable
                        5. Brief hiring recommendation

                        Format your response clearly for each CV, and conclude with a ranked comparison of all candidates."""},
                        {"role": "user", "content": [
                            {
                                "type": "text",
                                "text": f"Job Description:\n{user_message}\n\nPlease analyze the following CVs:"
                            }
                        ]}
                    ]

                    print("Processing CV images...")
                    for i, cv in enumerate(matched_cvs):
                        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], cv['filename'])
                        print(f"\nProcessing CV {i+1}: {cv['filename']}")
                        
                        if os.path.exists(pdf_path):
                            print(f"Converting PDF to images: {pdf_path}")
                            try:
                                base64_images = convert_pdf_to_base64_images(pdf_path)
                                if base64_images:
                                    print(f"Successfully converted PDF to {len(base64_images)} images")
                                    messages[1]["content"].extend([
                                        {
                                            "type": "text",
                                            "text": f"\nCV {i+1}: {cv['filename']} (Relevance Score: {cv['relevance_score']:.2f})"
                                        },
                                        *[{
                                            "type": "image_url",
                                            "image_url": {"url": img_url}
                                        } for img_url in base64_images]
                                    ])
                                else:
                                    print("Warning: No images generated from PDF")
                            except Exception as e:
                                print(f"Error converting PDF to images: {str(e)}")
                                continue
                        else:
                            print(f"Warning: PDF file not found at {pdf_path}")

                    print("\nCalling LLM API...")
                    response = client.chat.completions.create(
                        model="mistralai/Mistral-Small-3.1-24B-Instruct-2503",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2000,
                        stream=False
                    )
                    print("LLM API call successful")

                    try:
                        print("\nSaving chat history...")
                        from flask_sqlalchemy import SQLAlchemy
                        db_sql = SQLAlchemy(app)
                        
                        cv_filenames = [cv['filename'] for cv in matched_cvs]
                        chat = Chat(
                            user_id=current_user.id,
                            job_description=user_message,
                            cv_filename=','.join(cv_filenames),
                            ai_response=response.choices[0].message.content
                        )
                        db_sql.session.add(chat)
                        db_sql.session.commit()
                        print("Chat history saved successfully")
                    except Exception as e:
                        print(f"Error saving chat history: {str(e)}")
                        # Continue even if saving fails
                        pass

                else:
                    print("\nNo matching CVs found, generating suggestions...")
                    response = client.chat.completions.create(
                        model="mistralai/Mistral-Small-3.1-24B-Instruct-2503",
                        messages=[
                            {"role": "system", "content": "You are an expert HR assistant."},
                            {"role": "user", "content": [
                                {
                                    "type": "text",
                                    "text": f"I could not find any CVs that match the following job description. "
                                           f"Please suggest what kind of candidates I should look for:\n\n{user_message}"
                                }
                            ]}
                        ],
                        temperature=0.7,
                        max_tokens=1000,
                        stream=False
                    )
                    print("Generated suggestions for no matches")

            except Exception as e:
                print(f"\nError in job description processing:")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'error': 'Error processing job description',
                    'details': str(e) if app.debug else None
                }), 500
        else:
            print("\nProcessing as regular chat message...")
            response = client.chat.completions.create(
                model="mistralai/Mistral-Small-3.1-24B-Instruct-2503",
                messages=[
                    {"role": "system", "content": "You are an expert HR assistant who specializes in career advice, "
                                                 "resume writing, interview preparation, and professional development. "
                                                 "Provide clear, practical, and actionable advice."},
                    {"role": "user", "content": [{"type": "text", "text": user_message}]}
                ],
                temperature=0.7,
                max_tokens=1000,
                stream=False
            )
            print("Regular chat processing successful")

        print("\nSending response to client")
        return jsonify({
            'response': response.choices[0].message.content
        })

    except Exception as e:
        print(f"\n=== Error in chat endpoint ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("User:", current_user.id if current_user.is_authenticated else "Not authenticated")
        print("Request data:", data if 'data' in locals() else "No data")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'An error occurred processing your request',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/upload-pdf', methods=['POST', 'OPTIONS'])
def upload_pdf():
    """Handle PDF file upload and processing"""
    if request.method == 'OPTIONS':
        return handle_preflight()
        
    try:
        print("Received upload request")
        if 'file' not in request.files:
            print("No file part in request")
            return jsonify({"error": "No file part"}), 400
            
        file = request.files['file']
        if file.filename == '':
            print("No selected file")
            return jsonify({"error": "No selected file"}), 400
            
        print(f"Received file: {file.filename}")
        print(f"File content type: {file.content_type}")

        if not allowed_file(file.filename):
            print(f"Invalid file type: {file.filename}")
            return jsonify({"error": f"Invalid file type. Only PDF files are allowed. Received: {file.content_type}"}), 400

        # Create uploads directory if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['DB_FOLDER'], exist_ok=True)

        print("Creating temporary file...")
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

            try:
                # Load and split the document
                print("Loading and splitting document...")
                documents = load_cv(temp_file.name)
                print(f"Document loaded and split into {len(documents)} chunks")
                
                try:
                    # Try to load existing database
                    print("Loading existing database...")
                    db = load_db(app.config['DB_FOLDER'])
                    print("Adding documents to existing database...")
                    db.add_documents(documents)
                    db.persist()
                    print("Documents added successfully")
                except Exception as e:
                    print(f"Error loading existing database: {str(e)}")
                    print("Creating new database...")
                    db = create_db(documents, app.config['DB_FOLDER'])
                    db.persist()
                    print("New database created successfully")
                
            except ValueError as ve:
                print(f"Error processing PDF: {str(ve)}")
                os.unlink(temp_file.name)
                return jsonify({"error": f"Could not extract text from PDF: {str(ve)}"}), 400
                
            except Exception as e:
                print(f"Error processing file: {str(e)}")
                os.unlink(temp_file.name)
                return jsonify({"error": f"Error processing file: {str(e)}"}), 500
            
            # Clean up the temporary file
            print("Cleaning up temporary file...")
            os.unlink(temp_file.name)
            print("Temporary file deleted")
            
            return jsonify({
                "message": "File uploaded and processed successfully",
                "filename": file.filename,
                "chunks": len(documents)
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
@cross_origin(supports_credentials=True)
def check_auth():
    print("\n=== Check Auth Debug ===")
    print("1. Session data:", dict(session))
    print("2. Current user:", current_user)
    print("3. Request cookies:", dict(request.cookies))
    print("4. Headers:", {k: v for k, v in request.headers.items()})
    
    try:
        # First check if we already have an authenticated user
        if current_user.is_authenticated:
            print("5. User already authenticated:", current_user.email)
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': current_user.id,
                    'name': current_user.name,
                    'email': current_user.email
                }
            })
        
        # Try to restore session from stored user_id
        user_id = session.get('_user_id') or session.get('user_id')
        if user_id:
            user = User.query.get(int(user_id))
            if user:
                login_user(user, remember=True)
                session.permanent = True
                session.modified = True
                print("5. Restored session for user:", user.email)
                return jsonify({
                    'authenticated': True,
                    'user': {
                        'id': user.id,
                        'name': user.name,
                        'email': user.email
                    }
                })
        
        print("5. No valid session found")
        return jsonify({'authenticated': False})
        
    except Exception as e:
        print("Error in check_auth:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({'authenticated': False, 'error': str(e)})

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

@app.route('/debug/session-info')
def debug_session_info():
    """Debug endpoint to check session and authentication state"""
    return jsonify({
        'session_data': dict(session),
        'user_authenticated': current_user.is_authenticated,
        'user_info': {
            'id': current_user.id,
            'email': current_user.email,
            'name': current_user.name
        } if current_user.is_authenticated else None,
        'headers': {k: v for k, v in request.headers.items()},
        'cookies': dict(request.cookies)
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
    print("Request Headers:", {k: v for k, v in request.headers.items()})
    print("Request Cookies:", dict(request.cookies))
    print("Session Data:", dict(session))
    print("Current User:", current_user)
    print("Is Authenticated:", current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False)
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        origin = request.headers.get('Origin', 'http://localhost:3000')
        response.headers.update({
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '3600'
        })
        return response
        
    # Restore user session if needed
    if 'user_id' in session and not current_user.is_authenticated:
        user = User.query.get(session['user_id'])
        if user:
            login_user(user)
            session.permanent = True
    
    # Skip session handling for static files
    if request.path.startswith('/static/'):
        return

@app.after_request
def after_request(response):
    print("\n=== Response Debug ===")
    print("Response Status:", response.status)
    print("Original Response Headers:", dict(response.headers))
    
    origin = request.headers.get('Origin', 'http://localhost:3000')
    if origin:
        # Set CORS headers for the response
        response.headers.update({
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Cookie',
            'Access-Control-Expose-Headers': 'Set-Cookie, Authorization',
            'Vary': 'Origin, Cookie'
        })
    
    # Ensure proper cookie attributes for cross-origin requests
    try:
        cookies = response.headers.getlist('Set-Cookie')
        if cookies:
            print("Processing cookies:", cookies)
            response.headers.pop('Set-Cookie', None)
            
            for cookie in cookies:
                if 'session=' in cookie:
                    # Ensure session cookie has required attributes for cross-origin
                    if 'SameSite=None' not in cookie:
                        cookie += '; SameSite=None'
                    if 'Secure' not in cookie:
                        cookie += '; Secure'
                response.headers.add('Set-Cookie', cookie)
            
            print("Modified cookies:", response.headers.getlist('Set-Cookie'))
    except Exception as e:
        print("Error processing cookies:", str(e))
        
    print("Final Response Headers:", dict(response.headers))
    return response

def handle_preflight():
    """Handle CORS preflight requests"""
    response = jsonify({'status': 'ok'})
    
    # Get the origin from the request headers
    origin = request.headers.get('Origin', 'http://localhost:3000')
    
    # Set CORS headers
    response.headers.update({
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, Cookie, X-Requested-With, X-CSRF-Token',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Expose-Headers': 'Content-Type, Authorization, Set-Cookie',
        'Access-Control-Max-Age': '3600',
        'Vary': 'Origin'
    })
    
    return response, 200

@app.route('/pdf-stats', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def get_pdf_stats():
    """Get statistics about processed PDFs"""
    if request.method == 'OPTIONS':
        return handle_preflight()
        
    try:
        # Check authentication
        if not current_user.is_authenticated:
            print("User not authenticated, redirecting to login")
            return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            
        print(f"User authenticated: {current_user.id}")
        stats = get_processed_pdfs_stats(app.config['UPLOAD_FOLDER'])
        
        response = jsonify({
            "authenticated": True,
            "user_id": current_user.id,
            "stats": stats
        })
        return response
        
    except Exception as e:
        print("\n=== Error in pdf-stats endpoint ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("User:", current_user.id if current_user.is_authenticated else "Not authenticated")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Error retrieving PDF stats",
            "details": str(e) if app.debug else None
        }), 500

@app.route('/get-matched-pdfs/<chat_id>', methods=['GET'])
@login_required
def get_matched_pdfs(chat_id):
    try:
        # Get the chat history entry
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
            
        # Get filenames from the chat history
        cv_filenames = chat.cv_filename.split(',') if chat.cv_filename else []
        
        pdf_data = []
        for filename in cv_filenames:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                pdf_data.append({
                    'filename': filename,
                    'url': url_for('get_pdf', filename=filename, _external=True)
                })
                
        return jsonify({
            'pdfs': pdf_data
        })
        
    except Exception as e:
        print(f"Error retrieving matched PDFs: {str(e)}")
        return jsonify({"error": str(e)}), 500

def convert_pdf_to_base64_images(pdf_path):
    """Convert PDF pages to base64 encoded images"""
    try:
        # Convert PDF to images
        images = pdf2image.convert_from_path(pdf_path)
        
        # Convert each image to base64
        base64_images = []
        for img in images:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Convert to base64
            base64_str = base64.b64encode(img_byte_arr).decode('utf-8')
            base64_images.append(f"data:image/png;base64,{base64_str}")
            
        return base64_images
    except Exception as e:
        print(f"Error converting PDF to images: {str(e)}")
        return None

@app.route('/check-session', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def check_session():
    """Check if user session is valid"""
    if request.method == 'OPTIONS':
        return handle_preflight()
        
    try:
        print("\n=== Session Check Debug ===")
        print("Session data:", dict(session))
        print("Current user:", current_user)
        print("Is authenticated:", current_user.is_authenticated)
        print("Cookies:", dict(request.cookies))
        
        if current_user.is_authenticated:
            return jsonify({
                "authenticated": True,
                "user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "name": current_user.name
                }
            })
        else:
            return jsonify({
                "authenticated": False,
                "redirect": "/login"
            }), 401
            
    except Exception as e:
        print(f"Error checking session: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("\nStarting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)