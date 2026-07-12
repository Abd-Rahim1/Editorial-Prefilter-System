import React from 'react';
import { Box, Typography, LinearProgress, Tooltip } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import type { SemanticScoreDict } from '../../types/dashboard';
import { useAdminTheme } from '../admin/AdminThemeContext';

interface SemanticRadarChartProps {
  scores: any;
}

const SCORE_KEYS: { key: string; label: string }[] = [
  { key: 'abstract_clarity',        label: 'Abstract Clarity'       },
  { key: 'structural_completeness', label: 'Structural Completeness' },
  { key: 'methodological_strength', label: 'Methodological Strength' },
  { key: 'experimental_strength',   label: 'Experimental Strength'   },
  { key: 'argumentative_quality',   label: 'Argumentative Quality'   },
  { key: 'scope_alignment',         label: 'Scope Alignment'         },
  { key: 'overall_quality',         label: 'Overall Quality'         },
];

export default function SemanticRadarChart({ scores = {} as SemanticScoreDict }: SemanticRadarChartProps) {
  const { isDark, colors } = useAdminTheme();

  function scoreColor(v: number): string {
    if (v >= 0.8) return colors.success;
    if (v >= 0.6) return colors.warning;
    return colors.danger;
  }

  // Extract values with strict fallback and format resolution (nested or top-level keys)
  const getScoreValue = (key: string): number => {
    if (!scores) return 0.0;
    // Resolve: check scores.scores[key] first, then scores[key] directly
    const val = (scores as any)?.scores?.[key] ?? (scores as any)?.[key];
    return typeof val === 'number' ? val : 0.0;
  };

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: colors.panel,
      borderColor: colors.border,
      borderWidth: 1,
      textStyle: { color: colors.text, fontSize: 12 },
      formatter: (params: { value: number[] }) => {
        return SCORE_KEYS
          .map((m, i) => `${m.label}: <b>${(params.value[i] * 100).toFixed(0)}%</b>`)
          .join('<br/>');
      },
    },
    radar: {
      shape:  'polygon',
      center: ['50%', '52%'],
      radius: '65%',
      startAngle: 90,
      indicator: SCORE_KEYS.map(m => ({ name: m.label, max: 1 })),
      axisName: {
        color:     colors.muted,
        fontSize:  8,
        fontWeight: 600,
        fontFamily: 'Inter, sans-serif',
      },
      splitLine:  { lineStyle: { color: colors.border, width: 1 } },
      splitArea:  { show: false },
      axisLine:   { lineStyle: { color: colors.border } },
    },
    series: [{
      type:  'radar',
      data: [{
        value: SCORE_KEYS.map(m => getScoreValue(m.key)),
        name:  'Semantic Scores',
        lineStyle: { color: colors.primary, width: 2 },
        areaStyle: {
          color: {
            type: 'radial',
            x: 0.5, y: 0.5, r: 0.8,
            colorStops: [
              { offset: 0, color: isDark ? 'rgba(37,99,235,0.5)' : 'rgba(37,99,235,0.3)' },
              { offset: 1, color: 'rgba(37,99,235,0.05)' },
            ],
          },
        },
        itemStyle: { color: colors.primary },
        symbol:    'circle',
        symbolSize: 5,
        emphasis: {
          itemStyle: { color: '#fff', borderColor: colors.primary, borderWidth: 2 },
        },
      }],
      animation:         true,
      animationDuration: 800,
      animationEasing:   'cubicOut' as const,
    }],
  };

  return (
    <Box>
      <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: colors.muted, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 1 }}>
        Layer 2 · Semantic Radar
      </Typography>

      {/* ECharts Radar */}
      <ReactECharts
        option={option}
        style={{ height: 180, width: '100%' }}
        opts={{ renderer: 'svg' }}
      />

      {/* Score progress bars */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.7, mt: 1 }}>
        {SCORE_KEYS.map(({ key, label }) => {
          const v = getScoreValue(key);
          return (
            <Box key={key}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.3 }}>
                <Typography sx={{ fontSize: '0.6rem', color: colors.muted }}>{label}</Typography>
                <Typography sx={{ fontSize: '0.6rem', fontWeight: 700, color: scoreColor(v) }}>
                  {(v * 100).toFixed(0)}%
                </Typography>
              </Box>
              <Tooltip title={`${label}: ${(v * 100).toFixed(1)}%`} arrow placement="left">
                <LinearProgress
                  variant="determinate"
                  value={v * 100}
                  sx={{
                    height: 3, borderRadius: 2,
                    bgcolor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
                    '& .MuiLinearProgress-bar': { bgcolor: scoreColor(v) },
                  }}
                />
              </Tooltip>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
