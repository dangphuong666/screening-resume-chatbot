import { 
  ThemeProvider, 
  createTheme, 
  CssBaseline, 
  Box, 
  Container, 
  Typography, 
  Paper, 
  Button, 
  AppBar, 
  Toolbar,
  CircularProgress,
  Alert
} from '@mui/material';
import React, { useState, useEffect } from 'react';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import Chat from './components/Chat';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Theme configuration
  const theme = createTheme({
    palette: {
      mode: 'light',
      primary: {
        main: '#2196f3',
      },
    },
  });

  const fetchChatHistory = async () => {
    try {
      const response = await fetch('http://localhost:5000/chat-history', {
        credentials: 'include'
      });
      const data = await response.json();
      console.log('Received chat history:', data);  // Debug log
      if (data.error) {
        console.error('Server error:', data.error);
        return;
      }
      setChatHistory(data.history || []);
    } catch (error) {
      console.error('Error fetching chat history:', error);
    }
  };

  useEffect(() => {
    // Check URL for errors
    const params = new URLSearchParams(window.location.search);
    const error = params.get('error');
    if (error) {
      console.error('Authentication error:', error);
      setAuthError(error);
      setIsLoading(false);
      // Clear the error from URL
      window.history.replaceState({}, document.title, window.location.pathname);
      return;
    }

    // Check authentication status
    fetch('http://localhost:5000/api/check-auth', {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log('Auth status response:', data);
      if (data.authenticated && data.user) {
        setIsAuthenticated(true);
        setUser(data.user);
        return fetchChatHistory();
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      setIsAuthenticated(false);
      setUser(null);
      setAuthError(error.message);
    })
    .finally(() => {
      setIsLoading(false);
    });
  }, []);

  const handleLogin = () => {
    setIsLoading(true);
    window.location.href = 'http://localhost:5000/login';
  };

  const handleLogout = async () => {
    try {
      await fetch('http://localhost:5000/logout', {
        credentials: 'include'
      });
      setIsAuthenticated(false);
      setUser(null);
      setChatHistory([]);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  if (isLoading) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box 
          sx={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)'
          }}
        >
          <CircularProgress />
        </Box>
      </ThemeProvider>
    );
  }

  if (!isAuthenticated) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box 
          sx={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
            padding: 3,
          }}
        >
          <Paper
            elevation={0}
            sx={{
              p: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              maxWidth: 400,
              width: '100%',
              borderRadius: 2,
              background: 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 500 }}>
              Welcome
            </Typography>
            
            {authError && (
              <Alert severity="error" sx={{ mb: 3, width: '100%' }}>
                {(() => {
                  if (authError.includes('token_exchange_failed')) {
                    return 'Failed to complete login. This might be due to an expired session. Please try again.';
                  } else if (authError.includes('invalid_state')) {
                    return 'Session validation failed. Please try logging in again.';
                  } else if (authError.includes('oauth_')) {
                    return 'Google login failed. Please try again.';
                  } else {
                    return `Login error: ${authError}`;
                  }
                })()}
              </Alert>
            )}

            <Button
              onClick={handleLogin}
              variant="outlined"
              size="large"
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                bgcolor: 'white',
                border: '1px solid #e0e0e0',
                borderRadius: 2,
                py: 1.5,
                px: 3,
                color: 'text.primary',
                fontWeight: 500,
                transition: 'all 0.2s ease',
                boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                '&:hover': {
                  bgcolor: 'white',
                  borderColor: '#bdbdbd',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  transform: 'translateY(-1px)',
                },
              }}
            >
              <img src="https://www.google.com/favicon.ico" alt="Google" style={{ width: 20, height: 20 }} />
              <span>Continue with Google</span>
            </Button>
          </Paper>
        </Box>
      </ThemeProvider>
    );
  }

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
            {user && (
              <Typography variant="body2" sx={{ mr: 2 }}>
                {user.email}
              </Typography>
            )}
            <Button color="inherit" onClick={handleLogout}>
              Logout
            </Button>
          </Toolbar>
        </AppBar>
        <Container maxWidth="md" sx={{ flex: 1, py: 4 }}>
          <Chat history={chatHistory} onNewChat={fetchChatHistory} />
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
