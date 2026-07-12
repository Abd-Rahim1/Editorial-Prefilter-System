import React from 'react';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Typography, Paper, Box } from '@mui/material';

export default function EditorAnalyticsPage() {
  return (
    <DashboardLayout role="editor">
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 4, color: 'text.primary' }}>Editorial Analytics</Typography>
      
      <Box sx={{ display: 'flex', gap: 3, mb: 4, flexWrap: 'wrap' }}>
        <Paper sx={{ p: 3, flex: '1 1 250px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>Processed This Week</Typography>
          <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>124</Typography>
        </Paper>
        <Paper sx={{ p: 3, flex: '1 1 250px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>Average Triage Time</Typography>
          <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>4.2s</Typography>
        </Paper>
        <Paper sx={{ p: 3, flex: '1 1 250px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>Rejection Rate</Typography>
          <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>38%</Typography>
        </Paper>
      </Box>

      <Paper sx={{ 
        p: 4, 
        height: 350, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' 
      }}>
        <Typography color="text.secondary">[ Pipeline Performance Chart Placeholder ]</Typography>
      </Paper>
    </DashboardLayout>
  );
}
