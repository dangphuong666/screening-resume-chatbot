import React, { useState, useRef } from 'react';
import { Snackbar, Alert } from '@mui/material';
import axios from 'axios';
import './FileUpload.css';

const FileUpload = React.forwardRef(({ onUploadSuccess, onUploadComplete }, ref) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  React.useImperativeHandle(ref, () => ({
    click: () => {
      fileInputRef.current?.click();
    }
  }));

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    const invalidFiles = files.filter(file => file.type !== 'application/pdf');
    if (invalidFiles.length > 0) {
      setError('Please upload PDF files only');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const results = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await axios.post('http://localhost:5000/upload-pdf', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(progress);
          },
        });

        if (response.data) {
          results.push({
            filename: file.name,
            success: true,
            message: response.data.message
          });
        }
      }
      
      setUploading(false);
      onUploadSuccess && onUploadSuccess(results);
      onUploadComplete && onUploadComplete(); // Trigger stats refresh
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to upload file');
      setUploading(false);
    } finally {
      setUploadProgress(0);
      event.target.value = ''; // Reset file input
    }
  };

  return (
    <div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        multiple
        onChange={handleFileUpload}
        style={{ display: 'none' }}
      />
      {uploading && (
        <div>
          <div className="upload-progress">
            <div 
              className="upload-progress-bar" 
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <div className="upload-status">
            Uploading... {uploadProgress}%
          </div>
        </div>
      )}
      {error && (
        <Snackbar
          open={!!error}
          autoHideDuration={4000}
          onClose={() => setError(null)}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert onClose={() => setError(null)} severity="error" variant="filled">
            {error}
          </Alert>
        </Snackbar>
      )}
    </div>
  );
});

export default FileUpload;
