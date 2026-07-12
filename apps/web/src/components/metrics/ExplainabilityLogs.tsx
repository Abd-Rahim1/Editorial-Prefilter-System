import React from 'react';
import { Box, Typography, LinearProgress, Tooltip, Paper, Chip } from '@mui/material';
import ArrowTrendingUpIcon from '@mui/icons-material/TrendingUp';
import ArrowTrendingDownIcon from '@mui/icons-material/TrendingDown';
import type { RankedFeature } from '../../types/dashboard';
import { useAdminTheme } from '../admin/AdminThemeContext';

interface ExplainabilityLogsProps {
  entries?:          unknown[]; // For backward compatibility
  narrative?:        any;
  rankedFeatures?:   RankedFeature[];
}

function getActivityStyles(type: string, isDark: boolean) {
  if (isDark) {
    switch (type) {
      case 'success': return { bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.3)', text: '#34d399' };
      case 'warning': return { bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.3)', text: '#fbbf24' };
      case 'error': return { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.3)', text: '#f87171' };
      default: return { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.3)', text: '#60a5fa' };
    }
  } else {
    switch (type) {
      case 'success': return { bg: 'rgba(22, 163, 74, 0.1)', border: 'rgba(22, 163, 74, 0.2)', text: '#16a34a' };
      case 'warning': return { bg: 'rgba(217, 119, 6, 0.1)', border: 'rgba(217, 119, 6, 0.2)', text: '#d97706' };
      case 'error': return { bg: 'rgba(220, 38, 38, 0.1)', border: 'rgba(220, 38, 38, 0.2)', text: '#dc2626' };
      default: return { bg: 'rgba(37, 99, 235, 0.1)', border: 'rgba(37, 99, 235, 0.2)', text: '#2563eb' };
    }
  }
}

export default function ExplainabilityLogs({ entries, narrative = "", rankedFeatures = [] }: ExplainabilityLogsProps) {
  const { isDark, colors } = useAdminTheme();

  // 1. Sort ranked features by absolute impact descending
  const sortedFeatures = [...(rankedFeatures || [])].sort((a, b) => b.absolute_impact - a.absolute_impact);

  // 2. Safe JSON string extraction
  const narrativeText = typeof narrative === 'string'
    ? narrative
    : narrative?.text || narrative?.layer4_explanation || "";

  // 3. Parse paragraphs handling newlines
  const paragraphs: string[] = narrativeText
    ? String(narrativeText).split(/\n+/).filter((p: string) => p.trim() !== '')
    : [];

  // Calculate maximum absolute impact for relative scaling
  const maxImpact = Math.max(...sortedFeatures.map(f => f.absolute_impact || 0.001), 0.001);

  const hasRealData = sortedFeatures.length > 0 || paragraphs.length > 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

      {/* ── CARD 1: SHAP FEATURE ATTRIBUTION ─────────────────────────────── */}
      {hasRealData && (
        <Paper 
          sx={{ 
            p: 3, 
            borderRadius: 3, 
            bgcolor: colors.panel, 
            border: `1px solid ${colors.border}`,
            boxShadow: isDark ? '0 4px 12px rgba(0, 0, 0, 0.25)' : 'none',
            transition: 'all 0.25s ease'
          }}
        >
          <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: colors.muted, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 2 }}>
            Layer 3 · SHAP Feature Attribution (Quantified Weighting)
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {sortedFeatures.length > 0 ? (
              sortedFeatures.map((feat, index) => {
                const isRejectRisk = feat.direction === 'INCREASED_REJECT_RISK';
                const impactColor = isRejectRisk ? colors.danger : colors.success;
                const rank = feat.rank || (index + 1);
                
                // Scale visual width relative to max impact to ensure proper contrast
                const scaledPercentage = Math.min(((feat.absolute_impact) / maxImpact) * 100, 100);

                return (
                  <Box key={index} sx={{ p: 1.5, borderRadius: 1.5, border: `1px solid ${colors.border}`, bgcolor: isDark ? 'rgba(255,255,255,0.01)' : 'rgba(0,0,0,0.01)' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.8 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box sx={{ bgcolor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)', px: 0.8, py: 0.2, borderRadius: 1 }}>
                          <Typography sx={{ fontSize: '0.58rem', fontWeight: 800, color: colors.muted }}>
                            #{rank}
                          </Typography>
                        </Box>
                        <Typography sx={{ fontSize: '0.68rem', fontWeight: 700, color: colors.text, textTransform: 'capitalize' }}>
                          {feat.name ? feat.name.replace(/_/g, ' ') : 'Unknown Feature'}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {isRejectRisk ? (
                          <ArrowTrendingUpIcon sx={{ fontSize: 14, color: impactColor }} />
                        ) : (
                          <ArrowTrendingDownIcon sx={{ fontSize: 14, color: impactColor }} />
                        )}
                        <Typography sx={{ fontSize: '0.7rem', fontWeight: 800, color: impactColor }}>
                          {isRejectRisk ? '+' : ''}{feat.shap_value.toFixed(4)}
                        </Typography>
                      </Box>
                    </Box>

                    <Tooltip title={`SHAP Shift: ${feat.shap_value.toFixed(6)}`} arrow placement="top">
                      <LinearProgress
                        variant="determinate"
                        value={Math.max(scaledPercentage, 3)}
                        sx={{
                          height: 4, 
                          borderRadius: 1,
                          bgcolor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
                          '& .MuiLinearProgress-bar': { bgcolor: impactColor },
                        }}
                      />
                    </Tooltip>
                  </Box>
                );
              })
            ) : (
              <Typography sx={{ fontSize: '0.65rem', color: colors.muted, textAlign: 'center', py: 2 }}>
                No SHAP feature attributions generated for this model run.
              </Typography>
            )}
          </Box>
        </Paper>
      )}

      {/* ── CARD 2: NARRATIVE PROSE ──────────────────────────────────────── */}
      {hasRealData && (
        <Paper 
          sx={{ 
            p: 3, 
            borderRadius: 3, 
            bgcolor: colors.panel, 
            border: `1px solid ${colors.border}`,
            boxShadow: isDark ? '0 4px 12px rgba(0, 0, 0, 0.25)' : 'none',
            transition: 'all 0.25s ease'
          }}
        >
          <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: colors.muted, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 2 }}>
            Layer 4 · Explainable AI Narrative (Natural Language)
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {paragraphs.length > 0 ? (
              paragraphs.map((p: string, idx: number) => {
                const isConclusion = p.trim().toLowerCase().startsWith("conclusion:");
                if (isConclusion) {
                  return (
                    <Box 
                      key={idx} 
                      sx={{ 
                        p: 2, 
                        borderRadius: 2, 
                        bgcolor: isDark ? 'rgba(37,99,235,0.1)' : 'rgba(37,99,235,0.05)', 
                        border: `1px solid ${colors.border}`,
                        mt: 1
                      }}
                    >
                      <Typography sx={{ fontSize: '0.72rem', fontWeight: 700, color: colors.text, lineHeight: 1.6 }}>
                        {p}
                      </Typography>
                    </Box>
                  );
                }
                return (
                  <Typography key={idx} sx={{ fontSize: '0.72rem', color: colors.text, lineHeight: 1.6, fontWeight: 500 }}>
                    {p}
                  </Typography>
                );
              })
            ) : (
              <Typography sx={{ fontSize: '0.65rem', color: colors.muted, textAlign: 'center', py: 2 }}>
                No qualitative decision narrative available for this manuscript.
              </Typography>
            )}
          </Box>
        </Paper>
      )}

      {/* ── CARD 3: GENERAL EXPLAINABILITY ENTRIES (Fallback or Local Ingest) ── */}
      {!hasRealData && entries && (entries as any[]).length > 0 && (
        <Paper sx={{ p: 3, borderRadius: 3, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
          <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: colors.muted, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 2 }}>
            Evaluation Explainability Details
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {(entries as any[]).map((entry) => {
              const bgStyles = getActivityStyles(entry.type, isDark);
              return (
                <Box key={entry.id} sx={{ p: 2, borderRadius: 2, border: `1px solid ${colors.border}`, bgcolor: isDark ? 'rgba(255,255,255,0.01)' : 'rgba(0,0,0,0.01)' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography sx={{ fontSize: '0.75rem', fontWeight: 700, color: colors.text }}>
                      {entry.section}
                    </Typography>
                    <Chip 
                      label={String(entry.type).toUpperCase()} 
                      size="small" 
                      sx={{ 
                        fontSize: '0.6rem', 
                        fontWeight: 800, 
                        bgcolor: bgStyles.bg, 
                        color: bgStyles.text, 
                        border: `1px solid ${bgStyles.border}` 
                      }} 
                    />
                  </Box>
                  <Typography sx={{ fontSize: '0.72rem', fontWeight: 600, color: colors.text, mb: 0.5 }}>
                    {entry.issue}
                  </Typography>
                  <Typography sx={{ fontSize: '0.7rem', color: colors.muted, mb: 1, lineHeight: 1.5 }}>
                    {entry.reasoning}
                  </Typography>
                  <Typography sx={{ fontSize: '0.65rem', color: colors.muted, fontFamily: 'monospace' }}>
                    Evidence: {entry.evidence}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Paper>
      )}

    </Box>
  );
}
