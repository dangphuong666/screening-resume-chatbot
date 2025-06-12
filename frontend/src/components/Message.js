import React, { useState, useEffect } from 'react';
import { Paper, Typography, Box, Avatar, Chip, CircularProgress } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import InfoIcon from '@mui/icons-material/Info';
import ReactMarkdown from 'react-markdown';

const Message = ({ text, sender, isError, isFileSummary, isLoading }) => {
  console.log('Message component received:', { text, sender, isError, isFileSummary, isLoading });
  const isUser = sender === 'user';
  const isSystem = sender === 'system';
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(!isUser && !isSystem && !isLoading);

  useEffect(() => {
    if (!text || isLoading) {
      setDisplayedText('');
      setIsTyping(false);
      return;
    }

    if (!isUser && !isSystem) {
      setDisplayedText('');
      setIsTyping(true);
      let currentText = '';
      const words = text.split(' ');
      let currentIndex = 0;

      const typingInterval = setInterval(() => {
        if (currentIndex < words.length) {
          currentText += (currentIndex === 0 ? '' : ' ') + words[currentIndex];
          setDisplayedText(currentText);
          currentIndex++;
        } else {
          clearInterval(typingInterval);
          setIsTyping(false);
        }
      }, 50);

      return () => clearInterval(typingInterval);
    } else {
      setDisplayedText(text);
      setIsTyping(false);
    }
  }, [text, isUser, isSystem, isLoading]);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'flex-start',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        gap: 1,
        mb: 2,
        width: '100%',
      }}
    >
      {!isUser && (
        <Avatar
          sx={{
            bgcolor: isSystem ? 'warning.main' : 'secondary.main',
            width: 32,
            height: 32,
          }}
        >
          {isSystem ? (
            <InfoIcon fontSize="small" />
          ) : (
            <SmartToyIcon fontSize="small" />
          )}
        </Avatar>
      )}
      
      <Paper
        sx={{
          p: 2,
          maxWidth: '70%',
          bgcolor: isUser
            ? 'primary.main'
            : isSystem
            ? 'warning.dark'
            : isError
            ? 'error.dark'
            : 'secondary.dark',
          color: '#fff',
          borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
          position: 'relative',
        }}
      >
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 1 }}>
            <CircularProgress size={20} color="inherit" />
          </Box>
        ) : (
          <Typography component="div">
            {isFileSummary && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <PictureAsPdfIcon />
                <Typography variant="subtitle2">File Summary</Typography>
              </Box>
            )}
            <ReactMarkdown>{displayedText}</ReactMarkdown>
          </Typography>
        )}
      </Paper>

      {isUser && (
        <Avatar
          sx={{
            bgcolor: 'primary.main',
            width: 32,
            height: 32,
          }}
        >
          <PersonIcon fontSize="small" />
        </Avatar>
      )}
    </Box>
  );
};

export default Message;