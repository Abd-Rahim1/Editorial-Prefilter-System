import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { createTheme, ThemeProvider as MuiThemeProvider, alpha } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

export interface AdminThemeColors {
  bg: string;
  panel: string;
  border: string;
  text: string;
  muted: string;
  primary: string;
  success: string;
  warning: string;
  danger: string;
  highlight: string;
  drawerBg: string;
  hover: string;
}

interface AdminThemeContextType {
  isDark: boolean;
  toggleTheme: () => void;
  colors: AdminThemeColors;
}

const AdminThemeContext = createContext<AdminThemeContextType | undefined>(undefined);

export const useAdminTheme = () => {
  const context = useContext(AdminThemeContext);
  if (!context) {
    throw new Error('useAdminTheme must be used within an AdminThemeProvider');
  }
  return context;
};

export const AdminThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isDark, setIsDark] = useState<boolean>(true);

  useEffect(() => {
    const saved = localStorage.getItem('admin_theme');
    if (saved !== null) {
      setIsDark(saved === 'dark');
    }
  }, []);

  const toggleTheme = () => {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem('admin_theme', next ? 'dark' : 'light');
      return next;
    });
  };

  const colors: AdminThemeColors = useMemo(() => {
    if (isDark) {
      return {
        bg: '#0f172a',
        panel: '#1e293b',
        border: '#334155',
        text: '#f8fafc',
        muted: '#94a3b8',
        primary: '#3b82f6',
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
        highlight: '#1d4ed8',
        drawerBg: '#0f172a',
        hover: 'rgba(59, 130, 246, 0.15)',
      };
    } else {
      return {
        bg: '#f8fafc',
        panel: '#ffffff',
        border: '#e2e8f0',
        text: '#0f172a',
        muted: '#64748b',
        primary: '#2563eb',
        success: '#16a34a',
        warning: '#d97706',
        danger: '#dc2626',
        highlight: '#3b82f6',
        drawerBg: '#ffffff',
        hover: 'rgba(37, 99, 235, 0.08)',
      };
    }
  }, [isDark]);

  const muiTheme = useMemo(() => {
    return createTheme({
      palette: {
        mode: isDark ? 'dark' : 'light',
        background: {
          default: colors.bg,
          paper: colors.panel,
        },
        primary: { main: colors.primary },
        success: { main: colors.success },
        warning: { main: colors.warning },
        error: { main: colors.danger },
        text: {
          primary: colors.text,
          secondary: colors.muted,
        },
        divider: colors.border,
      },
      typography: {
        fontFamily: '"Inter", "Roboto", -apple-system, BlinkMacSystemFont, sans-serif',
        h1: { fontSize: '1.8rem', fontWeight: 700, letterSpacing: '-0.02em', color: colors.text },
        h2: { fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-0.01em', color: colors.text },
        h3: { fontSize: '1.2rem', fontWeight: 600, color: colors.text },
        h4: { fontSize: '1.05rem', fontWeight: 600, color: colors.text },
        h5: { fontSize: '0.95rem', fontWeight: 600, color: colors.text },
        h6: { fontSize: '0.85rem', fontWeight: 600, color: colors.text },
        body1: { fontSize: '0.875rem', lineHeight: 1.6, color: colors.text },
        body2: { fontSize: '0.8rem', lineHeight: 1.5, color: colors.text },
        caption: { fontSize: '0.72rem', color: colors.muted },
        button: { textTransform: 'none', fontWeight: 600 },
      },
      shape: { borderRadius: 8 },
      components: {
        MuiCssBaseline: {
          styleOverrides: `
            body {
              background-color: ${colors.bg};
              color: ${colors.text};
              transition: background-color 0.25s ease, color 0.25s ease;
            }
            * {
              box-sizing: border-box;
              transition: border-color 0.25s ease, background-color 0.25s ease;
            }
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: ${colors.bg}; }
            ::-webkit-scrollbar-thumb { background: ${colors.border}; border-radius: 4px; }
            ::-webkit-scrollbar-thumb:hover { background: ${colors.muted}; }
          `,
        },
        MuiPaper: {
          defaultProps: { elevation: 0 },
          styleOverrides: {
            root: {
              backgroundColor: colors.panel,
              border: `1px solid ${colors.border}`,
              color: colors.text,
              borderRadius: 8,
              transition: 'all 0.25s ease',
            },
          },
        },
        MuiCard: {
          defaultProps: { elevation: 0 },
          styleOverrides: {
            root: {
              backgroundColor: colors.panel,
              border: `1px solid ${colors.border}`,
              borderRadius: 8,
              color: colors.text,
              transition: 'all 0.25s ease',
              '&:hover': {
                borderColor: isDark ? '#475569' : '#cbd5e1',
                boxShadow: `0 4px 12px ${alpha('#000', isDark ? 0.35 : 0.06)}`,
              },
            },
          },
        },
        MuiButton: {
          styleOverrides: {
            root: { borderRadius: 6, fontWeight: 600, textTransform: 'none' },
            outlined: { borderColor: colors.border, color: colors.text },
          },
        },
        MuiChip: {
          styleOverrides: {
            root: { fontWeight: 600, fontSize: '0.68rem', borderRadius: 6 },
          },
        },
        MuiTableCell: {
          styleOverrides: {
            root: { borderColor: colors.border, color: colors.text, fontSize: '0.8rem' },
            head: { fontWeight: 700, color: colors.muted, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', backgroundColor: isDark ? '#111827' : '#f1f5f9' },
          },
        },
        MuiDialog: {
          styleOverrides: {
            paper: { backgroundColor: colors.panel, border: `1px solid ${colors.border}`, color: colors.text },
          },
        },
      },
    });
  }, [isDark, colors]);

  return (
    <AdminThemeContext.Provider value={{ isDark, toggleTheme, colors }}>
      <MuiThemeProvider theme={muiTheme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </AdminThemeContext.Provider>
  );
};
