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
      // Always scroll to new messages
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      previousScrollHeight.current = scrollContainer.scrollHeight;
    }
  };

  useEffect(() => {
    console.log('MessageList received messages:', messages);
    scrollToBottom();
  }, [messages]);

  return (
    <Box
      ref={containerRef}
      className="message-list"
      sx={{
        flex: 1,
        overflowY: 'auto',
        scrollBehavior: 'smooth',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column', // Standard top-to-bottom layout
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