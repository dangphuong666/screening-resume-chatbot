import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Paper, Typography, LinearProgress, Alert, Snackbar, SpeedDial, SpeedDialIcon, SpeedDialAction } from '@mui/material';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import CloseIcon from '@mui/icons-material/Close';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import FileUpload from './FileUpload';
import axios from 'axios';

const Chat = ({ history, onNewChat }) => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pendingFiles, setPendingFiles] = useState([]);
  const fileUploadRef = useRef(null);

  useEffect(() => {
    // Load chat history when component mounts or history changes
    if (history && history.length > 0) {
      console.log('Processing chat history:', history);
      // Each chat entry becomes two messages: user message and bot response
      // Process history chronologically (oldest first)
      const formattedHistory = history.flatMap(chat => {
        console.log('Processing chat entry:', chat);
        return [
          {
            id: `${chat.id}-user`,
            text: chat.job_description || '',
            sender: 'user',
            timestamp: new Date(chat.created_at)
          },
          {
            id: `${chat.id}-bot`,
            text: chat.ai_response || '',
            sender: 'bot',
            timestamp: new Date(chat.created_at),
            matchedFiles: Array.isArray(chat.cv_filename)
              ? chat.cv_filename.filter(Boolean)
              : (chat.cv_filename ? chat.cv_filename.split(',').filter(Boolean) : [])
          }
        ];
      });
      setMessages(formattedHistory); // Maintains chronological order
    }
  }, [history]);

  const handleFileUploadSuccess = (filesData) => {
    setPendingFiles(prev => [...prev, ...filesData]);
    
    const systemMessage = {
      id: Date.now(),
      text: `📄 ${filesData.length} PDF file${filesData.length > 1 ? 's' : ''} uploaded. Start chatting to analyze ${filesData.length > 1 ? 'them' : 'it'}.`,
      sender: 'system',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [systemMessage, ...prev]); // Add to beginning
  };

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() && pendingFiles.length === 0) return;

    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const botMessageId = `bot-${messageId}`;
    const messageTimestamp = new Date();

    // Add user message to chat
    const userMessage = {
      id: messageId,
      text: text.trim(),
      sender: 'user',
      timestamp: messageTimestamp,
    };

    // Add placeholder for bot response
    const botPlaceholder = {
      id: botMessageId,
      text: '...',
      sender: 'bot',
      timestamp: messageTimestamp,
      isLoading: true,
    };

    // Add both messages to the end of the messages array
    setMessages(prev => [...prev, userMessage, botPlaceholder]);
    setLoading(true);

    try {
      const response = await axios.post('/chat', {
        message: text,
        files: pendingFiles,
      }, {
        timeout: 300000, // 5-minute timeout
        headers: {
          'Content-Type': 'application/json',
        },
        withCredentials: true
      });

      if (response.data.error) {
        throw new Error(response.data.error);
      }

      // Update the bot message with the actual response
      const botMessage = {
        id: botMessageId,
        text: response.data.response || '',
        sender: 'bot',
        timestamp: messageTimestamp,
      };

      // Replace the placeholder while maintaining order
      setMessages(prev => prev.map(msg => 
        msg.id === botMessageId ? botMessage : msg
      ));
      setPendingFiles([]);
      
      if (onNewChat) {
        onNewChat();
      }
    } catch (error) {
      console.error('Error sending message:', error);
      let errorMessage = 'An error occurred while sending your message. Please try again.';
      
      if (error.code === 'ECONNABORTED') {
        errorMessage = 'The request timed out. The AI service is taking too long to respond. Please try again.';
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      }
      
      setError(errorMessage);
      
      // Update the placeholder with error message
      const errorBotMessage = {
        id: botMessageId,
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
        timestamp: messageTimestamp,
        isError: true,
      };
      setMessages(prev => prev.map(msg => 
        msg.id === botMessageId ? errorBotMessage : msg
      ));
    } finally {
      setLoading(false);
    }
  }, [pendingFiles, onNewChat]);

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
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100vh - 120px)',
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