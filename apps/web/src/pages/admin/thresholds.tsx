import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Slider, Grid, Chip, Alert } from '@mui/material';
import TuneIcon from '@mui/icons-material/Tune';
import SaveIcon from '@mui/icons-material/Save';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AdminLayout from '../../components/admin/AdminLayout';
import { AdminCard } from '../../components/admin/ui/AdminCard';
import { useAdminTheme } from '../../components/admin/AdminThemeContext';
import { getThresholds, updateThresholds } from '../../components/admin/AdminApiClient';

export default function AdminThresholdsPage() {
  const { colors, isDark } = useAdminTheme();
  const [rejectThresh, setRejectThresh] = useState<number>(0.50);
  const [reviewThresh, setReviewThresh] = useState<number>(0.80);
  const [loading, setLoading] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const fetchPolicy = async () => {
    setLoading(true);
    try {
      const res = await getThresholds();
      if (res) {
        setRejectThresh(res.auto_reject_threshold || 0.50);
        setReviewThresh(res.manual_review_threshold || 0.80);
      }
    } catch (err) {
      console.warn('Failed to fetch policy thresholds:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, []);

  const handleSave = async () => {
    if (rejectThresh >= reviewThresh) {
      alert("Auto Reject threshold must be strictly lower than Manual Review threshold!");
      return;
    }
    try {
      await updateThresholds(rejectThresh, reviewThresh);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 4000);
    } catch (err) {
      alert("Failed to update policy thresholds in PostgreSQL.");
    }
  };

  const handleReset = () => {
    setRejectThresh(0.50);
    setReviewThresh(0.80);
  };

  return (
    <AdminLayout>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 960 }}>
        <Box>
          <Typography variant="h1" sx={{ fontSize: '1.8rem', fontWeight: 800, color: colors.text }}>
            Section 3 — Policy Management & Thresholds
          </Typography>
          <Typography variant="body2" sx={{ color: colors.muted, mt: 0.5 }}>
            Calibrate decision boundaries for automated desk rejection, manual editorial routing, and fast-track approval.
          </Typography>
        </Box>

        {savedSuccess && (
          <Alert icon={<CheckCircleIcon fontSize="inherit" />} severity="success" sx={{ fontWeight: 700, borderRadius: 2 }}>
            Policy thresholds successfully committed to PostgreSQL (system_settings & threshold_history ledgers)!
          </Alert>
        )}

        <AdminCard title="Editorial Decision Threshold Sliders" subtitle="Directly updates public.system_settings table in PostgreSQL">
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, py: 2 }}>
            {/* Slider 1: Auto Reject */}
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Box>
                  <Typography sx={{ fontSize: '0.95rem', fontWeight: 700, color: colors.text }}>
                    Automated Desk Rejection Threshold
                  </Typography>
                  <Typography variant="caption" sx={{ color: colors.muted }}>
                    Manuscripts with predicted quality score below this cutoff are automatically flagged for desk rejection.
                  </Typography>
                </Box>
                <Chip
                  label={`<= ${(rejectThresh * 100).toFixed(0)}%`}
                  size="medium"
                  sx={{ bgcolor: 'rgba(239,68,68,0.15)', color: '#ef4444', fontWeight: 800, fontSize: '0.9rem', border: '1px solid rgba(239,68,68,0.3)', px: 1 }}
                />
              </Box>
              <Slider
                value={rejectThresh}
                min={0.10}
                max={0.90}
                step={0.01}
                onChange={(_, val) => setRejectThresh(val as number)}
                sx={{
                  color: '#ef4444',
                  height: 8,
                  '& .MuiSlider-thumb': { width: 22, height: 22, bgcolor: colors.panel, border: '3px solid #ef4444', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }
                }}
              />
            </Box>

            {/* Slider 2: Manual Review */}
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Box>
                  <Typography sx={{ fontSize: '0.95rem', fontWeight: 700, color: colors.text }}>
                    Manual Editorial Review Threshold
                  </Typography>
                  <Typography variant="caption" sx={{ color: colors.muted }}>
                    Manuscripts scoring between Reject and this threshold are routed to Senior Editors for manual evaluation.
                  </Typography>
                </Box>
                <Chip
                  label={`<= ${(reviewThresh * 100).toFixed(0)}%`}
                  size="medium"
                  sx={{ bgcolor: 'rgba(245,158,11,0.15)', color: '#f59e0b', fontWeight: 800, fontSize: '0.9rem', border: '1px solid rgba(245,158,11,0.3)', px: 1 }}
                />
              </Box>
              <Slider
                value={reviewThresh}
                min={0.20}
                max={0.95}
                step={0.01}
                onChange={(_, val) => setReviewThresh(val as number)}
                sx={{
                  color: '#f59e0b',
                  height: 8,
                  '& .MuiSlider-thumb': { width: 22, height: 22, bgcolor: colors.panel, border: '3px solid #f59e0b', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }
                }}
              />
            </Box>

            {/* Live Values Visual Band Explanation */}
            <Box sx={{ p: 2.5, borderRadius: 2, bgcolor: isDark ? 'rgba(0,0,0,0.25)' : '#f8fafc', border: `1px solid ${colors.border}`, mt: 1 }}>
              <Typography sx={{ fontSize: '0.85rem', fontWeight: 800, color: colors.text, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                <TuneIcon sx={{ fontSize: 18, color: colors.primary }} /> Live Decision Band Breakdown
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Box sx={{ p: 1.5, borderRadius: 1.5, borderLeft: '4px solid #ef4444', bgcolor: isDark ? 'rgba(239,68,68,0.08)' : '#fef2f2' }}>
                    <Typography sx={{ fontSize: '0.72rem', fontWeight: 800, color: '#ef4444', textTransform: 'uppercase' }}>
                      DESK REJECT BAND
                    </Typography>
                    <Typography sx={{ fontSize: '1.1rem', fontWeight: 800, color: colors.text, mt: 0.5 }}>
                      0.00 — {rejectThresh.toFixed(2)}
                    </Typography>
                    <Typography variant="caption" sx={{ color: colors.muted }}>
                      Automated decline notification
                    </Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Box sx={{ p: 1.5, borderRadius: 1.5, borderLeft: '4px solid #f59e0b', bgcolor: isDark ? 'rgba(245,158,11,0.08)' : '#fffbeb' }}>
                    <Typography sx={{ fontSize: '0.72rem', fontWeight: 800, color: '#f59e0b', textTransform: 'uppercase' }}>
                      MANUAL REVIEW BAND
                    </Typography>
                    <Typography sx={{ fontSize: '1.1rem', fontWeight: 800, color: colors.text, mt: 0.5 }}>
                      {rejectThresh.toFixed(2)} — {reviewThresh.toFixed(2)}
                    </Typography>
                    <Typography variant="caption" sx={{ color: colors.muted }}>
                      Human-in-the-loop editorial queue
                    </Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Box sx={{ p: 1.5, borderRadius: 1.5, borderLeft: '4px solid #22c55e', bgcolor: isDark ? 'rgba(34,197,94,0.08)' : '#f0fdf4' }}>
                    <Typography sx={{ fontSize: '0.72rem', fontWeight: 800, color: '#22c55e', textTransform: 'uppercase' }}>
                      FAST-TRACK APPROVAL
                    </Typography>
                    <Typography sx={{ fontSize: '1.1rem', fontWeight: 800, color: colors.text, mt: 0.5 }}>
                      {reviewThresh.toFixed(2)} — 1.00
                    </Typography>
                    <Typography variant="caption" sx={{ color: colors.muted }}>
                      Automated acceptance recommendation
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </Box>

            {/* Actions */}
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, pt: 1 }}>
              <Button variant="outlined" startIcon={<RestartAltIcon />} onClick={handleReset} sx={{ borderColor: colors.border, color: colors.text }}>
                Reset to Baseline
              </Button>
              <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSave} sx={{ bgcolor: colors.primary, color: '#fff', fontWeight: 700, px: 3 }}>
                Commit to PostgreSQL
              </Button>
            </Box>
          </Box>
        </AdminCard>
      </Box>
    </AdminLayout>
  );
}