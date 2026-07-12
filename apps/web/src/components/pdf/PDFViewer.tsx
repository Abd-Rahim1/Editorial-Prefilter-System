import React from 'react';
import { Box, Typography } from '@mui/material';
import PictureAsPdfOutlinedIcon from '@mui/icons-material/PictureAsPdfOutlined';
import { COLORS } from '../../styles/theme';

interface PDFViewerProps {
  file: File | null;
}

export default function PDFViewer({ file }: PDFViewerProps) {
  const url = React.useMemo(
    () => (file ? URL.createObjectURL(file) : null),
    [file],
  );

  React.useEffect(() => {
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [url]);

  if (!url) {
    return (
      <Box sx={{
        flex: 1, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        bgcolor: 'rgba(255,255,255,0.01)',
        border: `1px dashed ${COLORS.border}`,
        borderRadius: 2, gap: 1.5, py: 6,
      }}>
        <Box sx={{
          width: 48, height: 48, borderRadius: 2,
          bgcolor: 'rgba(37,99,235,0.1)', border: `1px solid ${COLORS.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <PictureAsPdfOutlinedIcon sx={{ color: COLORS.muted, fontSize: 24 }} />
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: COLORS.muted, mb: 0.3 }}>
            No manuscript loaded
          </Typography>
          <Typography sx={{ fontSize: '0.68rem', color: '#475569' }}>
            Upload a PDF to view it here
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', borderRadius: 2, overflow: 'hidden', border: `1px solid ${COLORS.border}` }}>
      {/* Toolbar bar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', gap: 1, px: 1.5, py: 0.8,
        bgcolor: 'rgba(255,255,255,0.03)', borderBottom: `1px solid ${COLORS.border}`,
      }}>
        <PictureAsPdfOutlinedIcon sx={{ fontSize: 14, color: COLORS.danger }} />
        <Typography sx={{ fontSize: '0.68rem', fontWeight: 600, color: COLORS.text, flex: 1 }} noWrap>
          {file?.name}
        </Typography>
        <Typography sx={{ fontSize: '0.6rem', color: COLORS.muted }}>
          {file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : ''}
        </Typography>
      </Box>

      {/* Embed */}
      <Box sx={{ flex: 1, position: 'relative' }}>
        <embed
          src={`${url}#toolbar=0&navpanes=0&view=FitH`}
          type="application/pdf"
          style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
        />
      </Box>
    </Box>
  );
}
