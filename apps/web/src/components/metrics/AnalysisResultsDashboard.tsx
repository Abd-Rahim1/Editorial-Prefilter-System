import React from 'react';

type EvidenceSpan = {
  section: string;
  reason: string;
};

type AppendixDResult = {
  abstract_clarity: number;
  structural_completeness: number;
  methodological_strength: number;
  experimental_strength: number;
  argumentative_quality: number;
  scope_alignment: number;
  overall_quality: number;
  detected_issues: string[];
  evidence_spans: EvidenceSpan[];
};

type Props = {
  data?: AppendixDResult | null;
};

const metrics = [
  { key: 'abstract_clarity', label: 'Abstract Clarity' },
  { key: 'structural_completeness', label: 'Structural Completeness' },
  { key: 'methodological_strength', label: 'Methodological Strength' },
  { key: 'experimental_strength', label: 'Experimental Strength' },
  { key: 'argumentative_quality', label: 'Argumentative Quality' },
  { key: 'scope_alignment', label: 'Scope Alignment' },
  { key: 'overall_quality', label: 'Overall Quality' },
] as const;

const scoreColor = (value: number) => {
  if (value >= 0.8) return 'bg-emerald-500';
  if (value >= 0.6) return 'bg-amber-500';
  return 'bg-rose-500';
};

const formatPercent = (value: number | undefined) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  return `${Math.round(value * 100)}%`;
};

export default function AnalysisResultsDashboard({ data }: Props) {
  if (!data) {
    return (
      <div className="space-y-8 p-6 sm:p-8">
        <div className="animate-pulse rounded-[2rem] bg-slate-200 p-6" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="animate-pulse rounded-3xl bg-slate-200 p-5" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="animate-pulse rounded-[2rem] bg-slate-200 p-6" />
          <div className="animate-pulse rounded-[2rem] bg-slate-200 p-6" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6 sm:p-8">
      <div className="rounded-[2rem] border border-slate-200 bg-slate-950/5 p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Appendix D Results</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Qwen Semantic Scoring</h1>
          </div>
          <div className="rounded-3xl bg-white px-5 py-4 text-center shadow-sm">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Evidence Spans</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{data.evidence_spans.length}</p>
          </div>
        </div>
        <p className="mt-4 max-w-2xl text-sm text-slate-600">
          High-level quality metrics for the analyzed manuscript. Values are shown as percentages for clarity.
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const value = data[metric.key];
          const percentage = Math.round(value * 100);
          return (
            <div key={metric.key} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-slate-700">{metric.label}</p>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-600">
                  {formatPercent(value)}
                </span>
              </div>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
                <div className={`${scoreColor(value)} h-full rounded-full`} style={{ width: `${percentage}%` }} />
              </div>
              <p className="mt-3 text-xs text-slate-500">
                {percentage >= 80 ? 'Strong' : percentage >= 60 ? 'Average' : 'Weak'}
              </p>
            </div>
          );
        })}
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Detected Issues</h2>
              <p className="mt-1 text-sm text-slate-500">Potential weaknesses found by the model.</p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-600">
              {data.detected_issues.length} item{data.detected_issues.length === 1 ? '' : 's'}
            </span>
          </div>

          <div className="mt-5 space-y-3">
            {data.detected_issues.length === 0 ? (
              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600">
                No issues detected.
              </div>
            ) : (
              data.detected_issues.map((issue, index) => (
                <div key={index} className="rounded-3xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">{issue.replace(/_/g, ' ')}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Evidence Spans</h2>
              <p className="mt-1 text-sm text-slate-500">Sections and reasoning identified by the model.</p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-600">
              {data.evidence_spans.length}
            </span>
          </div>

          <div className="mt-5 space-y-3">
            {data.evidence_spans.length === 0 ? (
              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600">
                No evidence spans available.
              </div>
            ) : (
              <div className="space-y-3">
                {data.evidence_spans.map((span, index) => (
                  <div key={index} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center justify-between gap-3 text-sm text-slate-600">
                      <span className="font-semibold text-slate-900">{span.section}</span>
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs uppercase tracking-[0.24em] text-slate-500">
                        Section
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-700">{span.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
