# Resume Screening Chatbot

A full-stack AI-powered system for automated resume (CV) screening, job description matching, and candidate analysis.  
Built with React (frontend) and Flask (backend), leveraging multimodal LLMs (Mistral via Hugging Face), semantic search (ChromaDB), and Google OAuth authentication.

---

## Features

- **Google OAuth Authentication:** Secure login for users.
- **PDF Upload:** Upload candidate CVs in PDF format.
- **Semantic Search:** Find and match CVs to job descriptions using vector embeddings.
- **Multimodal LLM Analysis:** Uses Mistral LLM (via Hugging Face) to analyze both text and images from CVs.
- **Chat Interface:** Interactive chat for job description input and candidate analysis.
- **PDF Statistics:** View stats about uploaded/processed CVs.
- **Session Management:** Secure, server-side sessions with Flask-Session.
- **Modern UI:** Built with React and Material-UI.

---

## System Purpose

To automate and enhance the recruitment process by enabling intelligent, AI-driven screening and matching of candidate CVs against job descriptions.

## System Audience

- HR professionals and recruiters
- Hiring managers
- Talent acquisition teams
- Organizations seeking to automate resume screening

---

## Technologies Used

- **Frontend:** React, Material-UI
- **Backend:** Flask, Flask-Session, Flask-Login, Flask-SQLAlchemy, Flask-CORS
- **Authentication:** Google OAuth 2.0
- **PDF Processing:** PyPDF2, pdf2image, pytesseract, Pillow
- **Vector DB & Embeddings:** ChromaDB, LangChain, HuggingFaceEmbeddings (`BAAI/bge-large-en-v1.5`)
- **LLM:** Mistral (via Hugging Face Inference API)
- **Database:** SQLite (for user and chat data)
- **Session Storage:** Filesystem (`flask_session/`)

---

## Project Structure

```
frontend/         # React app (UI, chat, PDF stats, etc.)
  src/
    App.js
    components/
      Chat.js
      PdfStats.js
      FileUpload.js
      MessageList.js
      ...
server/           # Flask backend (API, auth, processing)
  main.py
  document_processor.py
  chroma_db/      # Chroma vector DB files
  flask_session/  # Session files
  instance/       # SQLite DB
uploads/          # Uploaded PDF files
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/dangphuong666/screening-resume-chatbot.git
cd screening-resume-chatbot
```

### 2. Backend Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the root directory with:

```
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
HF_TOKEN=your_huggingface_token
FLASK_ENV=development
FLASK_DEBUG=1
```

Start the backend:

```bash
cd server
python main.py
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm start
```

The app will be available at [http://localhost:3000](http://localhost:3000).

---

## Usage

1. Log in with Google.
2. Upload candidate CVs (PDF).
3. Enter a job description in the chat.
4. View AI-powered candidate analysis and PDF statistics.

---

## License

This project is licensed under the MIT License.
