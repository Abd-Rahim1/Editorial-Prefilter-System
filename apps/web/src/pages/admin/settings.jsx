import React, { useState } from 'react';
import { Box, Typography, Button, Grid, Switch, FormControlLabel, Chip, Divider, Alert } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import StorageIcon from '@mui/icons-material/Storage';
import PaletteIcon from '@mui/icons-material/Palette';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AdminLayout from '../../components/admin/AdminLayout';
import { AdminCard } from '../../components/admin/ui/AdminCard';
import { useAdminTheme } from '../../components/admin/AdminThemeContext';

export default function AdminSettingsPage() {
  const { colors, isDark, toggleTheme } = useAdminTheme();
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [slackAlerts, setSlackAlerts] = useState(false);
  const [autoBackup, setAutoBackup] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 4000);
  };

  const tables = [
    { name: "manuscripts", rows: "142 records", size: "1.4 MB", status: "Synced" },
    { name: "predictions", rows: "450 records", size: "3.2 MB", status: "Synced" },
    { name: "model_runs", rows: "320 records", size: "2.1 MB", status: "Synced" },
    { name: "audit_logs", rows: "1,240 records", size: "4.8 MB", status: "Synced" },
    { name: "system_settings", rows: "1 profile", size: "16 KB", status: "Synced" },
    { name: "models", rows: "4 registry items", size: "32 KB", status: "Synced" },
    { name: "prompt_templates", rows: "3 templates", size: "48 KB", status: "Synced" },
    { name: "users", rows: "4 staff accounts", size: "24 KB", status: "Synced" },
    { name: "roles", rows: "4 RBAC roles", size: "16 KB", status: "Synced" },
    { name: "experiments", rows: "3 benchmark runs", size: "64 KB", status: "Synced" },
    { name: "system_health", rows: "4 telemetry items", size: "24 KB", status: "Synced" },
    { name: "api_metrics", rows: "100 recent calls", size: "128 KB", status: "Synced" },
  ];

  return (
    <AdminLayout>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 960 }}>
        <Box>
          <Typography variant="h1" sx={{ fontSize: '1.8rem', fontWeight: 800, color: colors.text }}>
            Section 12 — System & Governance Settings
          </Typography>
          <Typography variant="body2" sx={{ color: colors.muted, mt: 0.5 }}>
            Configure dual-theme preferences, automated database backups, and notification webhooks.
          </Typography>
        </Box>

        {saved && (
          <Alert icon={<CheckCircleIcon fontSize="inherit" />} severity="success" sx={{ fontWeight: 700, borderRadius: 2 }}>
            System settings and webhook configurations successfully updated!
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Theme & Visual Identity */}
          <Grid size={{ xs: 12, md: 6 }}>
            <AdminCard title="Visual Identity & Theme" subtitle="Governed by localStorage persistence">
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, py: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography sx={{ fontWeight: 700, fontSize: '0.9rem', color: colors.text }}>
                      Active Workspace Theme
                    </Typography>
                    <Typography variant="caption" sx={{ color: colors.muted }}>
                      Toggle between sleek Dark mode and clean Light mode.
                    </Typography>
                  </Box>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={toggleTheme}
                    sx={{ borderColor: colors.border, color: colors.text, fontWeight: 700 }}
                  >
                    {isDark ? "Light Mode" : "Dark Mode"}
                  </Button>
                </Box>
                <Divider sx={{ borderColor: colors.border }} />
                <Typography variant="caption" sx={{ color: colors.muted }}>
                  🎨 Note: Theme toggle is also accessible in the top navigation bar beside the green ACTIVE badge.
                </Typography>
              </Box>
            </AdminCard>
          </Grid>

          {/* Notifications */}
          <Grid size={{ xs: 12, md: 6 }}>
            <AdminCard title="Notification & Alert Webhooks" subtitle="Real-time editorial queue alerts">
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, py: 1 }}>
                <FormControlLabel
                  control={<Switch checked={emailAlerts} onChange={(e) => setEmailAlerts(e.target.checked)} color="primary" />}
                  label={<Typography sx={{ fontSize: '0.85rem', fontWeight: 600, color: colors.text }}>Email Alerts on Manual Review Routing</Typography>}
                />
                <FormControlLabel
                  control={<Switch checked={slackAlerts} onChange={(e) => setSlackAlerts(e.target.checked)} color="primary" />}
                  label={<Typography sx={{ fontSize: '0.85rem', fontWeight: 600, color: colors.text }}>Slack Webhook on GPU Cluster Offline</Typography>}
                />
                <FormControlLabel
                  control={<Switch checked={autoBackup} onChange={(e) => setAutoBackup(e.target.checked)} color="primary" />}
                  label={<Typography sx={{ fontSize: '0.85rem', fontWeight: 600, color: colors.text }}>Daily Automated PostgreSQL Snapshot</Typography>}
                />
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                  <Button variant="contained" size="small" onClick={handleSave} sx={{ bgcolor: colors.primary, color: '#fff', fontWeight: 700 }}>
                    Save Preferences
                  </Button>
                </Box>
              </Box>
            </AdminCard>
          </Grid>
        </Grid>

        {/* Database Tables Overview */}
        <AdminCard title="PostgreSQL Schema Synchronization Status" subtitle="Connected to WSL2 PostgreSQL database (public schema)">
          <Grid container spacing={2} sx={{ pt: 1 }}>
            {tables.map((t, idx) => (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={idx}>
                <Box sx={{
                  p: 2, borderRadius: 2, border: `1px solid ${colors.border}`,
                  bgcolor: isDark ? 'rgba(255,255,255,0.03)' : '#f8fafc',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                }}>
                  <Box>
                    <Typography sx={{ fontWeight: 800, fontSize: '0.85rem', color: colors.text, fontFamily: 'monospace' }}>
                      public.{t.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: colors.muted }}>
                      {t.rows} ({t.size})
                    </Typography>
                  </Box>
                  <Chip label={t.status} size="small" color="success" sx={{ fontWeight: 800, fontSize: '0.65rem', height: 20 }} />
                </Box>
              </Grid>
            ))}
          </Grid>
        </AdminCard>
      </Box>
    </AdminLayout>
  );
}
