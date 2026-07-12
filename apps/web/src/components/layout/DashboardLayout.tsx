import React from 'react';
import { 
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItem, ListItemButton, 
  ListItemIcon, ListItemText, Divider, Avatar, Chip, Button, IconButton, Tooltip 
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import SettingsIcon from '@mui/icons-material/Settings';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import AltRouteIcon from '@mui/icons-material/AltRoute';
import LogoutIcon from '@mui/icons-material/Logout';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import { useRouter } from 'next/router';
import { useAdminTheme } from '../admin/AdminThemeContext';

interface DashboardLayoutProps {
  children: React.ReactNode;
  role: 'editor' | 'admin';
}

const drawerWidth = 240;

export default function DashboardLayout({ children, role }: DashboardLayoutProps) {
  const router = useRouter();
  const { isDark, toggleTheme, colors } = useAdminTheme();

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('userRole');
    document.cookie = 'user_role=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
    window.location.href = '/login';
  };

  const navItem = (path: string, label: string, icon: React.ReactNode) => {
    const isSelected = router.pathname === path;
    return (
      <ListItem disablePadding>
        <ListItemButton 
          selected={isSelected} 
          onClick={() => router.push(path)}
          sx={{
            '&.Mui-selected': { bgcolor: colors.hover },
            '&.Mui-selected:hover': { bgcolor: colors.hover }
          }}
        >
          <ListItemIcon sx={{ color: isSelected ? colors.primary : colors.muted }}>
            {icon}
          </ListItemIcon>
          <ListItemText 
            primary={label} 
            sx={{ 
              '& .MuiTypography-root': { 
                fontWeight: isSelected ? 700 : 500,
                color: isSelected ? colors.primary : colors.text 
              } 
            }} 
          />
        </ListItemButton>
      </ListItem>
    );
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar 
        position="fixed" 
        sx={{ 
          width: `calc(100% - ${drawerWidth}px)`, 
          ml: `${drawerWidth}px`, 
          bgcolor: colors.panel, 
          color: colors.text, 
          boxShadow: 'none', 
          borderBottom: `1px solid ${colors.border}`,
          transition: 'all 0.25s ease'
        }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, fontWeight: 700, color: colors.text }}>
            {role === 'admin' ? 'Admin Dashboard' : 'Editor Workspace'}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip 
              label="ACTIVE" 
              color="success" 
              size="small" 
              sx={{ fontWeight: 'bold' }} 
            />

            {/* Theme Toggle */}
            <Tooltip title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'} arrow>
              <IconButton
                onClick={toggleTheme}
                size="small"
                aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                sx={{
                  color: colors.text,
                  bgcolor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  border: `1px solid ${colors.border}`,
                  p: 0.8,
                  transition: 'all 0.2s ease',
                  '&:hover': { 
                    bgcolor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)', 
                    transform: 'scale(1.05)' 
                  }
                }}
              >
                {isDark ? (
                  <LightModeIcon fontSize="small" sx={{ color: '#fbbf24' }} />
                ) : (
                  <DarkModeIcon fontSize="small" sx={{ color: '#3b82f6' }} />
                )}
              </IconButton>
            </Tooltip>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Avatar sx={{ width: 32, height: 32, bgcolor: colors.primary }}>
                {role === 'admin' ? 'A' : 'E'}
              </Avatar>
              <Typography variant="body2" sx={{ fontWeight: 600, color: colors.text }}>
                {role === 'admin' ? 'Admin User' : 'Editor User'}
              </Typography>
            </Box>
            <Button 
              variant="outlined" 
              color="inherit" 
              size="small" 
              startIcon={<LogoutIcon />} 
              onClick={handleLogout} 
              sx={{ ml: 2, borderColor: colors.border, color: colors.text }}
            >
              Logout
            </Button>
          </Box>
        </Toolbar>
      </AppBar>
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
            transition: 'all 0.25s ease'
          },
        }}
        variant="permanent"
        anchor="left"
      >
        <Toolbar>
          <Typography variant="h6" sx={{ fontWeight: 800, color: colors.text }}>Prefilter</Typography>
        </Toolbar>
        <Divider sx={{ borderColor: colors.border }} />
        <List>
          {role === 'editor' && (
            <>
              {navItem('/editor/queue', 'Editorial Tasks', <DashboardIcon />)}
              {navItem('/editor/upload', 'Ingest Manuscript', <UploadFileIcon />)}
              {navItem('/editor/analytics', 'Editorial Analytics', <AnalyticsIcon />)}
              {navItem('/editor/strategies', 'Strategies', <AccountTreeIcon />)}
              {navItem('/editor/workflow', 'Workflow', <AltRouteIcon />)}
            </>
          )}
          {role === 'admin' && (
            <>
              {navItem('/admin/settings', 'Admin Cockpit', <DashboardIcon />)}
              {navItem('/admin/thresholds', 'Policy Thresholds', <SettingsIcon />)}
              {navItem('/admin/models', 'Models & Runs', <AnalyticsIcon />)}
              {navItem('/admin/users', 'Users & Roles', <AccountTreeIcon />)}
              {navItem('/admin/audit', 'Audit Ledger', <AltRouteIcon />)}
            </>
          )}
        </List>
      </Drawer>
      <Box 
        component="main" 
        sx={{ 
          flexGrow: 1, 
          bgcolor: colors.bg, 
          p: 0, 
          minHeight: '100vh',
          transition: 'all 0.25s ease'
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}