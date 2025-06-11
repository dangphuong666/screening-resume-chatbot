import React from 'react';
import { Container, CssBaseline, ThemeProvider, createTheme, AppBar, Toolbar, Typography, Box } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import Chat from './components/Chat';
import './App.css';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1976d2',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <AppBar position="static" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Toolbar>
            <SmartToyIcon sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              AI Chat Assistant
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Powered by Nebius AI
            </Typography>
          </Toolbar>
        </AppBar>
        <Container 
          maxWidth="md" 
          sx={{ 
            flex: 1, 
            py: 4, 
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Chat />
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
