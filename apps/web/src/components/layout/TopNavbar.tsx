import React from 'react';
import {
  AppBar, Toolbar, Box, Typography, Tabs, Tab, IconButton,
  Avatar, Chip, Badge, Tooltip,
} from '@mui/material';
import NotificationsOutlinedIcon from '@mui/icons-material/NotificationsOutlined';
import SettingsOutlinedIcon       from '@mui/icons-material/SettingsOutlined';
import DashboardOutlinedIcon      from '@mui/icons-material/DashboardOutlined';
import ListAltOutlinedIcon        from '@mui/icons-material/ListAltOutlined';
import BarChartOutlinedIcon       from '@mui/icons-material/BarChartOutlined';
import TuneOutlinedIcon           from '@mui/icons-material/TuneOutlined';
import HistoryOutlinedIcon        from '@mui/icons-material/HistoryOutlined';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { COLORS } from '../../styles/theme';

interface NavItem {
  label:  string;
  href:   string;
  icon:   React.ReactElement;
  match:  RegExp;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Cockpit',          href: '/',                    icon: <DashboardOutlinedIcon fontSize="small" />, match: /^\/$/ },
  { label: 'Queue',            href: '/editor/queue',        icon: <ListAltOutlinedIcon   fontSize="small" />, match: /^\/editor\/queue/ },
  { label: 'Analytics',        href: '/editor/analytics',    icon: <BarChartOutlinedIcon  fontSize="small" />, match: /^\/editor\/analytics/ },
  { label: 'Threshold Config', href: '/admin/thresholds',    icon: <TuneOutlinedIcon      fontSize="small" />, match: /^\/admin\/thresholds/ },
  { label: 'Audit Logs',       href: '/admin/audit',         icon: <HistoryOutlinedIcon   fontSize="small" />, match: /^\/admin\/audit/ },
];

export default function TopNavbar() {
  const router = useRouter();
  const activeIdx = NAV_ITEMS.findIndex(n => n.match.test(router.pathname));

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        bgcolor: COLORS.panel,
        borderBottom: `1px solid ${COLORS.border}`,
        zIndex: 1200,
        backdropFilter: 'blur(8px)',
      }}
    >
      <Toolbar sx={{ minHeight: '52px !important', px: 2, gap: 2 }}>

        {/* Logo + Title */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, mr: 2 }}>
          <Box sx={{
            width: 30, height: 30, borderRadius: '6px',
            background: `linear-gradient(135deg, ${COLORS.primary} 0%, #6366f1 100%)`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '14px', fontWeight: 800, color: '#fff', flexShrink: 0,
            boxShadow: `0 0 12px rgba(37,99,235,0.5)`,
          }}>
            U
          </Box>
          <Box>
            <Typography sx={{
              fontSize: '0.78rem', fontWeight: 700, color: COLORS.text, lineHeight: 1.1,
              letterSpacing: '-0.01em',
            }}>
              UJA Editorial
            </Typography>
            <Typography sx={{ fontSize: '0.58rem', color: COLORS.muted, letterSpacing: '0.04em' }}>
              PRE-FILTER COCKPIT
            </Typography>
          </Box>
        </Box>

        {/* Navigation Tabs */}
        <Tabs
          value={activeIdx === -1 ? 0 : activeIdx} // ⚡ FIX: Numeric boundary fallback avoids Boolean/Signature overloads
          sx={{ 
            flex: 1, 
            minHeight: 52,
            '& .MuiTabs-flexContainer': {
              height: 52,
            },
            // ⚡ FIX: Style element indicators safely without using the deprecated prop
            '& .MuiTabs-indicator': {
              height: 2,
              bottom: 0,
              bgcolor: COLORS.primary,
            }
          }}
        >
          {NAV_ITEMS.map((item, idx) => (
            <Tab
              key={idx}
              component={Link}
              href={item.href}
              label={item.label}
              icon={item.icon}
              iconPosition="start"
              sx={{
                minHeight: 52,
                fontSize: '0.72rem',
                textTransform: 'none',
                fontWeight: activeIdx === idx ? 700 : 500,
                color: activeIdx === idx ? COLORS.text : COLORS.muted,
                gap: 0.8,
                '&.Mui-selected': {
                  color: COLORS.text,
                },
              }}
            />
          ))}
        </Tabs>

        {/* Right-side controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Tooltip title="Notifications" arrow>
            <IconButton size="small" sx={{ color: COLORS.muted }}>
              <Badge badgeContent={3} color="error" sx={{ '& .MuiBadge-badge': { fontSize: '0.55rem', height: 14, minWidth: 14 } }}>
                <NotificationsOutlinedIcon fontSize="small" />
              </Badge>
            </IconButton>
          </Tooltip>

          <Tooltip title="System settings" arrow>
            <IconButton size="small" sx={{ color: COLORS.muted }}>
              <SettingsOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Box sx={{ width: 1, height: 24, bgcolor: COLORS.border, mx: 1.5 }} />

          {/* User Profile Hook */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }}>
            <Box sx={{ textAlign: 'right' }}>
              <Typography sx={{ fontSize: '0.7rem', fontWeight: 600, color: COLORS.text, lineHeight: 1.2 }}>
                Editor Admin
              </Typography>
              <Chip
                label="Academic Editor"
                size="small"
                sx={{
                  height: 14, fontSize: '0.55rem', fontWeight: 700,
                  bgcolor: 'rgba(37,99,235,0.15)', color: '#60a5fa',
                  border: '1px solid rgba(37,99,235,0.3)',
                }}
              />
            </Box>
            <Avatar
              sx={{
                width: 30, height: 30, bgcolor: COLORS.primary,
                fontSize: '0.75rem', fontWeight: 700,
              }}
            >
              EA
            </Avatar>
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
}