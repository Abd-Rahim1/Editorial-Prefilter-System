import React, { useState } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import type { DropzoneProps } from '../../types/dashboard';

const DragAndDropZone: React.FC<DropzoneProps> = ({ onFileSelected, loading }) => {
  const [dragActive, setDragActive] = useState<boolean>(false);

  // ── Event handlers ───────────────────────────────────────
  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>): void => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (): void => {
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>): void => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onFileSelected(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  };

  // ── Render ───────────────────────────────────────────────
  return (
    <Box
      component="label"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      sx={{ display: 'block', width: '100%', cursor: loading ? 'not-allowed' : 'pointer' }}
    >
      <input
        type="file"
        accept="application/pdf"
        hidden
        disabled={loading}
        onChange={handleChange}
      />

      <Paper
        variant="outlined"
        sx={{
          p: 2.5,
          textAlign: 'center',
          borderRadius: 2,
          transition: 'all 0.2s ease',
          bgcolor: dragActive ? 'action.selected' : 'grey.50',
          border: dragActive ? '2px dashed #1e3a8a' : '2px dashed #cbd5e1',
          '&:hover': { bgcolor: 'action.hover', borderColor: '#1e3a8a' },
        }}
      >
        <CloudUploadIcon color="primary" sx={{ fontSize: 32, mb: 0.5 }} />
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          Drag &amp; Drop Manuscript PDF Here
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
          Runs cross-layer tokenization models
        </Typography>
      </Paper>
    </Box>
  );
};

export default DragAndDropZone;
