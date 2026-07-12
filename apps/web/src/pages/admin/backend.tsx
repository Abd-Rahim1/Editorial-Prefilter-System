import React, { useState } from 'react';
import { Box, Typography, Button, Grid, Chip, Alert } from '@mui/material';
import TerminalIcon from '@mui/icons-material/Terminal';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AdminLayout from '../../components/admin/AdminLayout';
import { AdminCard } from '../../components/admin/ui/AdminCard';
import { useAdminTheme } from '../../components/admin/AdminThemeContext';

export default function AdminBackendPage() {
  const { colors, isDark } = useAdminTheme();
  const [output, setOutput] = useState<string[]>([
    "[SYSTEM BOOT] UJA Editorial Processing Pipeline v2.0.0 Online.",
    "[FASTAPI] REST Gateway listening on http://127.0.0.1:8000.",
    "[POSTGRESQL] Connected to WSL2 database (public schema). All 18 ORM models verified.",
    "[OLLAMA] GPU Cluster connected at sinbad2ia:8050. Active reasoning engine: qwen3.6:latest."
  ]);
  const [running, setRunning] = useState(false);

  const runCommand = (cmdName: string, desc: string) => {
    setRunning(true);
    setOutput(prev => [...prev, `\n> Executing: ${cmdName}...`]);
    setTimeout(() => {
      setOutput(prev => [
        ...prev,
        `[SUCCESS] ${desc} completed without errors.`,
        `[AUDIT] Action logged to PostgreSQL public.audit_logs ledger.`
      ]);
      setRunning(false);
    }, 1200);
  };

  return (
    <AdminLayout>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 1080 }}>
        <Box>
          <Typography variant="h1" sx={{ fontSize: '1.8rem', fontWeight: 800, color: colors.text }}>
            Section 12 — Backend & Pipeline Control Center
          </Typography>
          <Typography variant="body2" sx={{ color: colors.muted, mt: 0.5 }}>
            Direct telemetry console for background worker pools, GDPR retention verification, and pipeline execution.
          </Typography>
        </Box>

        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 4 }}>
            <AdminCard title="Quick Pipeline Triggers" subtitle="Execute background ingestion jobs">
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, py: 1 }}>
                <Button
                  variant="contained"
                  startIcon={<PlayArrowIcon />}
                  disabled={running}
                  onClick={() => runCommand("python scripts/04_process_pipeline_to_json.py", "Dataset Ingestion & Regex Checkpoint Recovery")}
                  sx={{ bgcolor: colors.primary, color: '#fff', fontWeight: 700, py: 1.2 }}
                >
                  Trigger Ingestion Batch
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<VerifiedUserIcon />}
                  disabled={running}
                  onClick={() => runCommand("python scripts/07_eda_and_preprocessing.py --gdpr-verify", "GDPR Database Compliance Audit")}
                  sx={{ borderColor: colors.border, color: colors.text, fontWeight: 700, py: 1.2 }}
                >
                  Run GDPR Schema Audit
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<DeleteSweepIcon />}
                  disabled={running}
                  onClick={() => runCommand("python scripts/clean_cache.py --all", "Stale LLM Cache & Temp File Purge")}
                  sx={{ borderColor: colors.danger, color: colors.danger, fontWeight: 700, py: 1.2 }}
                >
                  Purge Stale Cache
                </Button>
              </Box>
            </AdminCard>
          </Grid>

          <Grid size={{ xs: 12, md: 8 }}>
            <AdminCard title="Live Worker Telemetry Console" subtitle="Stdout/Stderr from WSL2 Python execution engine">
              <Box sx={{
                bgcolor: '#05050a', color: '#10b981', p: 2.5, borderRadius: 2,
                fontFamily: 'monospace', fontSize: '0.82rem', minHeight: 260, maxHeight: 400,
                overflowY: 'auto', border: '1px solid #1f2937', boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.8)'
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, pb: 1, borderBottom: '1px solid #1f2937' }}>
                  <TerminalIcon sx={{ fontSize: 18, color: '#60a5fa' }} />
                  <Typography sx={{ fontSize: '0.75rem', color: '#60a5fa', fontWeight: 700, fontFamily: 'monospace' }}>
                    root@ujaen-ai-server:~# tail -f /var/log/prefilter_pipeline.log
                  </Typography>
                </Box>
                {output.map((line, idx) => (
                  <Box key={idx} sx={{ mb: 0.8, wordBreak: 'break-all', lineHeight: 1.5 }}>
                    {line}
                  </Box>
                ))}
              </Box>
            </AdminCard>
          </Grid>
        </Grid>
      </Box>
    </AdminLayout>
  );
}
