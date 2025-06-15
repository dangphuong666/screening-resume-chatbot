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
      // Force immediate scroll to bottom without animation for best UX
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
      previousScrollHeight.current = scrollContainer.scrollHeight;
    }
  };

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    console.log('MessageList received messages:', messages);
    scrollToBottom();
  }, [messages]);

  // Ensure scroll position stays at bottom when window is resized
  useEffect(() => {
    const handleResize = () => scrollToBottom();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <Box
      ref={containerRef}
      className="message-list"
      sx={{
        flex: 1,
        overflowY: 'auto',
        scrollBehavior: 'auto', // Changed to auto for more responsive scrolling
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: 'calc(100vh - 200px)', // Limit height to prevent overflow
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
        <Box
          key={message.id}
          sx={{
            mb: 2,
            '&:last-of-type': {
              mb: 0
            }
          }}
        >
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
          <Message
            text={message.text}
            sender={message.sender}
            isError={message.isError}
            isLoading={message.isLoading}
          />
        </Box>
      ))}
      <div ref={messagesEndRef} />
    </Box>
  );
};

export default MessageList;