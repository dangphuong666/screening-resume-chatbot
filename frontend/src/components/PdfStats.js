import React, { useState, useEffect } from 'react';
import { Paper, Typography, List, ListItem, ListItemText, Box } from '@mui/material';
import axios from 'axios';

const PdfStats = () => {
  const [stats, setStats] = useState({ total_count: 0, files: [] });
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    try {
      const response = await axios.get('http://localhost:5000/pdf-stats', { withCredentials: true });
      setStats(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  // Fetch stats on component mount and after each file upload
  useEffect(() => {
    fetchStats();
    // Set up polling to refresh stats every 5 seconds
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <Paper sx={{ p: 2, mt: 2, bgcolor: 'error.main', color: 'error.contrastText' }}>
        <Typography>Error loading PDF statistics: {error}</Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        PDF Statistics
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        Total PDFs: {stats.total_count}
      </Typography>
      <List>
        {Array.isArray(stats.files) && stats.files.map((file) => (
          <ListItem key={file.name}>
            <ListItemText
              primary={file.name}
              secondary={`Size: ${file.size_formatted}`}
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default PdfStats;
