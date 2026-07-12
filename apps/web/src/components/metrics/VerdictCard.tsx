import React from 'react';
import { Box, Typography } from '@mui/material';
import type { Recommendation } from '../../types/dashboard';
import { useAdminTheme } from '../admin/AdminThemeContext';

interface VerdictCardProps {
  recommendation:  string; // Supports "DESK_REJECT", "ACCEPT", or Recommendation enum
  rejectProb:      number;  // float 0.0 - 1.0
  confidence:      number | string;  // float 0.0 - 1.0 or string
  modelId:         string;
}

export default function VerdictCard({ recommendation, rejectProb, confidence, modelId }: VerdictCardProps) {
  const { isDark, colors } = useAdminTheme();

  const VERDICT_CONFIG: Record<Recommendation, {
    label: string; sublabel: string;
    color: string; bg: string; glow: string;
    emoji: string;
  }> = {
    ACCEPT:   { label: 'ACCEPT',   sublabel: 'Send to Peer Review',    color: colors.success, bg: isDark ? 'rgba(34,197,94,0.1)' : 'rgba(34,197,94,0.08)',   glow: isDark ? 'rgba(34,197,94,0.3)' : 'rgba(34,197,94,0.1)',   emoji: '✓' },
    REVIEW:   { label: 'REVIEW',   sublabel: 'Further Editor Review',  color: colors.primary, bg: isDark ? 'rgba(96,165,250,0.1)' : 'rgba(96,165,250,0.08)',  glow: isDark ? 'rgba(96,165,250,0.3)' : 'rgba(96,165,250,0.1)',  emoji: '◎' },
    ESCALATE: { label: 'ESCALATE', sublabel: 'Senior Board Required',  color: colors.warning, bg: isDark ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.08)',  glow: isDark ? 'rgba(245,158,11,0.3)' : 'rgba(245,158,11,0.1)',  emoji: '⬆' },
    REJECT:   { label: 'REJECT',   sublabel: 'Desk Reject Recommended',color: colors.danger,  bg: isDark ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.08)',   glow: isDark ? 'rgba(239,68,68,0.3)' : 'rgba(239,68,68,0.1)',   emoji: '✕' },
  };

  // Normalize DESK_REJECT from real Layer 4 payload to REJECT for UI config
  let normalizedRec: Recommendation = 'ACCEPT';
  const recUpper = (recommendation || '').toUpperCase();
  if (recUpper === 'DESK_REJECT' || recUpper === 'REJECT') {
    normalizedRec = 'REJECT';
  } else if (recUpper === 'ACCEPT' || recUpper === 'PEER_REVIEW') {
    normalizedRec = 'ACCEPT';
  } else if (recUpper === 'REVIEW' || recUpper === 'MANUAL_REVIEW') {
    normalizedRec = 'REVIEW';
  } else if (recUpper === 'ESCALATE') {
    normalizedRec = 'ESCALATE';
  }

  const cfg = VERDICT_CONFIG[normalizedRec] || VERDICT_CONFIG.ACCEPT;

  return (
    <Box>
      <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: colors.muted, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 1.2 }}>
        Final Verdict
      </Typography>

      {/* Main verdict banner */}
      <Box sx={{
        p: 2, borderRadius: 2,
        bgcolor: cfg.bg,
        border: `1px solid ${cfg.color}40`,
        boxShadow: `0 0 24px ${cfg.glow}`,
        textAlign: 'center', mb: 1.5,
        position: 'relative', overflow: 'hidden',
        '&::before': {
          content: '""', position: 'absolute',
          top: -20, right: -20, width: 80, height: 80,
          borderRadius: '50%', bgcolor: `${cfg.color}15`,
        },
      }}>
        <Typography sx={{
          fontSize: '2.4rem', lineHeight: 1, fontWeight: 900,
          color: cfg.color, letterSpacing: '-0.03em',
          textShadow: `0 0 20px ${cfg.glow}`,
          mb: 0.3,
        }}>
          {cfg.emoji}
        </Typography>
        <Typography sx={{ fontSize: '1rem', fontWeight: 800, color: cfg.color, letterSpacing: '0.1em' }}>
          {cfg.label}
        </Typography>
        <Typography sx={{ fontSize: '0.68rem', color: colors.muted, mt: 0.3 }}>
          {cfg.sublabel}
        </Typography>
      </Box>

      {/* Stats row */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.8, mb: 1 }}>
        <Box sx={{ p: 1, borderRadius: 1.5, border: `1px solid ${colors.border}`, bgcolor: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)', textAlign: 'center' }}>
          <Typography sx={{ fontSize: '1.1rem', fontWeight: 700, color: rejectProb > 0.5 ? colors.danger : colors.success }}>
            {(rejectProb * 100).toFixed(1)}%
          </Typography>
          <Typography sx={{ fontSize: '0.58rem', color: colors.muted, fontWeight: 600 }}>
            REJECT RISK
          </Typography>
        </Box>
        <Box sx={{ p: 1, borderRadius: 1.5, border: `1px solid ${colors.border}`, bgcolor: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)', textAlign: 'center' }}>
          <Typography sx={{ fontSize: '1.1rem', fontWeight: 700, color: colors.primary }}>
            {typeof confidence === 'number' ? `${(confidence * 100).toFixed(0)}%` : confidence}
          </Typography>
          <Typography sx={{ fontSize: '0.58rem', color: colors.muted, fontWeight: 600 }}>
            CONFIDENCE
          </Typography>
        </Box>
      </Box>

      {/* Model badge */}
      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <Box sx={{
          px: 1.2, py: 0.3, borderRadius: 1,
          border: `1px solid ${colors.border}`,
          bgcolor: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
        }}>
          <Typography sx={{ fontSize: '0.58rem', color: colors.muted, fontFamily: 'monospace' }}>
            Model: {modelId}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
