import React, { useState, useCallback, useRef } from 'react';
import { Paper, Typography, LinearProgress, Alert, Snackbar, SpeedDial, SpeedDialIcon, SpeedDialAction } from '@mui/material';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import CloseIcon from '@mui/icons-material/Close';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import FileUpload from './FileUpload';
import axios from 'axios';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pendingFiles, setPendingFiles] = useState([]);
  const fileUploadRef = useRef(null);

  const handleFileUploadSuccess = (filesData) => {
    setPendingFiles(prev => [...prev, ...filesData]);
    
    // Add system message about file uploads
    const systemMessage = {
      id: Date.now(),
      text: `📄 ${filesData.length} PDF file${filesData.length > 1 ? 's' : ''} uploaded. Start chatting to analyze ${filesData.length > 1 ? 'them' : 'it'}.`,
      sender: 'system',
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, systemMessage]);
  };

  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return;

    const newMessage = {
      id: Date.now(),
      text,
      sender: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, newMessage]);
    setLoading(true);
    setError(null);

    try {
      // If there are pending files, send them along with the message
      const payload = {
        message: text,
        pendingFiles: pendingFiles.map(file => ({
          name: file.name,
          content: file.content,
          summary: file.summary
        }))
      };

      const response = await axios.post('http://localhost:5000/chat', payload, {
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      const botMessage = {
        id: Date.now() + 1,
        text: response.data.response,
        sender: 'bot',
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, botMessage]);
      // Clear pending files after processing
      setPendingFiles([]);
    } catch (error) {
      console.error('Error sending message:', error);
      setError(error.message || 'An error occurred while sending your message. Please try again.');
      
      const errorMessage = {
        id: Date.now() + 1,
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }, [pendingFiles]);

  const handleCloseError = () => {
    setError(null);
  };

  return (
    <>
      <Paper 
        className="chat-container" 
        elevation={3}
        sx={{
          position: 'relative',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
        }}
      >
        {messages.length === 0 && (
          <Typography
            variant="h6"
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'text.secondary',
              textAlign: 'center',
              width: '80%',
            }}
          >
            Start a conversation by typing a message below or upload a PDF file
          </Typography>
        )}
        <MessageList messages={messages} />
        {loading && (
          <LinearProgress 
            sx={{ 
              position: 'absolute', 
              bottom: '72px', 
              left: 0, 
              right: 0,
            }} 
          />
        )}
        <ChatInput onSend={sendMessage} disabled={loading} fileUploadRef={fileUploadRef} />
      </Paper>

      {/* File Upload Speed Dial */}
      <SpeedDial
        ariaLabel="File upload actions"
        sx={{ 
          position: 'fixed', 
          bottom: 24, 
          right: 24,
          '& .MuiFab-primary': {
            width: 56,
            height: 56,
            '&:hover': {
              backgroundColor: 'primary.dark',
            },
          },
        }}
        icon={<SpeedDialIcon icon={<AttachFileIcon />} openIcon={<CloseIcon />} />}
      >
        <SpeedDialAction
          icon={<PictureAsPdfIcon />}
          tooltipTitle="Upload PDF"
          tooltipOpen
          onClick={() => fileUploadRef.current?.click()}
          sx={{
            '&:hover': {
              backgroundColor: 'primary.light',
            },
          }}
        />
      </SpeedDial>

      {/* Hidden FileUpload component */}
      <div style={{ display: 'none' }}>
        <FileUpload
          ref={fileUploadRef}
          onUploadSuccess={handleFileUploadSuccess}
        />
      </div>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={handleCloseError}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseError} severity="error" variant="filled">
          {error}
        </Alert>
      </Snackbar>
    </>
  );
};

export default Chat;