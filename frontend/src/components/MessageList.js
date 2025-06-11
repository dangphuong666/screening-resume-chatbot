import React, { useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import Message from './Message';

const MessageList = ({ messages }) => {
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  const previousScrollHeight = useRef(0);

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const scrollToBottom = () => {
    if (containerRef.current) {
      const scrollContainer = containerRef.current;
      const { scrollHeight, clientHeight, scrollTop } = scrollContainer;
      const maxScrollTop = scrollHeight - clientHeight;
      
      // If user has scrolled up more than 100px, don't auto-scroll
      if (maxScrollTop - scrollTop < 100 || scrollHeight > previousScrollHeight.current) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
      previousScrollHeight.current = scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <Box
      ref={containerRef}
      className="message-list"
      sx={{
        overflowY: 'auto',
        scrollBehavior: 'smooth',
        '&::-webkit-scrollbar': {
          width: '8px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '4px',
        },
        '&::-webkit-scrollbar-thumb': {
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: '4px',
          '&:hover': {
            background: 'rgba(255, 255, 255, 0.3)',
          },
        },
      }}
    >
      {messages.map((message, index) => (
        <Box key={message.id}>
          {(index === 0 ||
            new Date(message.timestamp).toDateString() !==
              new Date(messages[index - 1].timestamp).toDateString()) && (
            <Typography
              variant="caption"
              sx={{
                display: 'block',
                textAlign: 'center',
                color: 'text.secondary',
                my: 2,
              }}
            >
              {new Date(message.timestamp).toLocaleDateString()}
            </Typography>
          )}
          <Box sx={{ position: 'relative' }}>
            <Message
              text={message.text}
              sender={message.sender}
              isError={message.isError}
            />
            <Typography
              variant="caption"
              sx={{
                position: 'absolute',
                bottom: -4,
                [message.sender === 'user' ? 'left' : 'right']: 12,
                color: 'text.disabled',
                fontSize: '0.7rem',
              }}
            >
              {formatTimestamp(message.timestamp)}
            </Typography>
          </Box>
        </Box>
      ))}
      <div ref={messagesEndRef} />
    </Box>
  );
};

export default MessageList;