import React, { useState, useRef } from 'react';
import { useRouter } from 'next/router';
import DashboardLayout from '../../components/layout/DashboardLayout';
import {
  Typography, Box, Button, CircularProgress, Snackbar, Alert, Modal, Backdrop, Fade
} from '@mui/material';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';
import {
  LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer
} from 'recharts';
import {
  FileText, CheckCircle, Clock, XCircle, TrendingUp, ChevronRight, Upload, FileCheck, Download, Plus
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useAdminTheme } from '../../components/admin/AdminThemeContext';
import { authAxiosGet, authAxiosPost, getAuthToken, handleUnauthorized } from '../../utils/auth';

// ─── TYPES ───────────────────────────────────────────────────────────────────

export interface KPIStats {
  total: number;
  accepted: number;
  attention: number;
  rejected: number;
  avg_confidence: string;
}

export interface TimelineBucket {
  date: string;
  'Accept for Review': number;
  'Requires Attention': number;
  'Reject': number;
}

export interface DistributionItem {
  name: string;
  value: number;
}

export interface EvaluationRow {
  id: number;
  title: string;
  filename: string;
  upload_date: string;
  status: string;
  num_pages: number;
  total_word_count: number;
  recommendation?: string;
  predicted_label: boolean | null;
  desk_reject_probability: number | null;
  confidence: number | null;
}

export interface AnalyticsResponse {
  success: boolean;
  kpis: KPIStats;
  timeline: TimelineBucket[];
  distribution: DistributionItem[];
  recent_evaluations: EvaluationRow[];
}

const PIE_COLORS: Record<string, string> = {
  'Accept for Review': '#10b981',
  'Requires Attention': '#f59e0b',
  'Reject': '#ef4444',
};

// ─── ACTIVITY TYPE → DISPLAY MAPPING ────────────────────────────────────────

const ACTIVITY_DISPLAY: Record<string, { label: string; type: string }> = {
  manuscript_uploaded:      { label: 'Manuscript uploaded',           type: 'upload' },
  layer1_parsing_completed: { label: 'Layer 1 — Parsing completed',   type: 'eval'   },
  layer1_rules_completed:   { label: 'Layer 1 — Rules checked',       type: 'eval'   },
  layer2_completed:         { label: 'Layer 2 — Qwen scoring done',   type: 'eval'   },
  layer3_completed:         { label: 'Layer 3 — Recommendation ready',type: 'eval'   },
  layer4_completed:         { label: 'Layer 4 — Explanation generated',type: 'export' },
  evaluation_completed:     { label: 'Evaluation completed',          type: 'export' },
  evaluation_failed:        { label: 'Evaluation failed',             type: 'reject' },
  report_exported:          { label: 'Report exported',               type: 'export' },
};

function formatRelativeTime(isoStr: string): string {
  if (!isoStr) return 'Unknown';
  try {
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days  = Math.floor(diff / 86400000);
    if (mins  < 1)   return 'Just now';
    if (mins  < 60)  return `${mins}m ago`;
    if (hours < 24)  return `${hours}h ago`;
    if (days  < 7)   return `${days}d ago`;
    return new Date(isoStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return isoStr;
  }
}

function getActivityStyles(type: string, isDark: boolean) {
  if (isDark) {
    switch (type) {
      case 'upload': return { bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.3)', text: '#34d399' };
      case 'eval': return { bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.3)', text: '#fbbf24' };
      case 'reject': return { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.3)', text: '#f87171' };
      case 'export': default: return { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.3)', text: '#60a5fa' };
    }
  } else {
    switch (type) {
      case 'upload': return { bg: 'rgba(22, 163, 74, 0.1)', border: 'rgba(22, 163, 74, 0.2)', text: '#16a34a' };
      case 'eval': return { bg: 'rgba(217, 119, 6, 0.1)', border: 'rgba(217, 119, 6, 0.2)', text: '#d97706' };
      case 'reject': return { bg: 'rgba(220, 38, 38, 0.1)', border: 'rgba(220, 38, 38, 0.2)', text: '#dc2626' };
      case 'export': default: return { bg: 'rgba(37, 99, 235, 0.1)', border: 'rgba(37, 99, 235, 0.2)', text: '#2563eb' };
    }
  }
}

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────────

export default function EditorQueuePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isDark, colors } = useAdminTheme();

  type ToastSeverity = 'success' | 'error' | 'warning' | 'info';
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' as ToastSeverity });
  const [activeId, setActiveId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
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

  const { data: analyticsData, isLoading } = useQuery<AnalyticsResponse | null>({
    queryKey: ['editor-analytics'],
    queryFn: async () => {
      if (!getAuthToken()) return null;
      return await authAxiosGet<AnalyticsResponse>('/api/v1/editor/analytics');
    },
    enabled: isAuthed,
    refetchInterval: (query) => {
      if (!query.state.data) return false;
      return 10000;
    },
  });

  const { data: statusData } = useQuery({
    queryKey: ['pipeline-status', activeId],
    queryFn: async () => {
      if (!activeId || !getAuthToken()) return null;
      const data = await authAxiosGet<any>(`/api/v1/pipelines/status/${activeId}`);
      if (!data) return null;
      const progress = data?.stage_progress || {};
      if (progress.stage_4 === 'completed' || data?.status?.toLowerCase() === 'reviewed' || data?.status?.toLowerCase() === 'complete') {
        queryClient.invalidateQueries({ queryKey: ['editor-analytics'] });
      }
      return data;
    },
    enabled: !!activeId && modalOpen,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 1000;
      const progress = data.stage_progress || {};
      if (progress.stage_4 === 'completed' || data.status?.toLowerCase() === 'reviewed' || data.status?.toLowerCase() === 'complete' || data.status?.toLowerCase() === 'failed') {
        queryClient.invalidateQueries({ queryKey: ['editor-analytics'] });
        return false;
      }
      return 1000;
    }
  });

  React.useEffect(() => {
    if (statusData) {
      const progress = statusData.stage_progress || {};
      if (progress.stage_4 === 'completed' || statusData.status?.toLowerCase() === 'reviewed' || statusData.status?.toLowerCase() === 'complete') {
        queryClient.invalidateQueries({ queryKey: ['editor-analytics'] });
      }
    }
  }, [statusData, queryClient]);

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('version', 'v5');

      const data = await authAxiosPost<any>('/api/v1/pipelines/evaluate', formData, {
        timeout: 300000,
      });
      if (!data) throw new Error("Authentication failed or request unauthorized.");
      return data;
    },
    onSuccess: (data: any) => {
      const manuscriptId = data?.manuscript_id;
      if (manuscriptId) {
        setActiveId(manuscriptId);
        setToast({ open: true, message: 'Manuscript submitted to the four-layer evaluation pipeline.', severity: 'info' });
        queryClient.invalidateQueries({ queryKey: ['editor-analytics'] });
        queryClient.invalidateQueries({ queryKey: ['editor-recent-activity'] });
      } else {
        setToast({ open: true, message: 'Manuscript uploaded successfully.', severity: 'success' });
        queryClient.invalidateQueries({ queryKey: ['editor-analytics'] });
        queryClient.invalidateQueries({ queryKey: ['editor-recent-activity'] });
      }
    },
    onError: (err: any) => {
      console.error('Upload failed', err);
      const errMsg = err.response?.data?.detail || err.message || 'Upload failed';
      setToast({ open: true, message: `Upload error: ${errMsg}`, severity: 'error' });
    }
  });

  const handleCloseToast = () => {
    setToast(prev => ({ ...prev, open: false }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setActiveId(null);
      setModalOpen(true);
      uploadMutation.mutate(files[0]);
    }
  };

  const triggerUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  const stagesList = [
    { key: 'stage_0', label: 'Extracting manuscript text and metadata' },
    { key: 'stage_1', label: 'Applying editorial rule checks' },
    { key: 'stage_2', label: 'Evaluating semantic quality with Qwen' },
    { key: 'stage_3', label: 'Computing probabilistic recommendation' },
    { key: 'stage_4', label: 'Generating SHAP-based explanation' },
  ];

  const isPipelineComplete = statusData?.stage_progress?.stage_4 === 'completed' ||
                             statusData?.status?.toLowerCase() === 'reviewed' ||
                             statusData?.status?.toLowerCase() === 'complete';

  // Auto-redirect removed intentionally.
  // The "View Analysis Dashboard" button handles navigation on explicit user click.
  // This prevents race conditions where the report may not yet be saved when the
  // stage_4 'completed' signal fires in the progress tracker.

  const kpis = analyticsData?.kpis || { total: 0, accepted: 0, attention: 0, rejected: 0, avg_confidence: '0.00' };
  const timeline = analyticsData?.timeline || [];
  const distribution = analyticsData?.distribution || [];
  const recentEvals = analyticsData?.recent_evaluations || [];

  // ── Real activity from audit_logs ──────────────────────────────────────────
  const { data: activityData } = useQuery({
    queryKey: ['editor-recent-activity'],
    queryFn: async () => {
      if (!getAuthToken()) return null;
      return await authAxiosGet<any>('/api/v1/editor/recent-activity?limit=8');
    },
    enabled: isAuthed,
    refetchInterval: (query) => {
      if (!query.state.data) return false;
      return 15000;
    },
  });
  const recentActivities: Array<{
    id: number;
    manuscript_id: number | null;
    manuscript_title: string;
    action: string;
    details: string;
    created_at: string;
  }> = activityData?.activity || [];

  const totalCount = kpis.total || 1;
  const acceptPct = ((kpis.accepted / totalCount) * 100).toFixed(1);
  const attentionPct = ((kpis.attention / totalCount) * 100).toFixed(1);
  const rejectPct = ((kpis.rejected / totalCount) * 100).toFixed(1);

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return `${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}\n${d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return dateStr;
    }
  };

  if (!authChecked || !isAuthed) {
    return (
      <div 
        className="min-h-screen flex justify-center items-center p-8 w-full transition-colors duration-250 ease-in-out"
        style={{ backgroundColor: colors.bg, color: colors.text }}
      >
        <CircularProgress size={40} sx={{ color: colors.primary }} />
      </div>
    );
  }

  return (
    <div 
      className="min-h-screen p-8 w-full transition-colors duration-250 ease-in-out"
      style={{ backgroundColor: colors.bg, color: colors.text }}
    >
      <DashboardLayout role="editor">
        <style>{`
          .editor-themed-card {
            background-color: ${colors.panel} !important;
            border-color: ${colors.border} !important;
          }
          .editor-themed-text {
            color: ${colors.text} !important;
          }
          .editor-themed-muted {
            color: ${colors.muted} !important;
          }
          .editor-themed-border {
            border-color: ${colors.border} !important;
          }
          .editor-themed-row {
            border-bottom: 1px solid ${colors.border} !important;
            transition: background-color 0.2s ease;
          }
          .editor-themed-row:hover {
            background-color: ${colors.hover} !important;
          }
          .editor-themed-action-btn {
            background-color: ${isDark ? '#334155' : '#f1f5f9'} !important;
            color: ${colors.text} !important;
            border: 1px solid ${colors.border} !important;
            transition: all 0.2s ease;
          }
          .editor-themed-action-btn:hover {
            background-color: ${isDark ? '#475569' : '#e2e8f0'} !important;
          }
          .editor-themed-select {
            background-color: ${colors.panel} !important;
            border-color: ${colors.border} !important;
            color: ${colors.text} !important;
          }
          .editor-themed-select option {
            background-color: ${colors.panel} !important;
            color: ${colors.text} !important;
          }
        `}</style>

        <div className="w-full">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />

          {/* ── 1. HEADER (Welcome removed, button aligned right) ──────────── */}
          <div className="flex flex-row justify-end items-center w-full mb-6">
            <button
              onClick={triggerUpload}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer"
              aria-label="Switch theme mode or upload manuscript"
            >
              <Plus className="w-4 h-4" />
              <span>Upload Manuscript</span>
            </button>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center h-96">
              <CircularProgress sx={{ color: colors.primary }} size={48} />
            </div>
          ) : (
            <>
              {/* ── 2. KPI CARDS (Top Row) ─────────────────────────────────── */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
                {/* Card 1: Total Manuscripts */}
                <div className="editor-themed-card border rounded-xl p-5 shadow-sm flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold editor-themed-muted block">Total Manuscripts</span>
                      <span className="text-3xl font-bold editor-themed-text mt-2 block">{kpis.total}</span>
                    </div>
                    <div 
                      className="p-2.5 rounded-xl border"
                      style={{ 
                        backgroundColor: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(37, 99, 235, 0.08)',
                        borderColor: isDark ? 'rgba(59, 130, 246, 0.3)' : 'rgba(37, 99, 235, 0.2)'
                      }}
                    >
                      <FileText className="w-5 h-5" style={{ color: isDark ? '#60a5fa' : '#2563eb' }} />
                    </div>
                  </div>
                  <span className="text-xs editor-themed-muted mt-4 font-medium">All time submissions</span>
                </div>

                {/* Card 2: Accept for Review */}
                <div className="editor-themed-card border rounded-xl p-5 shadow-sm flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold editor-themed-muted block">Accept for Review</span>
                      <span className="text-3xl font-bold mt-2 block" style={{ color: isDark ? '#34d399' : '#16a34a' }}>{kpis.accepted}</span>
                    </div>
                    <div 
                      className="p-2.5 rounded-xl border"
                      style={{ 
                        backgroundColor: isDark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(22, 163, 74, 0.08)',
                        borderColor: isDark ? 'rgba(16, 185, 129, 0.3)' : 'rgba(22, 163, 74, 0.2)'
                      }}
                    >
                      <CheckCircle className="w-5 h-5" style={{ color: isDark ? '#34d399' : '#16a34a' }} />
                    </div>
                  </div>
                  <span className="text-xs editor-themed-muted mt-4 font-medium">{acceptPct}% of total</span>
                </div>

                {/* Card 3: Requires Attention */}
                <div className="editor-themed-card border rounded-xl p-5 shadow-sm flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold editor-themed-muted block">Requires Attention</span>
                      <span className="text-3xl font-bold mt-2 block" style={{ color: isDark ? '#fbbf24' : '#d97706' }}>{kpis.attention}</span>
                    </div>
                    <div 
                      className="p-2.5 rounded-xl border"
                      style={{ 
                        backgroundColor: isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(217, 119, 6, 0.08)',
                        borderColor: isDark ? 'rgba(245, 158, 11, 0.3)' : 'rgba(217, 119, 6, 0.2)'
                      }}
                    >
                      <Clock className="w-5 h-5" style={{ color: isDark ? '#fbbf24' : '#d97706' }} />
                    </div>
                  </div>
                  <span className="text-xs editor-themed-muted mt-4 font-medium">{attentionPct}% of total</span>
                </div>

                {/* Card 4: Reject */}
                <div className="editor-themed-card border rounded-xl p-5 shadow-sm flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold editor-themed-muted block">Reject</span>
                      <span className="text-3xl font-bold mt-2 block" style={{ color: isDark ? '#f87171' : '#dc2626' }}>{kpis.rejected}</span>
                    </div>
                    <div 
                      className="p-2.5 rounded-xl border"
                      style={{ 
                        backgroundColor: isDark ? 'rgba(239, 68, 68, 0.15)' : 'rgba(220, 38, 38, 0.08)',
                        borderColor: isDark ? 'rgba(239, 68, 68, 0.3)' : 'rgba(220, 38, 38, 0.2)'
                      }}
                    >
                      <XCircle className="w-5 h-5" style={{ color: isDark ? '#f87171' : '#dc2626' }} />
                    </div>
                  </div>
                  <span className="text-xs editor-themed-muted mt-4 font-medium">{rejectPct}% of total</span>
                </div>

                {/* Card 5: Avg. Confidence */}
                <div className="editor-themed-card border rounded-xl p-5 shadow-sm flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold editor-themed-muted block">Avg. Confidence</span>
                      <span className="text-3xl font-bold mt-2 block" style={{ color: isDark ? '#c084fc' : '#9333ea' }}>{kpis.avg_confidence}</span>
                    </div>
                    <div 
                      className="p-2.5 rounded-xl border"
                      style={{ 
                        backgroundColor: isDark ? 'rgba(168, 85, 247, 0.15)' : 'rgba(147, 51, 234, 0.08)',
                        borderColor: isDark ? 'rgba(168, 85, 247, 0.3)' : 'rgba(147, 51, 234, 0.2)'
                      }}
                    >
                      <TrendingUp className="w-5 h-5" style={{ color: isDark ? '#c084fc' : '#9333ea' }} />
                    </div>
                  </div>
                  <span className="text-xs editor-themed-muted mt-4 font-medium">Across all evaluations</span>
                </div>
              </div>

              {/* ── 3. CHARTS (Middle Row) ─────────────────────────────────── */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                {/* Left Chart: Evaluations Over Time */}
                <div className="lg:col-span-2 editor-themed-card border rounded-xl p-6 shadow-sm flex flex-col justify-between">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                    <h3 className="text-base font-bold editor-themed-text tracking-wide">
                      Evaluations Over Time
                    </h3>
                    <div className="flex items-center gap-4 text-xs font-semibold">
                      <span className="flex items-center gap-1.5" style={{ color: isDark ? '#34d399' : '#16a34a' }}>
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                        Accept for Review
                      </span>
                      <span className="flex items-center gap-1.5" style={{ color: isDark ? '#fbbf24' : '#d97706' }}>
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
                        Requires Attention
                      </span>
                      <span className="flex items-center gap-1.5" style={{ color: isDark ? '#f87171' : '#dc2626' }}>
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                        Reject
                      </span>
                      <select className="editor-themed-select border rounded-lg px-2.5 py-1 text-xs focus:outline-none ml-2 cursor-pointer">
                        <option>Last 6 weeks</option>
                        <option>Last 30 days</option>
                      </select>
                    </div>
                  </div>

                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={timeline} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
                        <XAxis dataKey="date" stroke={colors.border} tick={{ fill: colors.muted, fontSize: 11 }} tickLine={false} />
                        <YAxis stroke={colors.border} tick={{ fill: colors.muted, fontSize: 11 }} tickLine={false} allowDecimals={false} />
                        <RechartsTooltip
                          contentStyle={{
                            backgroundColor: colors.panel,
                            borderColor: colors.border,
                            borderRadius: '0.75rem',
                            color: colors.text,
                            fontSize: '0.75rem',
                            boxShadow: isDark ? '0 10px 15px -3px rgba(0,0,0,0.5)' : '0 4px 6px -1px rgba(0,0,0,0.05)'
                          }}
                        />
                        <Line type="monotone" dataKey="Accept for Review" stroke="#10b981" strokeWidth={2.5} dot={{ r: 4, fill: '#10b981', strokeWidth: 2, stroke: colors.panel }} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey="Requires Attention" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 4, fill: '#f59e0b', strokeWidth: 2, stroke: colors.panel }} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey="Reject" stroke="#ef4444" strokeWidth={2.5} dot={{ r: 4, fill: '#ef4444', strokeWidth: 2, stroke: colors.panel }} activeDot={{ r: 6 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Right Chart: Evaluation Summary Donut */}
                <div className="lg:col-span-1 editor-themed-card border rounded-xl p-6 shadow-sm flex flex-col justify-between">
                  <h3 className="text-base font-bold editor-themed-text tracking-wide mb-2">
                    Evaluation Summary
                  </h3>
                  
                  <div className="relative h-56 w-full flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={distribution}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={82}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {distribution.map((entry, idx) => (
                            <Cell key={`cell-${idx}`} fill={PIE_COLORS[entry.name] || '#3b82f6'} />
                          ))}
                        </Pie>
                        <RechartsTooltip
                          contentStyle={{
                            backgroundColor: colors.panel,
                            borderColor: colors.border,
                            borderRadius: '0.75rem',
                            color: colors.text,
                            fontSize: '0.75rem'
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    {/* Center Text inside Donut */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                      <span className="text-3xl font-extrabold editor-themed-text">{kpis.total}</span>
                      <span className="text-xs editor-themed-muted font-medium uppercase tracking-wider">Total</span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2.5 pt-4 editor-themed-border border-t text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                        <span className="font-semibold editor-themed-text">Accept for Review</span>
                      </div>
                      <span className="editor-themed-muted font-mono">{acceptPct}% ({kpis.accepted})</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
                        <span className="font-semibold editor-themed-text">Requires Attention</span>
                      </div>
                      <span className="editor-themed-muted font-mono">{attentionPct}% ({kpis.attention})</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                        <span className="font-semibold editor-themed-text">Reject</span>
                      </div>
                      <span className="editor-themed-muted font-mono">{rejectPct}% ({kpis.rejected})</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── 4. BOTTOM ROW (Table & Sidebar) ────────────────────────── */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column (col-span-2): Recent Evaluations Table */}
                <div className="lg:col-span-2 editor-themed-card border rounded-xl p-6 shadow-sm flex flex-col justify-between">
                  <div>
                    <h3 className="text-base font-bold editor-themed-text mb-4">
                      Recent Evaluations
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="editor-themed-border border-b text-xs font-semibold editor-themed-muted uppercase tracking-wider">
                            <th className="pb-3 pr-4">Manuscript</th>
                            <th className="pb-3 px-4">Submitted</th>
                            <th className="pb-3 px-4">Recommendation</th>
                            <th className="pb-3 px-4">Confidence</th>
                            <th className="pb-3 pl-4 text-right">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-transparent text-sm">
                          {recentEvals.length === 0 ? (
                            <tr>
                              <td colSpan={5} className="py-8 text-center text-xs editor-themed-muted">
                                no evaluations yet
                              </td>
                            </tr>
                          ) : (
                            recentEvals.slice(0, 6).map((row) => {
                              const rec = row.recommendation || 'Requires Attention';
                              const confNum = row.confidence !== null && row.confidence !== undefined
                                ? row.confidence
                                : row.desk_reject_probability !== null && row.desk_reject_probability !== undefined
                                ? (rec === 'Accept for Review' ? 1 - row.desk_reject_probability : row.desk_reject_probability)
                                : 0.75;

                              const badgeStyle =
                                rec === 'Accept for Review'
                                  ? isDark
                                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60'
                                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : rec === 'Reject'
                                  ? isDark
                                    ? 'bg-rose-950/60 text-rose-300 border border-rose-800/60'
                                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                                  : isDark
                                  ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                                  : 'bg-amber-50 text-amber-700 border border-amber-200';

                              const barColor =
                                rec === 'Accept for Review'
                                  ? 'bg-emerald-500'
                                  : rec === 'Reject'
                                  ? 'bg-rose-500'
                                  : 'bg-amber-500';

                              return (
                                <tr
                                  key={row.id}
                                  onClick={() => router.push(`/editor/evaluation/${row.id}`)}
                                  className="editor-themed-row cursor-pointer group"
                                >
                                  <td className="py-3.5 pr-4 max-w-xs">
                                    <div className="flex items-start gap-3">
                                      <div 
                                        className="p-1.5 rounded border mt-0.5 flex-shrink-0"
                                        style={{ 
                                          backgroundColor: isDark ? 'rgba(239, 68, 68, 0.15)' : 'rgba(220, 38, 38, 0.08)',
                                          borderColor: isDark ? 'rgba(239, 68, 68, 0.3)' : 'rgba(220, 38, 38, 0.2)' 
                                        }}
                                      >
                                        <FileText className="w-4 h-4" style={{ color: isDark ? '#f87171' : '#dc2626' }} />
                                      </div>
                                      <div className="min-w-0">
                                        <p className="font-medium editor-themed-text truncate group-hover:text-blue-500 transition-colors">
                                          {row.title || row.filename}
                                        </p>
                                        <span className="text-xs font-mono editor-themed-muted">
                                          MS-2026-0{row.id}
                                        </span>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-3.5 px-4 text-xs editor-themed-muted whitespace-pre-line">
                                    {formatDate(row.upload_date)}
                                  </td>
                                  <td className="py-3.5 px-4 whitespace-nowrap">
                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${badgeStyle}`}>
                                      {rec}
                                    </span>
                                  </td>
                                  <td className="py-3.5 px-4 whitespace-nowrap">
                                    <div className="flex items-center gap-2.5">
                                      <span className="font-mono text-xs font-semibold editor-themed-text w-8">
                                        {confNum.toFixed(2)}
                                      </span>
                                      <div className="w-14 bg-gray-300 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                                        <div
                                          className={`h-1.5 rounded-full ${barColor}`}
                                          style={{ width: `${Math.min(100, Math.round(confNum * 100))}%` }}
                                        />
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-3.5 pl-4 whitespace-nowrap text-right">
                                    <div className="flex items-center justify-end gap-1 text-xs font-semibold text-emerald-500">
                                      <span>Completed</span>
                                      <ChevronRight className="w-4 h-4 editor-themed-muted group-hover:text-blue-500 transition-colors" />
                                    </div>
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="pt-4 border-t editor-themed-border mt-4 flex justify-center">
                    <a
                      href="/editor/dashboard"
                      className="text-xs font-bold text-blue-500 hover:text-blue-600 transition-colors flex items-center gap-1"
                    >
                      <span>View all evaluations</span>
                      <span>→</span>
                    </a>
                  </div>
                </div>

                {/* Right Column (col-span-1): Vertical split of 2 cards */}
                <div className="lg:col-span-1 flex flex-col gap-6">
                  {/* Top Card: Recent Activity — real events from audit_logs */}
                  <div className="editor-themed-card border rounded-xl p-6 shadow-sm flex flex-col justify-between">
                    <h3 className="text-base font-bold editor-themed-text mb-4">
                      Recent Activity
                    </h3>
                    <div className="flex flex-col gap-4">
                      {recentActivities.length === 0 ? (
                        <p className="text-xs editor-themed-muted text-center py-4 font-medium">
                          no activity yet
                        </p>
                      ) : (
                        recentActivities.map((act) => {
                          const display = ACTIVITY_DISPLAY[act.action] || { label: act.action, type: 'eval' };
                          const actStyles = getActivityStyles(display.type, isDark);
                          const iconMap: Record<string, React.ReactNode> = {
                            upload: <Upload className="w-4 h-4" />,
                            eval:   <FileCheck className="w-4 h-4" />,
                            reject: <XCircle className="w-4 h-4" />,
                            export: <Download className="w-4 h-4" />,
                          };
                          return (
                            <div key={act.id} className="flex items-start gap-3">
                              <div
                                className="p-2 rounded-lg border flex-shrink-0 mt-0.5 flex items-center justify-center"
                                style={{
                                  backgroundColor: actStyles.bg,
                                  borderColor: actStyles.border,
                                  color: actStyles.text
                                }}
                              >
                                {iconMap[display.type] || <FileCheck className="w-4 h-4" />}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="text-xs font-bold editor-themed-text">{display.label}</p>
                                <p className="text-xs editor-themed-muted truncate mt-0.5">
                                  {act.manuscript_title}
                                </p>
                              </div>
                              <span className="text-[11px] editor-themed-muted whitespace-nowrap">
                                {formatRelativeTime(act.created_at)}
                              </span>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>

                  {/* Bottom Card: Quick Actions */}
                  <div className="editor-themed-card border rounded-xl p-6 shadow-sm">
                    <h3 className="text-base font-bold editor-themed-text mb-4">
                      Quick Actions
                    </h3>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        onClick={triggerUpload}
                        className="editor-themed-action-btn font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 text-xs cursor-pointer"
                      >
                        <Upload className="w-3.5 h-3.5 text-blue-500" />
                        <span>Upload Manuscript</span>
                      </button>
                      <a
                        href="/editor/dashboard"
                        className="editor-themed-action-btn font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 text-xs cursor-pointer text-center"
                      >
                        <FileText className="w-3.5 h-3.5 text-emerald-500" />
                        <span>View Manuscripts</span>
                      </a>
                      <a
                        href="/editor/analytics"
                        className="editor-themed-action-btn font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 text-xs cursor-pointer text-center"
                      >
                        <TrendingUp className="w-3.5 h-3.5 text-purple-500" />
                        <span>Editorial Analytics</span>
                      </a>
                      <button
                        onClick={() => window.print()}
                        className="editor-themed-action-btn font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 text-xs cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5 text-amber-500" />
                        <span>Export Report</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ── PROCESSING MODAL ─────────────────────────────────────────── */}
        <Modal
          open={modalOpen}
          onClose={() => !uploadMutation.isPending && setModalOpen(false)}
          closeAfterTransition
          slots={{ backdrop: Backdrop }}
          slotProps={{
            backdrop: {
              timeout: 500,
              sx: { backgroundColor: isDark ? 'rgba(15, 23, 42, 0.85)' : 'rgba(15, 23, 42, 0.4)' }
            },
          }}
        >
          <Fade in={modalOpen}>
            <Box sx={{
              position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
              width: 580, maxWidth: '92vw', bgcolor: colors.panel, color: colors.text,
              borderRadius: 4, p: 4, boxShadow: isDark ? '0 25px 50px -12px rgba(0,0,0,0.7)' : '0 10px 25px -5px rgba(0,0,0,0.1)', 
              border: `1px solid ${colors.border}`,
              outline: 'none'
            }}>
              <Typography variant="h5" sx={{ fontWeight: 800, color: colors.primary, mb: 1 }}>
                Automated Four-Layer Evaluation
              </Typography>
              <Typography variant="body2" sx={{ color: colors.muted, mb: 3 }}>
                Running sequential PDF parsing, editorial rule checks, Qwen semantic evaluation, and SHAP explanation generation.
              </Typography>

              {uploadMutation.isError && (
                <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
                  Upload Failed: {toast.message}
                </Alert>
              )}

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, bgcolor: isDark ? colors.bg : 'rgba(0,0,0,0.02)', p: 3, borderRadius: 3, border: `1px solid ${colors.border}` }}>
                {stagesList.map((st, idx) => {
                  const prog = statusData?.stage_progress?.[st.key] || (uploadMutation.isPending && idx === 0 ? 'active' : 'pending');
                  const isComplete = prog === 'completed' || isPipelineComplete;
                  const isActive = prog === 'active' || (uploadMutation.isPending && idx === 0);
                  return (
                    <Box key={st.key} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      {isComplete ? (
                        <CheckCircleOutlinedIcon sx={{ color: colors.success, fontSize: 22 }} />
                      ) : isActive ? (
                        <CircularProgress size={18} sx={{ color: colors.primary }} />
                      ) : (
                        <Box sx={{ width: 18, height: 18, borderRadius: '50%', border: `2px solid ${colors.border}` }} />
                      )}
                      <Typography variant="body2" sx={{
                        fontWeight: isActive || isComplete ? 700 : 500,
                        color: isComplete ? colors.text : isActive ? colors.primary : colors.muted
                      }}>
                        {st.label}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
                {!uploadMutation.isPending && (
                  <Button variant="outlined" onClick={() => setModalOpen(false)} sx={{ color: colors.text, borderColor: colors.border, borderRadius: 2, textTransform: 'none', fontWeight: 600 }}>
                    Close Window
                  </Button>
                )}
                {activeId && isPipelineComplete && (
                  <Button variant="contained" onClick={() => router.push(`/editor/evaluation/${activeId}`)} sx={{ bgcolor: colors.success, '&:hover': { bgcolor: isDark ? '#15803d' : '#166534' }, borderRadius: 2, fontWeight: 700, textTransform: 'none' }}>
                    View Analysis Dashboard →
                  </Button>
                )}
              </Box>
            </Box>
          </Fade>
        </Modal>

        <Snackbar open={toast.open} autoHideDuration={5000} onClose={handleCloseToast} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
          <Alert onClose={handleCloseToast} severity={toast.severity} sx={{ width: '100%', borderRadius: 2, fontWeight: 600 }}>
            {toast.message}
          </Alert>
        </Snackbar>
      </DashboardLayout>
    </div>
  );
}