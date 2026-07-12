import React from 'react';
import { Box, Typography } from '@mui/material';
import { COLORS } from '../../styles/theme';

interface Stat { label: string; value: number; color: string; }

interface QueueStatsProps {
  pending:   number;
  accepted:  number;
  escalated: number;
  rejected:  number;
}

export default function QueueStats({ pending, accepted, escalated, rejected }: QueueStatsProps) {
  const stats: Stat[] = [
    { label: 'Pending',   value: pending,   color: COLORS.muted   },
    { label: 'Accepted',  value: accepted,  color: COLORS.success  },
    { label: 'Escalated', value: escalated, color: COLORS.warning  },
    { label: 'Rejected',  value: rejected,  color: COLORS.danger   },
  ];

  return (
    <Box>
      <Typography variant="overline" sx={{ display: 'block', mb: 1, px: 0.5 }}>
        Queue Stats
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.8 }}>
        {stats.map(s => (
          <Box
            key={s.label}
            sx={{
              p: 1, borderRadius: 1.5,
              border: `1px solid ${COLORS.border}`,
              bgcolor: 'rgba(255,255,255,0.02)',
              textAlign: 'center',
            }}
          >
            <Typography sx={{ fontSize: '1.1rem', fontWeight: 700, color: s.color, lineHeight: 1.2 }}>
              {s.value}
            </Typography>
            <Typography sx={{ fontSize: '0.58rem', color: COLORS.muted, fontWeight: 600 }}>
              {s.label.toUpperCase()}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
