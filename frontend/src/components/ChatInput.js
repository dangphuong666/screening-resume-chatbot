import React, { useState, useRef, useEffect } from 'react';
import { Box, IconButton, TextField, Tooltip, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import ClearIcon from '@mui/icons-material/Clear';

const ChatInput = ({ onSend, disabled, fileUploadRef }) => {
  const [message, setMessage] = useState('');
  const [rows, setRows] = useState(1);
  const textFieldRef = useRef(null);
  const maxRows = 5;

  useEffect(() => {
    if (textFieldRef.current) {
      const lineHeight = 20; // approximate line height in pixels
      const padding = 32; // total vertical padding
      const currentHeight = textFieldRef.current.querySelector('textarea').scrollHeight;
      const calculatedRows = Math.min(Math.floor((currentHeight - padding) / lineHeight), maxRows);
      setRows(Math.max(1, calculatedRows));
    }
  }, [message]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message);
      setMessage('');
      setRows(1);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const clearInput = () => {
    setMessage('');
    setRows(1);
    textFieldRef.current?.querySelector('textarea').focus();
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        p: 2,
        backgroundColor: 'background.paper',
        borderTop: 1,
        borderColor: 'divider',
        display: 'flex',
        gap: 1,
        position: 'relative',
      }}
    >
      <TextField
        ref={textFieldRef}
        fullWidth
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Type your message..."
        disabled={disabled}
        multiline
        minRows={1}
        maxRows={maxRows}
        variant="outlined"
        size="medium"
        sx={{
          '& .MuiOutlinedInput-root': {
            backgroundColor: 'background.default',
            transition: 'all 0.3s ease',
            '&:hover': {
              backgroundColor: 'background.paper',
            },
            '&.Mui-focused': {
              backgroundColor: 'background.paper',
            },
          },
        }}
      />
      {message && (
        <Tooltip title="Clear message">
          <span>
            <IconButton
              onClick={clearInput}
              size="small"
              sx={{
                position: 'absolute',
                right: 120,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'text.secondary',
              }}
            >
              <ClearIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      )}
      <Tooltip title="Upload PDF">
        <IconButton
          onClick={() => fileUploadRef?.current?.click()}
          sx={{
            width: 56,
            height: 56,
            '&:hover': {
              backgroundColor: 'rgba(25, 118, 210, 0.08)',
            },
          }}
        >
          <PictureAsPdfIcon />
        </IconButton>
      </Tooltip>
      <Tooltip title={disabled ? 'Processing...' : 'Send message'}>
        <span>
          <IconButton
            type="submit"
            color="primary"
            disabled={disabled || !message.trim()}
            sx={{
              width: 56,
              height: 56,
              transition: 'all 0.3s ease',
              '&:hover': {
                backgroundColor: 'primary.dark',
              },
            }}
          >
            {disabled ? <CircularProgress size={24} /> : <SendIcon />}
          </IconButton>
        </span>
      </Tooltip>
    </Box>
  );
};

export default ChatInput;