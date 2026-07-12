import React from 'react';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Typography, Paper, Box, Button } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

export default function EditorUploadPage() {
  return (
    <DashboardLayout role="editor">
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 4, color: 'text.primary' }}>Ingest Manuscript</Typography>
      
      <Paper sx={{ 
        p: 6, 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        border: '2px dashed #cbd5e1', 
        bgcolor: '#ffffff', 
        boxShadow: 'none', 
        maxWidth: 800 
      }}>
        <CloudUploadIcon sx={{ fontSize: 48, color: '#94a3b8', mb: 2 }} />
        <Typography variant="h6" color="text.primary" sx={{ mb: 1 }}>Drag and drop PDF here</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>or click to browse files (max 50MB)</Typography>
        <Button variant="contained" size="large">Select PDF</Button>
      </Paper>
    </DashboardLayout>
  );
}
