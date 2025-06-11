import React, { useState, useEffect } from 'react';
import { Paper, Typography, Box, Avatar, Chip } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import InfoIcon from '@mui/icons-material/Info';
import ReactMarkdown from 'react-markdown';

const Message = ({ text, sender, isError, isFileSummary }) => {
  const isUser = sender === 'user';
  const isSystem = sender === 'system';
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(!isUser && !isSystem);

  useEffect(() => {
    if (!isUser && !isSystem) {
      setDisplayedText('');
      setIsTyping(true);
      let currentText = '';
      const words = text.split(' ');

      const typeNextWord = (index) => {
        if (index < words.length) {
          currentText += (index === 0 ? '' : ' ') + words[index];
          setDisplayedText(currentText);
          const delay = Math.random() * 50 + 30; // Random delay between 30-80ms
          setTimeout(() => typeNextWord(index + 1), delay);
        } else {
          setIsTyping(false);
        }
      };

      typeNextWord(0);
    } else {
      setDisplayedText(text);
      setIsTyping(false);
    }
  }, [text, isUser, isSystem]);

  const getIcon = () => {
    if (isSystem) return <InfoIcon />;
    if (isUser) return <PersonIcon />;
    return <SmartToyIcon />;
  };

  const getAvatarColor = () => {
    if (isError) return 'error.main';
    if (isSystem) return 'info.main';
    if (isUser) return 'primary.main';
    return 'secondary.main';
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        flexDirection: isUser ? 'row-reverse' : 'row',
        mb: 2,
        gap: 1,
        animation: 'fadeIn 0.3s ease-in-out',
        '@keyframes fadeIn': {
          from: {
            opacity: 0,
            transform: 'translateY(10px)',
          },
          to: {
            opacity: 1,
            transform: 'translateY(0)',
          },
        },
      }}
    >
      <Avatar
        sx={{
          bgcolor: getAvatarColor(),
          mt: 0.5,
          animation: isTyping ? 'pulse 1.5s ease-in-out infinite' : 'none',
          '@keyframes pulse': {
            '0%': { transform: 'scale(1)' },
            '50%': { transform: 'scale(1.1)' },
            '100%': { transform: 'scale(1)' },
          },
        }}
      >
        {getIcon()}
      </Avatar>
      <Paper
        className={`message ${sender}-message`}
        elevation={1}
        sx={{
          p: 2,
          maxWidth: '70%',
          color: 'white',
          backgroundColor: isError ? 'error.dark' : isSystem ? 'info.dark' : isUser ? 'primary.main' : 'background.paper',
          borderRadius: 2,
          position: 'relative',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 10,
            [isUser ? 'right' : 'left']: -10,
            borderStyle: 'solid',
            borderWidth: '10px 10px 0',
            borderColor: `${
              isError ? '#d32f2f' : 
              isSystem ? '#0288d1' :
              isUser ? '#1976d2' : '#1e1e1e'
            } transparent transparent`,
            transform: isUser ? 'rotate(-45deg)' : 'rotate(45deg)',
          },
          '& pre': {
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
            padding: '10px',
            borderRadius: '4px',
            overflow: 'auto',
          },
          '& code': {
            fontFamily: 'monospace',
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
            padding: '2px 4px',
            borderRadius: '4px',
          },
        }}
      >
        {isFileSummary && (
          <Box sx={{ mb: 2 }}>
            <Chip
              icon={<PictureAsPdfIcon />}
              label="PDF Summary"
              color="primary"
              size="small"
              sx={{ mb: 1 }}
            />
          </Box>
        )}
        <ReactMarkdown
          components={{
            p: ({ children }) => (
              <Typography variant="body1" component="div" sx={{ mb: 1 }}>
                {children}
              </Typography>
            ),
          }}
        >
          {displayedText}
        </ReactMarkdown>
        {isTyping && (
          <Box
            sx={{
              mt: 1,
              display: 'flex',
              gap: 0.5,
              '& .dot': {
                width: 6,
                height: 6,
                backgroundColor: 'rgba(255, 255, 255, 0.6)',
                borderRadius: '50%',
                animation: 'bounce 1.4s infinite ease-in-out',
                '&:nth-of-type(1)': {
                  animationDelay: '0s',
                },
                '&:nth-of-type(2)': {
                  animationDelay: '0.2s',
                },
                '&:nth-of-type(3)': {
                  animationDelay: '0.4s',
                },
              },
              '@keyframes bounce': {
                '0%, 100%': {
                  transform: 'translateY(0)',
                },
                '50%': {
                  transform: 'translateY(-5px)',
                },
              },
            }}
          >
            <div className="dot" />
            <div className="dot" />
            <div className="dot" />
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default Message;