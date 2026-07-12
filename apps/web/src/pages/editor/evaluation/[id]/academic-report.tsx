import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { Box, Typography, CircularProgress, Alert, Button, Divider, Grid } from '@mui/material';
import PrintIcon from '@mui/icons-material/Print';
import KeyboardBackspaceIcon from '@mui/icons-material/KeyboardBackspace';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { authAxiosGet, getAuthToken, handleUnauthorized } from '../../../../utils/auth';

// Import Types
import type { ReportData } from '../../../../types/dashboard';

// Clean, formal SVG Radar Chart to replace ECharts and guarantee instant vector printing in black/white/navy
function SVGAcademicRadarChart({ scores = {} }: { scores: Record<string, number> }) {
  const keys = [
    { key: 'abstract_clarity',        label: 'Clarity' },
    { key: 'structural_completeness', label: 'Structure' },
    { key: 'methodological_strength', label: 'Methodology' },
    { key: 'experimental_strength',   label: 'Experiments' },
    { key: 'argumentative_quality',   label: 'Arguments' },
    { key: 'scope_alignment',         label: 'Scope' },
    { key: 'overall_quality',         label: 'Quality' }
  ];

  const size = 260;
  const center = size / 2;
  const radius = 80;
  const totalSides = keys.length;

  // Generate radar guidelines
  const levels = [0.25, 0.5, 0.75, 1.0];
  const webPaths = levels.map((lvl) => {
    const points = [];
    for (let i = 0; i < totalSides; i++) {
      const angle = (i * 2 * Math.PI) / totalSides - Math.PI / 2;
      const x = center + radius * lvl * Math.cos(angle);
      const y = center + radius * lvl * Math.sin(angle);
      points.push(`${x},${y}`);
    }
    return points.join(' ');
  });

  // Generate axis rays
  const axisRays = [];
  for (let i = 0; i < totalSides; i++) {
    const angle = (i * 2 * Math.PI) / totalSides - Math.PI / 2;
    const x = center + radius * Math.cos(angle);
    const y = center + radius * Math.sin(angle);
    axisRays.push({ x, y });
  }

  // Generate data polygon path
  const scorePoints = [];
  for (let i = 0; i < totalSides; i++) {
    const key = keys[i].key;
    const val = scores[key] || 0.0;
    const angle = (i * 2 * Math.PI) / totalSides - Math.PI / 2;
    const x = center + radius * val * Math.cos(angle);
    const y = center + radius * val * Math.sin(angle);
    scorePoints.push(`${x},${y}`);
  }
  const dataPath = scorePoints.join(' ');

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="font-sans text-[8px] font-bold text-slate-800">
        {/* Guidelines */}
        {webPaths.map((path, idx) => (
          <polygon key={idx} points={path} fill="none" stroke="#cbd5e1" strokeWidth="0.5" strokeDasharray="2,2" />
        ))}
        {/* Rays */}
        {axisRays.map((r, idx) => (
          <line key={idx} x1={center} y1={center} x2={r.x} y2={r.y} stroke="#e2e8f0" strokeWidth="0.75" />
        ))}
        {/* Radar Value Shape */}
        <polygon points={dataPath} fill="rgba(15, 23, 42, 0.15)" stroke="#0f172a" strokeWidth="1.5" />
        {/* Value Vertices */}
        {scorePoints.map((pt, idx) => {
          const [x, y] = pt.split(',');
          return <circle key={idx} cx={x} cy={y} r="3" fill="#0f172a" stroke="#fff" strokeWidth="1" />;
        })}
        {/* Axis Labels */}
        {keys.map((k, i) => {
          const angle = (i * 2 * Math.PI) / totalSides - Math.PI / 2;
          const x = center + (radius + 20) * Math.cos(angle);
          const y = center + (radius + 12) * Math.sin(angle);
          const anchor = Math.cos(angle) > 0.1 ? 'start' : Math.cos(angle) < -0.1 ? 'end' : 'middle';
          return (
            <text key={i} x={x} y={y} textAnchor={anchor} alignmentBaseline="middle" fill="#475569">
              {k.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

export default function AcademicReportPage() {
  const router = useRouter();
  const { id } = router.query;
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthed, setIsAuthed] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = getAuthToken();
      if (!token) {
        handleUnauthorized(router);
      } else {
        setIsAuthed(true);
        setAuthChecked(true);
      }
    }
  }, [router]);

  // Direct DB JSON report fetch
  const { data: reportData, isLoading, isError } = useQuery({
    queryKey: ['academic-report', id],
    queryFn: async () => {
      if (!id || !getAuthToken()) return null;
      return await authAxiosGet<ReportData>(`/api/manuscripts/${id}/report`);
    },
    enabled: !!id && isAuthed,
  });

  if (!authChecked || !isAuthed || isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', bgcolor: '#fff' }}>
        <CircularProgress size={40} sx={{ color: '#0f172a' }} />
      </Box>
    );
  }

  if (isError || !reportData) {
    return (
      <Box sx={{ p: 4, bgcolor: '#fff' }}>
        <Alert severity="error">
          Error retrieving formal academic report. Verify FastAPI is online.
        </Alert>
      </Box>
    );
  }

  // Extract variables
  const predictions = reportData.prediction || {};
  const explanation = reportData.natural_language_explanation || {};
  const explanationText = typeof explanation === 'string' ? explanation : explanation.text || explanation.layer4_explanation || "";
  const paragraphs = explanationText.split(/\n+/).filter(p => p.trim() !== '');
  const rankedFeatures = reportData.feature_importance?.ranked_features || [];
  const violations = reportData.editorial_rules?.violations || [];
  const scores = reportData.semantic_scores?.scores || {};
  const isRejected = predictions.verdict === 'DESK_REJECT';

  // Compute maximum absolute impact for relative scaling of the SHAP bars
  const maxSHAPImpact = Math.max(...rankedFeatures.map(f => f.absolute_impact || 0.001), 0.001);

  return (
    <div className="min-h-screen bg-slate-100 py-12 px-4 print:bg-white print:p-0 print:py-0">
      <Head>
        <title>Academic Annex Report - Manuscript #{id}</title>
        <style type="text/css">{`
          @media print {
            body {
              background-color: #ffffff;
              color: #000000;
            }
            .no-print {
              display: none !important;
            }
            @page {
              size: A4 portrait;
              margin: 2cm;
            }
          }
        `}</style>
      </Head>

      {/* ── FLOAT CONTROL HEADERBAR (Screen only) ────────────────────────── */}
      <div className="no-print max-w-[210mm] mx-auto mb-6 flex justify-between items-center bg-slate-900 text-white px-6 py-3 rounded-lg shadow-md">
        <Button 
          startIcon={<KeyboardBackspaceIcon />} 
          onClick={() => router.back()}
          sx={{ color: '#94a3b8', textTransform: 'none', fontWeight: 600 }}
        >
          Back to Cockpit
        </Button>
        <Button
          variant="contained"
          startIcon={<PrintIcon />}
          onClick={() => window.print()}
          sx={{ bgcolor: '#3b82f6', '&:hover': { bgcolor: '#2563eb' }, textTransform: 'none', fontWeight: 700 }}
        >
          Print Formal Report
        </Button>
      </div>

      {/* ── SCIENTIFIC PAPER PAGE CONTAINER (A4 Layout) ─────────────────── */}
      <div className="max-w-[210mm] mx-auto bg-white p-16 text-slate-900 font-serif shadow-xl border border-slate-200 min-h-[297mm] print:shadow-none print:border-none print:p-0">
        
        {/* Annex Header */}
        <div className="text-center mb-8">
          <Typography variant="overline" className="text-[10px] tracking-widest font-sans font-bold text-slate-500">
            TECHNICAL ANNEX REPORT &nbsp;·&nbsp; AUTOMATED EDITORIAL PRE-SCREENER
          </Typography>
          <h1 className="text-2xl font-bold text-slate-900 mt-2 mb-1 uppercase tracking-tight">
            Automated Editorial Decision Support Report
          </h1>
          <div className="w-16 h-0.5 bg-slate-800 mx-auto my-3"></div>
          <Typography variant="body2" className="text-xs font-sans text-slate-600">
            Manuscript Identifier: <span className="font-bold font-mono">{id}</span> &nbsp;|&nbsp; 
            Generated: {new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
          </Typography>
        </div>

        {/* Verdict Callout Banner */}
        <div className={`border p-5 rounded-lg mb-8 font-sans ${
          isRejected 
            ? 'bg-rose-50/50 border-rose-200 text-rose-900' 
            : 'bg-emerald-50/50 border-emerald-200 text-emerald-900'
        }`}>
          <div className="flex justify-between items-center">
            <div>
              <div className="text-xs uppercase tracking-wider font-bold opacity-75">Automated Recommendation</div>
              <div className="text-xl font-extrabold uppercase mt-0.5 tracking-tight">
                {isRejected ? 'DESK REJECTION RECOMMENDATION' : 'ACCEPT FOR PEER REVIEW'}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs uppercase tracking-wider font-bold opacity-75">Reject Probability</div>
              <div className="text-2xl font-mono font-extrabold">
                {(predictions.desk_reject_probability * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

        {/* Executive Summary Narrative */}
        <div className="mb-10">
          <h2 className="text-xs font-bold font-sans uppercase tracking-wider text-slate-800 mb-3 border-b pb-1">
            I. Executive Summary & Justification
          </h2>
          <div className="space-y-4 text-sm leading-relaxed text-slate-800 text-justify">
            {paragraphs.map((p, idx) => {
              const isConclusion = p.trim().toLowerCase().startsWith("conclusion:");
              return (
                <p key={idx} className={isConclusion ? "italic font-semibold bg-slate-50 p-4 border-l-4 border-slate-800 text-slate-900 my-4" : ""}>
                  {p}
                </p>
              );
            })}
          </div>
        </div>

        {/* Visual Analytics */}
        <div className="mb-10">
          <h2 className="text-xs font-bold font-sans uppercase tracking-wider text-slate-800 mb-4 border-b pb-1">
            II. Layer 2 & 4 Visual Analytics Suite
          </h2>
          
          <div className="grid grid-cols-2 gap-8 items-start">
            {/* Left Column: Semantic Radar */}
            <div className="border border-slate-200 p-4 rounded-lg bg-slate-50/50">
              <h3 className="text-[10px] font-sans font-bold uppercase tracking-wider text-slate-700 text-center mb-4">
                A. Qwen-2.5 Semantic Dimension Radar
              </h3>
              <SVGAcademicRadarChart scores={scores} />
              <div className="text-[9px] text-slate-500 font-sans text-justify mt-2 leading-snug">
                Indicator mapping evaluates the abstract, methodology, experiments, structure, and coherence metrics on a scaled range [0.0 - 1.0].
              </div>
            </div>

            {/* Right Column: SHAP Bar Chart */}
            <div className="border border-slate-200 p-4 rounded-lg bg-slate-50/50">
              <h3 className="text-[10px] font-sans font-bold uppercase tracking-wider text-slate-700 text-center mb-4">
                B. SHAP Feature Attribution Weight
              </h3>
              <div className="space-y-3 mt-4">
                {rankedFeatures.length > 0 ? (
                  rankedFeatures.map((feat, idx) => {
                    const isRejectRisk = feat.direction === 'INCREASED_REJECT_RISK';
                    const barColor = isRejectRisk ? 'bg-rose-600' : 'bg-emerald-600';
                    const percentWidth = Math.max((feat.absolute_impact / maxSHAPImpact) * 100, 3);
                    return (
                      <div key={idx} className="space-y-1 font-sans">
                        <div className="flex justify-between text-[9px] font-semibold text-slate-700">
                          <span className="capitalize">{feat.name.replace(/_/g, ' ')}</span>
                          <span className={isRejectRisk ? 'text-rose-700' : 'text-emerald-700'}>
                            {isRejectRisk ? '+' : ''}{feat.shap_value.toFixed(4)}
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${barColor} rounded-full`} 
                            style={{ width: `${percentWidth}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-xs text-slate-500 text-center py-6 font-sans">
                    No attributions calculated.
                  </div>
                )}
              </div>
              <div className="text-[9px] text-slate-500 font-sans text-justify mt-5 leading-snug">
                Positive values (+) denote increased reject risk contribution; negative values (-) indicate risk mitigation characteristics.
              </div>
            </div>
          </div>
        </div>

        {/* Structural Integrity Violations */}
        <div>
          <h2 className="text-xs font-bold font-sans uppercase tracking-wider text-slate-800 mb-3 border-b pb-1">
            III. Layer 1 Deterministic Structural Integrity Checklist
          </h2>
          {violations.length > 0 ? (
            <ul className="list-disc pl-5 space-y-2 text-sm text-slate-800">
              {violations.map((violation, idx) => (
                <li key={idx} className="leading-relaxed">
                  {violation}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm italic text-slate-600 bg-emerald-50 p-4 border-l-4 border-emerald-500 rounded-r-md">
              Checklist passed. Zero deterministic formatting or boundary rule violations detected.
            </div>
          )}
        </div>

        {/* Annex Footer */}
        <div className="mt-16 border-t pt-4 text-center text-[9px] font-sans text-slate-400">
          PeerRead / tuned_idx_0/exp_C Model Run Annex Report. Antigravity AI Engine. All rights reserved.
        </div>

      </div>
    </div>
  );
}
