import { createTheme, alpha } from '@mui/material/styles';

// ── Brand tokens ─────────────────────────────────────────────
export const COLORS = {
  bg:        '#0f172a',
  panel:     '#1e293b',
  border:    '#334155',
  primary:   '#2563eb',
  success:   '#22c55e',
  warning:   '#f59e0b',
  danger:    '#ef4444',
  text:      '#f8fafc',
  muted:     '#94a3b8',
  highlight: '#1d4ed8',
} as const;

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: COLORS.bg,
      paper:   COLORS.panel,
    },
    primary:   { main: COLORS.primary,  light: '#3b82f6', dark: '#1d4ed8'  },
    secondary: { main: '#6366f1',        light: '#818cf8', dark: '#4f46e5'  },
    success:   { main: COLORS.success,  light: '#4ade80', dark: '#16a34a'  },
    warning:   { main: COLORS.warning,  light: '#fbbf24', dark: '#d97706'  },
    error:     { main: COLORS.danger,   light: '#f87171', dark: '#dc2626'  },
    text: {
      primary:   COLORS.text,
      secondary: COLORS.muted,
      disabled:  '#475569',
    },
    divider: COLORS.border,
  },
  typography: {
    fontFamily: '"Inter", "Roboto", -apple-system, BlinkMacSystemFont, sans-serif',
    h1: { fontSize: '2rem',   fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.01em' },
    h3: { fontSize: '1.25rem',fontWeight: 600 },
    h4: { fontSize: '1.1rem', fontWeight: 600 },
    h5: { fontSize: '0.95rem',fontWeight: 600 },
    h6: { fontSize: '0.875rem',fontWeight: 600 },
    subtitle1: { fontSize: '0.875rem', fontWeight: 500, color: COLORS.muted },
    subtitle2: { fontSize: '0.75rem',  fontWeight: 500, color: COLORS.muted },
    body1: { fontSize: '0.875rem', lineHeight: 1.6 },
    body2: { fontSize: '0.8rem',   lineHeight: 1.5 },
    caption: { fontSize: '0.7rem', lineHeight: 1.4, color: COLORS.muted },
    button: { textTransform: 'none', fontWeight: 600, letterSpacing: '0.01em' },
    overline: { fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.1em', color: COLORS.muted },
  },
  shape: { borderRadius: 8 },
  shadows: [
    'none',
    `0 1px 3px ${alpha('#000', 0.3)}, 0 1px 2px ${alpha('#000', 0.4)}`,
    `0 2px 6px ${alpha('#000', 0.35)}`,
    `0 4px 12px ${alpha('#000', 0.4)}`,
    `0 6px 20px ${alpha('#000', 0.45)}`,
    `0 8px 28px ${alpha('#000', 0.5)}`,
    ...Array(19).fill('none'),
  ] as any,
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: ${COLORS.bg}; }
        ::-webkit-scrollbar-thumb { background: ${COLORS.border}; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
      `,
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: COLORS.panel,
          border: `1px solid ${COLORS.border}`,
        },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: COLORS.panel,
          border: `1px solid ${COLORS.border}`,
          transition: 'border-color 0.2s ease',
          '&:hover': { borderColor: '#475569' },
        },
      },
    },
    MuiDivider: {
      styleOverrides: { root: { borderColor: COLORS.border } },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 6, fontWeight: 600 },
        contained: {
          boxShadow: 'none',
          '&:hover': { boxShadow: `0 0 12px ${alpha(COLORS.primary, 0.4)}` },
        },
        outlined: { borderColor: COLORS.border },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, fontSize: '0.65rem', letterSpacing: '0.03em' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: COLORS.border, fontSize: '0.78rem' },
        head: { fontWeight: 700, color: COLORS.muted, fontSize: '0.65rem', letterSpacing: '0.08em', textTransform: 'uppercase' },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { backgroundColor: alpha(COLORS.primary, 0.15), borderRadius: 4 },
        bar:  { borderRadius: 4 },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: { backgroundColor: '#0f172a', border: `1px solid ${COLORS.border}`, fontSize: '0.72rem' },
        arrow:   { color: '#0f172a' },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontSize: '0.75rem',
          fontWeight: 600,
          minHeight: 44,
          color: COLORS.muted,
          '&.Mui-selected': { color: COLORS.text },
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: { height: 2, backgroundColor: COLORS.primary },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 8, border: `1px solid` },
      },
    },
  },
});

export default theme;
