import React from 'react';
import { Box, Typography, LinearProgress, Tooltip } from '@mui/material';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined';
import CancelOutlinedIcon       from '@mui/icons-material/CancelOutlined';
import { COLORS } from '../../styles/theme';
import type { StructuralRule, RuleStatus } from '../../types/dashboard';

interface StructuralRulesCardProps {
  rules: StructuralRule[];
}

const RULE_CONFIG: Record<RuleStatus, { icon: React.ReactElement; color: string; label: string }> = {
  pass:    { icon: <CheckCircleOutlinedIcon   sx={{ fontSize: 14 }} />, color: COLORS.success, label: 'PASS'    },
  warning: { icon: <WarningAmberOutlinedIcon  sx={{ fontSize: 14 }} />, color: COLORS.warning, label: 'WARN'    },
  fail:    { icon: <CancelOutlinedIcon        sx={{ fontSize: 14 }} />, color: COLORS.danger,  label: 'FAIL'    },
};

export default function StructuralRulesCard({ rules }: StructuralRulesCardProps) {
  const passed   = rules.filter(r => r.status === 'pass').length;
  const total    = rules.length;
  const pct      = total > 0 ? (passed / total) * 100 : 0;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.2 }}>
        <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: COLORS.muted, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Layer 1 · Structural Rules
        </Typography>
        <Typography sx={{ fontSize: '0.68rem', fontWeight: 700, color: passed === total ? COLORS.success : COLORS.warning }}>
          {passed}/{total}
        </Typography>
      </Box>

      {/* Progress bar */}
      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{
          mb: 1.5, height: 3, borderRadius: 2,
          '& .MuiLinearProgress-bar': {
            bgcolor: pct === 100 ? COLORS.success : pct >= 70 ? COLORS.warning : COLORS.danger,
          },
        }}
      />

      {/* Rule rows */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.6 }}>
        {rules.map(rule => {
          const cfg = RULE_CONFIG[rule.status];
          return (
            <Tooltip key={rule.id} title={rule.detail} arrow placement="left">
              <Box sx={{
                display: 'flex', alignItems: 'center', gap: 1,
                p: 0.8, borderRadius: 1,
                bgcolor: `${cfg.color}0d`,
                border: `1px solid ${cfg.color}20`,
                cursor: 'default',
              }}>
                <Box sx={{ color: cfg.color, display: 'flex', alignItems: 'center', flexShrink: 0 }}>
                  {cfg.icon}
                </Box>
                <Typography sx={{ fontSize: '0.68rem', color: COLORS.text, flex: 1, fontWeight: 500 }}>
                  {rule.label}
                </Typography>
                <Typography sx={{
                  fontSize: '0.55rem', fontWeight: 800, color: cfg.color,
                  letterSpacing: '0.06em',
                }}>
                  {cfg.label}
                </Typography>
              </Box>
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
}
