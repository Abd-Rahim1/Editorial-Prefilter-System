import React from 'react';
import { Box } from '@mui/material';
import type { RadarChartProps } from '../../types/dashboard';

// ── Axis definitions ─────────────────────────────────────────
const METRICS: ReadonlyArray<{ key: string; label: string }> = [
  { key: 'abstract_clarity',        label: 'Clarity'     },
  { key: 'structural_completeness', label: 'Structure'   },
  { key: 'methodological_strength', label: 'Methodology' },
  { key: 'experimental_strength',   label: 'Experiments' },
  { key: 'argumentative_quality',   label: 'Argument'    },
  { key: 'scope_alignment',         label: 'Scope'       },
];

// ── SVG canvas constants ─────────────────────────────────────
const WIDTH  = 280;
const HEIGHT = 240;
const CX     = WIDTH  / 2;  // centre x
const CY     = HEIGHT / 2;  // centre y
const R      = 75;           // outer radius
const N      = METRICS.length;

// ── Coordinate helpers ───────────────────────────────────────
/** Returns the radian angle for axis i, starting from the top (−π/2). */
function toAngle(i: number): number {
  return (i * 2 * Math.PI) / N - Math.PI / 2;
}

/** Returns an SVG "x,y" point string for a grid ring at a given percentage. */
function gridPoint(i: number, pct: number): string {
  const a = toAngle(i);
  return `${CX + R * pct * Math.cos(a)},${CY + R * pct * Math.sin(a)}`;
}

// ── Component ────────────────────────────────────────────────
const NativeRadarChart: React.FC<RadarChartProps> = ({ scores }) => {
  const points = METRICS.map((m, i) => {
    const angle = toAngle(i);
    const value = scores[m.key] ?? 0.5;
    return {
      x:      CX +  R         * value * Math.cos(angle),
      y:      CY +  R         * value * Math.sin(angle),
      labelX: CX + (R + 20)           * Math.cos(angle),
      labelY: CY + (R + 10)           * Math.sin(angle),
      label:  m.label,
    };
  });

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
      <svg width={WIDTH} height={HEIGHT}>

        {/* Concentric grid rings */}
        {([0.25, 0.5, 0.75, 1.0] as const).map((pct, idx) => (
          <polygon
            key={idx}
            points={METRICS.map((_, i) => gridPoint(i, pct)).join(' ')}
            fill="none"
            stroke="#cbd5e1"
            strokeDasharray={pct === 1.0 ? '0' : '4,4'}
          />
        ))}

        {/* Axis spokes from centre */}
        {METRICS.map((_, i) => (
          <line
            key={i}
            x1={CX} y1={CY}
            x2={CX + R * Math.cos(toAngle(i))}
            y2={CY + R * Math.sin(toAngle(i))}
            stroke="#e2e8f0"
          />
        ))}

        {/* Filled data polygon */}
        <polygon
          points={points.map(p => `${p.x},${p.y}`).join(' ')}
          fill="rgba(30, 58, 138, 0.15)"
          stroke="#1e3a8a"
          strokeWidth="2"
        />

        {/* Data point markers */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3" fill="#3b82f6" />
        ))}

        {/* Axis labels */}
        {points.map((p, i) => (
          <text
            key={i}
            x={p.labelX}
            y={p.labelY}
            textAnchor="middle"
            fontSize="10px"
            fontWeight="bold"
            fill="#475569"
          >
            {p.label}
          </text>
        ))}

      </svg>
    </Box>
  );
};

export default NativeRadarChart;
