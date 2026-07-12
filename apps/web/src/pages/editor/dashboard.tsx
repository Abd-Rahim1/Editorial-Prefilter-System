import React, { useMemo, useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Box, Grid, Typography, Paper, Button, Alert, CircularProgress } from '@mui/material';
import DashboardLayout from '../../components/layout/DashboardLayout';
import UploadPanel from '../../components/ingestion/UploadPanel';
import StructuralRulesCard from '../../components/metrics/StructuralRulesCard';
import SemanticRadarChart from '../../components/charts/SemanticRadarChart';
import ExplainabilityLogs from '../../components/metrics/ExplainabilityLogs';
import { useAdminTheme } from '../../components/admin/AdminThemeContext';
import { getAuthToken, getAuthHeaders, handleUnauthorized } from '../../utils/auth';
import type { PipelineResult, QwenScores, QwenScoreKey, StructuralRule, ExplainabilityEntry } from '../../types/dashboard';

const INGEST_API_URL = '/api/v1/pipelines/evaluate';

const EMPTY_SCORES: QwenScores = {
  abstract_clarity: 0,
  structural_completeness: 0,
  methodological_strength: 0,
  experimental_strength: 0,
  argumentative_quality: 0,
  scope_alignment: 0,
};

const SCORE_LABELS: Record<QwenScoreKey, string> = {
  abstract_clarity: 'Abstract Clarity',
  structural_completeness: 'Structural Completeness',
  methodological_strength: 'Methodological Strength',
  experimental_strength: 'Experimental Strength',
  argumentative_quality: 'Argumentative Quality',
  scope_alignment: 'Scope Alignment',
};

const SCORE_TO_TYPE = (value: number) => {
  if (value >= 0.75) return 'success' as const;
  if (value >= 0.55) return 'warning' as const;
  return 'error' as const;
};

const buildExplainabilityEntries = (scores: QwenScores, fallback: boolean): ExplainabilityEntry[] => {
  const entries: ExplainabilityEntry[] = (Object.keys(SCORE_LABELS) as QwenScoreKey[]).map((typedKey) => {
    const value = typeof scores[typedKey] === 'number' ? (scores[typedKey] as number) : 0;
    const label = SCORE_LABELS[typedKey] || typedKey;
    return {
      id: `explain-${typedKey}`,
      section: label,
      issue: `${label} score is ${(value * 100).toFixed(0)}%`,
      reasoning: `Qwen evaluated ${label.toLowerCase()} at ${(value * 100).toFixed(0)}% confidence based on the manuscript content and section structure.`,
      confidence: Math.round(value * 100) / 100,
      type: SCORE_TO_TYPE(value),
      evidence: `Model annotation generated from the semantic scoring output for ${label}.`,
    };
  });

  if (fallback) {
    entries.unshift({
      id: 'explain-fallback',
      section: 'Fallback Mode',
      issue: 'Neutral scoring fallback was applied',
      reasoning: 'The ingest pipeline returned a fallback payload, so the dashboard preserves a conservative review recommendation.',
      confidence: 0.5,
      type: 'info',
      evidence: 'Fallback payload indicates a transient parsing or scoring failure; manual review is recommended.',
    });
  }

  return entries;
};

const mapViolationsToRules = (violations?: string[]): StructuralRule[] => {
  if (!violations || violations.length === 0) {
    return [
      {
        id: 'rule-pass-1',
        label: 'No structural rule violations detected.',
        detail: 'Layer 1 validation did not flag any mandatory section or formatting issues.',
        status: 'pass',
      },
    ];
  }

  return violations.map((violation, index) => ({
    id: `rule-${index + 1}`,
    label: violation,
    detail: violation,
    status: 'warning',
  }));
};

export default function EditorDashboardPage() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('Select a PDF to start analysis.');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthed, setIsAuthed] = useState(false);

  const { isDark, colors } = useAdminTheme();

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

  const rules = useMemo(() => mapViolationsToRules(result?.layer1_violations), [result?.layer1_violations]);
  const scores = result?.qwen_scores ?? result?.layer2_scores ?? EMPTY_SCORES;
  const entries = useMemo(
    () => buildExplainabilityEntries(scores, Boolean(result?.fallback_used)),
    [scores, result?.fallback_used]
  );

  const handleFileSelected = async (file: File) => {
    setSelectedFile(file);
    setError(null);
    setStatusMessage(`Ready to upload ${file.name}`);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a PDF manuscript before uploading.');
      return;
    }

    if (!getAuthToken()) {
      handleUnauthorized(router);
      return;
    }

    setLoading(true);
    setError(null);
    setStatusMessage('Uploading manuscript to ingest endpoint...');

    try {
      const payload = new FormData();
      payload.append('file', selectedFile);

      const response = await fetch(INGEST_API_URL, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: payload,
      });

      if (!response.ok) {
        if (response.status === 401) {
          handleUnauthorized(router);
          return;
        }
        const body = await response.json().catch(() => null);
        const message = body?.detail || body?.error || `Upload failed with status ${response.status}`;
        throw new Error(message);
      }

      const json = (await response.json()) as any;

      if (json && json.success && json.message && json.message.includes('Processing started') && json.manuscript_id) {
        setStatusMessage('Processing started on the server — awaiting results...');

        const pollForResults = async (id: string | number, timeoutMs = 120000, intervalMs = 3000) => {
          const start = Date.now();
          while (Date.now() - start < timeoutMs) {
            try {
              const res = await fetch('/api/manuscripts', {
                headers: getAuthHeaders()
              });
              if (!res.ok) {
                if (res.status === 401) {
                  handleUnauthorized(router);
                  return null;
                }
                await new Promise((r) => setTimeout(r, intervalMs));
                continue;
              }
              const body = await res.json().catch(() => null);
              const list = (body && body.manuscripts) || [];
              const found = list.find((m: any) => String(m.id) === String(id));
              if (found && found.qwen_scores) {
                const mapped: PipelineResult = {
                  manuscript_id: found.id,
                  metadata: { title: found.title, filename: found.filename },
                  layer1_violations: found.layer1_violations || [],
                  qwen_scores: found.qwen_scores,
                  raw_qwen: found.qwen_scores,
                  fallback_used: false,
                  success: true,
                } as any;
                return mapped;
              }
            } catch (e) {
              // ignore and retry
            }
            await new Promise((r) => setTimeout(r, intervalMs));
          }
          return null;
        };

        const polled = await pollForResults(json.manuscript_id);
        if (polled) {
          setResult(polled);
          setStatusMessage('Processing complete — results available.');
        } else {
          setStatusMessage('Processing is still running; please check back later.');
        }
      } else {
        setResult(json as PipelineResult);
        setStatusMessage('Manuscript ingested successfully. Review the Layer 1 and Layer 2 panels below.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected upload error');
      setStatusMessage('Upload failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!authChecked || !isAuthed) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', bgcolor: colors.bg }}>
        <CircularProgress size={40} sx={{ color: colors.primary }} />
      </Box>
    );
  }

  return (
    <DashboardLayout role="editor">
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, p: 4, minHeight: '100vh', transition: 'all 0.25s ease' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, mb: 1, color: colors.text }}>
            Author Dashboard
          </Typography>
          <Typography variant="body1" sx={{ color: colors.muted, maxWidth: 680 }}>
            Upload a new PDF manuscript to evaluate the rule-based validation layer and the Qwen semantic scoring layer. Results are served directly from the database-backed ingest API.
          </Typography>
        </Box>

        <Grid container spacing={3}>
          <Grid size={{ xs: 12, lg: 5 }}>
            <Paper sx={{ p: 3, borderRadius: 3, minHeight: 360, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
              <UploadPanel onFileSelected={handleFileSelected} loading={loading} selectedFile={selectedFile} />

              <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {error && <Alert severity="error" sx={{ borderRadius: 2 }}>{error}</Alert>}
                <Typography sx={{ fontSize: '0.8rem', color: colors.muted }}>{statusMessage}</Typography>
                <Button
                  variant="contained"
                  size="large"
                  disabled={loading || !selectedFile}
                  onClick={handleUpload}
                  sx={{ mt: 1, py: 1.5, borderRadius: 3, bgcolor: colors.primary }}
                >
                  {loading ? 'Uploading…' : 'Analyze Manuscript'}
                </Button>
              </Box>
            </Paper>

            <Paper sx={{ mt: 3, p: 3, borderRadius: 3, bgcolor: isDark ? 'rgba(15,23,42,0.88)' : 'rgba(0,0,0,0.02)', border: `1px solid ${colors.border}` }}>
              <Typography sx={{ fontSize: '0.75rem', fontWeight: 700, color: colors.muted, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 1.2 }}>
                Latest ingest details
              </Typography>
              <Typography sx={{ fontSize: '0.9rem', color: colors.text, mb: 0.5 }}>
                Manuscript ID: {result?.manuscript_id ?? 'n/a'}
              </Typography>
              <Typography sx={{ fontSize: '0.9rem', color: colors.text, mb: 0.5 }}>
                Title: {result?.metadata?.title ?? selectedFile?.name ?? 'Untitled'}
              </Typography>
              <Typography sx={{ fontSize: '0.9rem', color: colors.text }}>
                Layer 1 status: {result ? (result.layer1_violations?.length ? `${result.layer1_violations.length} issues found` : 'No issues detected') : 'Waiting for new upload'}
              </Typography>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, lg: 7 }}>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Paper sx={{ p: 3, borderRadius: 3, minHeight: 350, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
                  <StructuralRulesCard rules={rules} />
                </Paper>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <Paper sx={{ p: 3, borderRadius: 3, minHeight: 350, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
                  <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: colors.muted, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 1.2 }}>
                    Layer 2 · Semantic Scoring
                  </Typography>
                  <SemanticRadarChart scores={scores} />
                </Paper>
              </Grid>

              <Grid size={{ xs: 12 }}>
                <Paper sx={{ p: 3, borderRadius: 3, bgcolor: colors.panel, border: `1px solid ${colors.border}` }}>
                  <ExplainabilityLogs entries={entries} />
                </Paper>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </Box>
    </DashboardLayout>
  );
}
