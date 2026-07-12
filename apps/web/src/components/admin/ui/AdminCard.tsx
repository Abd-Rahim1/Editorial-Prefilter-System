import React from 'react';
import { Card, CardContent, CardHeader, Box, Typography, Divider } from '@mui/material';
import { useAdminTheme } from '../AdminThemeContext';

interface AdminCardProps {
  title?: React.ReactNode;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  noPadding?: boolean;
  sx?: any;
}

export const AdminCard: React.FC<AdminCardProps> = ({
  title, subtitle, action, children, noPadding = false, sx = {}
}) => {
  const { colors } = useAdminTheme();

  return (
    <Card
      sx={{
        bgcolor: colors.panel,
        border: `1px solid ${colors.border}`,
        borderRadius: 2, // 8px identical card radius
        boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
        transition: 'all 0.25s ease',
        ...sx,
      }}
    >
      {(title || action) && (
        <>
          <CardHeader
            title={
              typeof title === 'string' ? (
                <Typography variant="h6" sx={{ fontSize: '0.95rem', fontWeight: 700, color: colors.text }}>
                  {title}
                </Typography>
              ) : (
                title
              )
            }
            subheader={
              subtitle ? (
                <Typography variant="caption" sx={{ fontSize: '0.75rem', color: colors.muted }}>
                  {subtitle}
                </Typography>
              ) : undefined
            }
            action={action}
            sx={{ px: 2.5, py: 2, '& .MuiCardHeader-action': { m: 0, alignSelf: 'center' } }}
          />
          <Divider sx={{ borderColor: colors.border }} />
        </>
      )}
      <CardContent sx={{ p: noPadding ? 0 : 2.5, '&:last-child': { pb: noPadding ? 0 : 2.5 } }}>
        {children}
      </CardContent>
    </Card>
  );
};
