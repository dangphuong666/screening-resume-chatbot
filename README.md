# AI Chat Assistant

A modern chat interface powered by Nebius AI, built with React and Flask. This application allows users to chat with an AI assistant and analyze PDF documents through conversation.

## Features

- 🎯 Modern, responsive Material-UI interface
- 💬 Real-time chat with AI
- 📄 PDF file upload and analysis
- ✨ Multiple file upload support
- 🔍 Context-aware responses
- 🎨 Dark theme with glassmorphism design

## Project Structure

```
chat bot/
├── frontend/          # React frontend application
│   ├── src/          # Source code
│   │   ├── components/ # React components
│   │   └── ...       # Other frontend files
│   ├── public/       # Static files
│   └── package.json  # Frontend dependencies
├── main.py           # Flask backend server
├── pdf_process.py    # PDF processing utilities
├── requirements.txt  # Python dependencies
└── uploads/         # PDF upload directory
```

## Prerequisites

- Python 3.8 or higher
- Node.js 14.0 or higher
- npm or yarn

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd chat-bot
```

2. Set up the Python backend:
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

3. Set up the React frontend:
```bash
cd frontend
npm install
```

## Configuration

1. Set your Nebius AI API key in `main.py`:
```python
os.environ["NEBIUS_API_KEY"] = "your-api-key-here"
```

## Running the Application

1. Start the Flask backend server:
```bash
# From the root directory
source venv/bin/activate  # If not already activated
python main.py
```

2. Start the React frontend development server:
```bash
# In another terminal, from the frontend directory
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## Usage

1. Start chatting by typing in the message input
2. Upload PDF files using either:
   - The floating action button in the bottom right
   - The upload button next to the message input
3. Chat with the AI about the uploaded documents
4. The AI will incorporate information from the PDFs in its responses

## Development

- Backend API endpoint: http://localhost:5000/chat
- Frontend development server: http://localhost:3000
- Frontend build: `npm run build` in the frontend directory

## Technologies Used

- Frontend:
  - React.js
  - Material-UI
  - React Markdown
  - Axios

- Backend:
  - Flask
  - Flask-CORS
  - Nebius AI API

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
