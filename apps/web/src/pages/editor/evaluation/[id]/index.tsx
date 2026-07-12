import React, { useRef, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import DashboardLayout from '../../../../components/layout/DashboardLayout';
import { Typography, Paper, Box, CircularProgress, Alert, Button } from '@mui/material';
import { Grid } from '@mui/material';
import PrintIcon from '@mui/icons-material/Print';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import CodeIcon from '@mui/icons-material/Code';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import Chip from '@mui/material/Chip';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useAdminTheme } from '../../../../components/admin/AdminThemeContext';
import { authAxiosGet, getAuthToken, handleUnauthorized } from '../../../../utils/auth';

// Import Types
import type { ReportData } from '../../../../types/dashboard';

// Import Modular Components
import VerdictCard from '../../../../components/metrics/VerdictCard';
import SemanticRadarChart from '../../../../components/charts/SemanticRadarChart';
import ExplainabilityLogs from '../../../../components/metrics/ExplainabilityLogs';

export default function EvaluationDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const printRef = useRef<HTMLDivElement>(null);
  const { isDark, colors } = useAdminTheme();

  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthed, setIsAuthed] = useState(false);

  React.useEffect(() => {
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

  // Fetch the real Layer 4 JSON report from our FastAPI backend
  const { data: reportData, isLoading, isError } = useQuery({
    queryKey: ['manuscript-report', id],
    queryFn: async () => {
      if (!id || !getAuthToken()) return null;
      return await authAxiosGet<ReportData>(`/api/manuscripts/${id}/report`);
    },
    enabled: !!id && isAuthed,
  });

  const handleDownloadJSON = () => {
    if (!reportData) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(reportData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `editorial_artifact_${id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  if (!authChecked || !isAuthed || isLoading) {
    return (
      <DashboardLayout role="editor">
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 12 }}>
          <CircularProgress size={48} sx={{ color: colors.primary }} />
        </Box>
      </DashboardLayout>
    );
  }

  if (isError || !reportData) {
    return (
      <DashboardLayout role="editor">
        <Alert severity="error" sx={{ mt: 4, borderRadius: 2, fontWeight: 600 }}>
          Could not load live Layer 4 evaluation report for manuscript #{id}. Please verify the backend is running.
        </Alert>
      </DashboardLayout>
    );
  }

  const violations = reportData.editorial_rules.violations || [];

  return (
    <DashboardLayout role="editor">
      <Head>
        <title>Evaluation Report #{id} - Editorial Suite</title>
        {/* Inject CSS Print Stylesheet for A4 Paper formatting */}
        <style type="text/css" media="print">{`
          @page {
            size: A4 portrait;
            margin: 1.5cm 1cm 1.5cm 1cm;
          }
          body {
            background-color: #ffffff !important;
            color: #000000 !important;
          }
          /* Hide non-report layout elements during print */
          .print-hidden, header, nav, aside, button, a {
            display: none !important;
          }
          /* Force page containers and panels to stack nicely at full width */
          .print-stack {
            width: 100% !important;
            max-width: 100% !important;
            flex-basis: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
          }
          /* Force charts, progress bars, and badges to print colors */
          * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          .MuiPaper-root {
            border: 1px solid #e2e8f0 !important;
            background-color: #ffffff !important;
            color: #0f172a !important;
            box-shadow: none !important;
          }
          h4, h6, p, span, div {
            color: #0f172a !important;
          }
        `}</style>
      </Head>

      <Box ref={printRef} data-print-section sx={{ maxWidth: 1100, mx: 'auto', px: 2, py: 4, minHeight: '100vh', transition: 'all 0.25s ease' }}>

        {/* ── HEADER & EXPORT ACTION BAR (Hidden on print) ─────────────────── */}
        <Box className="print-hidden" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2, mb: 4 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: colors.text, mb: 0.5 }}>
              Evaluation Report
            </Typography>
            <Typography variant="body2" sx={{ color: colors.muted, fontWeight: 500 }}>
              ID: {reportData.prediction.manuscript_id} &nbsp;·&nbsp; Live PostgreSQL Database Mode
            </Typography>
          </Box>
          
          {/* Action buttons suite */}
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button
              variant="contained"
              component="a"
              href={`/editor/evaluation/${id}/academic-report`}
              target="_blank"
              startIcon={<PrintIcon />}
              sx={{
                bgcolor: '#3b82f6',
                color: '#ffffff',
                '&:hover': { bgcolor: '#2563eb' },
                px: 2.5,
                py: 1,
                borderRadius: 2,
                fontWeight: 600,
                textTransform: 'none'
              }}
            >
              Export Report to PDF
            </Button>
            <Button
              variant="contained"
              component="a"
              href={`http://127.0.0.1:8000/api/v1/manuscripts/${id}/pdf`}
              download
              startIcon={<PictureAsPdfIcon />}
              sx={{
                bgcolor: '#10b981',
                color: '#ffffff',
                '&:hover': { bgcolor: '#059669' },
                px: 2.5,
                py: 1,
                borderRadius: 2,
                fontWeight: 600,
                textTransform: 'none'
              }}
            >
              Download Original PDF
            </Button>
            <Button
              variant="outlined"
              startIcon={<CodeIcon />}
              onClick={handleDownloadJSON}
              sx={{
                borderColor: colors.border,
                color: colors.text,
                '&:hover': { borderColor: colors.muted, bgcolor: colors.hover },
                px: 2.5,
                py: 1,
                borderRadius: 2,
                fontWeight: 600,
                textTransform: 'none'
              }}
            >
              Download DB JSON
            </Button>
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* Left Column: Verdict, Radar, and Rules */}
          <Grid size={{ xs: 12, md: 4 }} className="print-stack" sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Paper sx={{ p: 3, borderRadius: 3, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
              <VerdictCard
                recommendation={reportData.prediction.verdict as any}
                rejectProb={reportData.prediction.desk_reject_probability}
                confidence={reportData.prediction.confidence !== undefined && reportData.prediction.confidence !== null ? reportData.prediction.confidence : (reportData.prediction.confidence_level || 0.95)}
                modelId={reportData.prediction.model_version || "random_forest_exp_C"}
              />
            </Paper>

            <Paper sx={{ p: 3, borderRadius: 3, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
              <SemanticRadarChart scores={reportData.semantic_scores} />
            </Paper>

            {/* Layer 1 Rules Panel */}
            <Paper sx={{ p: 3, borderRadius: 3, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2, color: colors.text }}>
                Layer 1 — Deterministic Rule Engine Audit
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                {violations.length > 0 ? (
                  violations.map((violation, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2, borderRadius: 2,
                        bgcolor: isDark ? 'rgba(239, 68, 68, 0.08)' : 'rgba(239, 68, 68, 0.05)',
                        border: '1px solid rgba(239, 68, 68, 0.2)',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <WarningAmberIcon sx={{ color: '#ef4444' }} />
                        <Typography variant="body2" sx={{ fontWeight: 600, color: colors.text }}>
                          {violation}
                        </Typography>
                      </Box>
                      <Chip className="print-hidden" label="ALERT" size="small" sx={{ fontWeight: 700, bgcolor: '#ef4444', color: '#fff' }} />
                    </Box>
                  ))
                ) : (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2, borderRadius: 2, bgcolor: isDark ? 'rgba(34, 197, 94, 0.08)' : 'rgba(34, 197, 94, 0.05)', border: '1px solid rgba(34, 197, 94, 0.2)' }}>
                    <CheckCircleOutlinedIcon sx={{ color: '#22c55e' }} />
                    <Typography variant="body2" sx={{ fontWeight: 700, color: '#22c55e' }}>
                      All deterministic validation rules verified successfully.
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>

          {/* Right Column: Narrative Logs & SHAP Attributions */}
          <Grid size={{ xs: 12, md: 8 }} className="print-stack" sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <ExplainabilityLogs
              entries={[]}
              narrative={reportData.natural_language_explanation}
              rankedFeatures={reportData.feature_importance.ranked_features}
            />
          </Grid>
        </Grid>
      </Box>
    </DashboardLayout>
  );
}
