import React, { useCallback } from 'react';
import { Box, Typography, Paper, CircularProgress } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined';
import { useDropzone } from 'react-dropzone';
import { COLORS } from '../../styles/theme';

interface UploadPanelProps {
  onFileSelected: (file: File) => void;
  loading: boolean;
  selectedFile: File | null;
}

export default function UploadPanel({ onFileSelected, loading, selectedFile }: UploadPanelProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      onFileSelected(acceptedFiles[0]);
    }
  }, [onFileSelected]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    disabled: loading,
    multiple: false
  });

  return (
    <Box>
      <Typography variant="overline" sx={{ display: 'block', mb: 1, px: 0.5 }}>
        Upload Manuscript
      </Typography>

      {/* Drop zone */}
      <Box {...getRootProps()} sx={{ display: 'block', cursor: loading ? 'wait' : 'pointer' }}>
        <input {...getInputProps()} />
        <Paper
          sx={{
            p: 3, 
            textAlign: 'center', 
            borderRadius: 2,
            border: '2px dashed',
            borderColor: isDragActive ? COLORS.primary : COLORS.border,
            bgcolor: isDragActive ? 'rgba(37,99,235,0.08)' : 'rgba(255,255,255,0.02)',
            transition: 'all 0.2s ease',
            '&:hover': { 
              borderColor: loading ? COLORS.border : COLORS.primary, 
              bgcolor: loading ? 'rgba(255,255,255,0.02)' : 'rgba(37,99,235,0.05)' 
            },
          }}
        >
          {loading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', my: 1 }}>
              <CircularProgress size={32} sx={{ color: COLORS.primary, mb: 1.5 }} />
              <Typography sx={{ fontSize: '0.72rem', fontWeight: 600, color: COLORS.primary }}>
                Uploading PDF...
              </Typography>
            </Box>
          ) : (
            <Box>
              <Box sx={{
                width: 40, height: 40, borderRadius: '50%',
                bgcolor: 'rgba(37,99,235,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                mx: 'auto', mb: 1.5,
              }}>
                <CloudUploadIcon sx={{ color: COLORS.primary, fontSize: 24 }} />
              </Box>
              <Typography sx={{ fontSize: '0.75rem', fontWeight: 600, color: COLORS.text, mb: 0.5 }}>
                {isDragActive ? 'Release to upload' : 'Drag & drop PDF here'}
              </Typography>
              <Typography sx={{ fontSize: '0.65rem', color: COLORS.muted }}>
                or click to browse files
              </Typography>
            </Box>
          )}
        </Paper>
      </Box>

      {/* Selected File Info */}
      {selectedFile && !loading && (
        <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1, p: 1.5, bgcolor: 'rgba(34, 197, 94, 0.1)', borderRadius: 1, border: `1px solid rgba(34, 197, 94, 0.3)` }}>
          <InsertDriveFileOutlinedIcon sx={{ fontSize: 18, color: COLORS.success }} />
          <Typography sx={{ fontSize: '0.7rem', color: COLORS.text, fontWeight: 500, flex: 1 }} noWrap>
            {selectedFile.name}
          </Typography>
          <Typography sx={{ fontSize: '0.65rem', color: COLORS.success, fontWeight: 600 }}>
            Ready
          </Typography>
        </Box>
      )}
    </Box>
  );
}
