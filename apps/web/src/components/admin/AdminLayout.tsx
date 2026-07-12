import React from 'react';
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItem, ListItemButton,
  ListItemIcon, ListItemText, Divider, Avatar, Chip, Button, IconButton, Tooltip,
  Snackbar, Alert, Badge
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import SecurityIcon from '@mui/icons-material/Security';
import MemoryIcon from '@mui/icons-material/Memory';
import CodeIcon from '@mui/icons-material/Code';
import TuneIcon from '@mui/icons-material/Tune';
import ScienceIcon from '@mui/icons-material/Science';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import HistoryIcon from '@mui/icons-material/History';
import SettingsIcon from '@mui/icons-material/Settings';
import TerminalIcon from '@mui/icons-material/Terminal';
import LogoutIcon from '@mui/icons-material/Logout';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import NotificationsIcon from '@mui/icons-material/Notifications';
import { useRouter } from 'next/router';
import { AdminThemeProvider, useAdminTheme } from './AdminThemeContext';

const drawerWidth = 240;

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactElement;
  match: RegExp;
}

const SIDEBAR_ITEMS: NavItem[] = [
  { path: '/admin/dashboard', label: 'Dashboard', icon: <DashboardIcon fontSize="small" />, match: /^\/admin\/dashboard/ },
  { path: '/admin/users', label: 'Users', icon: <PeopleIcon fontSize="small" />, match: /^\/admin\/users/ },
  { path: '/admin/roles', label: 'Roles', icon: <SecurityIcon fontSize="small" />, match: /^\/admin\/roles/ },
  { path: '/admin/models', label: 'Models', icon: <MemoryIcon fontSize="small" />, match: /^\/admin\/models/ },
  { path: '/admin/prompts', label: 'Prompt Templates', icon: <CodeIcon fontSize="small" />, match: /^\/admin\/prompts/ },
  { path: '/admin/thresholds', label: 'Thresholds', icon: <TuneIcon fontSize="small" />, match: /^\/admin\/thresholds/ },
  { path: '/admin/experiments', label: 'Experiments', icon: <ScienceIcon fontSize="small" />, match: /^\/admin\/experiments/ },
  { path: '/admin/analytics', label: 'Analytics', icon: <AnalyticsIcon fontSize="small" />, match: /^\/admin\/analytics/ },
  { path: '/admin/health', label: 'System Health', icon: <MonitorHeartIcon fontSize="small" />, match: /^\/admin\/health/ },
  { path: '/admin/audit', label: 'Audit Logs', icon: <HistoryIcon fontSize="small" />, match: /^\/admin\/audit/ },
  { path: '/admin/settings', label: 'Settings', icon: <SettingsIcon fontSize="small" />, match: /^\/admin\/settings/ },
  { path: '/admin/backend', label: 'Backend', icon: <TerminalIcon fontSize="small" />, match: /^\/admin\/backend/ },
];

const AdminWorkspace: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const router = useRouter();
  const { isDark, toggleTheme, colors } = useAdminTheme();
  const [toast, setToast] = React.useState<{ open: boolean; message: string; severity: 'success' | 'info' | 'warning' | 'error' }>({
    open: false, message: '', severity: 'info'
  });

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('userRole');
    document.cookie = 'user_role=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
    window.location.href = '/login';
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: colors.bg, color: colors.text }}>
      {/* Top Navbar — Identical style as Editor Dashboard TopNavbar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: `calc(100% - ${drawerWidth}px)`,
          ml: `${drawerWidth}px`,
          bgcolor: colors.panel,
          color: colors.text,
          borderBottom: `1px solid ${colors.border}`,
          zIndex: 1200,
          backdropFilter: 'blur(8px)',
        }}
      >
        <Toolbar sx={{ minHeight: '52px !important', px: 3, gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, flexGrow: 1 }}>
            <Typography variant="h6" sx={{ fontSize: '0.95rem', fontWeight: 700, color: colors.text, letterSpacing: '-0.01em' }}>
              AI Governance & Admin Portal
            </Typography>
          </Box>

          {/* Right Controls */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {/* Green ACTIVE badge exactly as requested */}
            <Chip
              label="ACTIVE"
              color="success"
              size="small"
              sx={{ fontWeight: 800, fontSize: '0.65rem', height: 22, px: 0.5 }}
            />

            {/* Dark / Light toggle button beside the green ACTIVE badge! */}
            <Tooltip title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'} arrow>
              <IconButton
                onClick={toggleTheme}
                size="small"
                sx={{
                  color: colors.text,
                  bgcolor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  border: `1px solid ${colors.border}`,
                  p: 0.8,
                  transition: 'all 0.2s ease',
                  '&:hover': { bgcolor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)', transform: 'scale(1.05)' }
                }}
              >
                {isDark ? <LightModeIcon fontSize="small" sx={{ color: '#fbbf24' }} /> : <DarkModeIcon fontSize="small" sx={{ color: '#3b82f6' }} />}
              </IconButton>
            </Tooltip>

            <Tooltip title="Notifications" arrow>
              <IconButton size="small" sx={{ color: colors.muted }}>
                <Badge badgeContent={3} color="error" sx={{ '& .MuiBadge-badge': { fontSize: '0.55rem', height: 14, minWidth: 14 } }}>
                  <NotificationsIcon fontSize="small" />
                </Badge>
              </IconButton>
            </Tooltip>

            <Box sx={{ width: 1, height: 24, bgcolor: colors.border, mx: 0.5 }} />

            {/* User Profile */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ textAlign: 'right', display: { xs: 'none', sm: 'block' } }}>
                <Typography sx={{ fontSize: '0.72rem', fontWeight: 700, color: colors.text, lineHeight: 1.2 }}>
                  System Administrator
                </Typography>
                <Chip
                  label="Super Admin"
                  size="small"
                  sx={{
                    height: 16, fontSize: '0.58rem', fontWeight: 700,
                    bgcolor: 'rgba(37,99,235,0.15)', color: '#60a5fa',
                    border: '1px solid rgba(37,99,235,0.3)',
                  }}
                />
              </Box>
              <Avatar
                sx={{
                  width: 32, height: 32, bgcolor: colors.primary,
                  fontSize: '0.8rem', fontWeight: 700,
                  boxShadow: '0 0 10px rgba(59,130,246,0.4)'
                }}
              >
                AD
              </Avatar>
            </Box>

            <Tooltip title="Logout" arrow>
              <IconButton size="small" onClick={handleLogout} sx={{ color: colors.danger, ml: 0.5 }}>
                <LogoutIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Sidebar — Identical style as Editor Dashboard drawer, suggested order */}
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: colors.drawerBg,
            color: colors.text,
            borderRight: `1px solid ${colors.border}`,
            transition: 'all 0.25s ease',
          },
        }}
        variant="permanent"
        anchor="left"
      >
        <Toolbar sx={{ minHeight: '52px !important', px: 2, borderBottom: `1px solid ${colors.border}` }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
            <Box sx={{
              width: 30, height: 30, borderRadius: '6px',
              background: `linear-gradient(135deg, ${colors.primary} 0%, #6366f1 100%)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '14px', fontWeight: 800, color: '#fff', flexShrink: 0,
              boxShadow: `0 0 12px rgba(37,99,235,0.5)`,
            }}>
              U
            </Box>
            <Box>
              <Typography sx={{ fontSize: '0.8rem', fontWeight: 800, color: colors.text, lineHeight: 1.1 }}>
                UJA Editorial
              </Typography>
              <Typography sx={{ fontSize: '0.6rem', color: colors.muted, letterSpacing: '0.04em', fontWeight: 600 }}>
                AI GOVERNANCE
              </Typography>
            </Box>
          </Box>
        </Toolbar>

        <Box sx={{ overflowY: 'auto', py: 1.5, px: 1 }}>
          <List disablePadding sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {SIDEBAR_ITEMS.map((item) => {
              const isSelected = item.match.test(router.pathname);
              return (
                <ListItem key={item.path} disablePadding>
                  <ListItemButton
                    selected={isSelected}
                    onClick={() => router.push(item.path)}
                    sx={{
                      borderRadius: 1.5,
                      py: 0.9,
                      px: 1.5,
                      transition: 'all 0.15s ease',
                      '&.Mui-selected': {
                        bgcolor: isDark ? 'rgba(59, 130, 246, 0.18)' : 'rgba(37, 99, 235, 0.1)',
                        color: isDark ? '#60a5fa' : '#1d4ed8',
                        borderLeft: `3px solid ${colors.primary}`,
                      },
                      '&:hover': {
                        bgcolor: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.04)',
                      },
                    }}
                  >
                    <ListItemIcon sx={{
                      minWidth: 32,
                      color: isSelected ? (isDark ? '#60a5fa' : '#1d4ed8') : colors.muted
                    }}>
                      {item.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={item.label}
                      sx={{
                        '& .MuiTypography-root': {
                          fontSize: '0.82rem',
                          fontWeight: isSelected ? 700 : 500,
                          color: isSelected ? (isDark ? '#60a5fa' : '#1d4ed8') : colors.text,
                        }
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </Box>
      </Drawer>

      {/* Main Content Workspace */}
      <Box component="main" sx={{ flexGrow: 1, p: 3, pt: 8, width: `calc(100% - ${drawerWidth}px)` }}>
        {children}
      </Box>

      {/* Global Toast Notification */}
      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={() => setToast({ ...toast, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setToast({ ...toast, open: false })} severity={toast.severity} sx={{ width: '100%', fontWeight: 600, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminWorkspace>{children}</AdminWorkspace>;
}
