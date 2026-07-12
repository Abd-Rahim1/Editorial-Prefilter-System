// ============================================================
// Extended TypeScript Interfaces — Editorial Dashboard v2
// ============================================================

// ── Verdict / Status types ───────────────────────────────────
export type ManuscriptStatus   = 'pending' | 'processing' | 'in_review' | 'accepted' | 'rejected' | 'escalated' | 'passed' | 'review';

export type Recommendation     = 'ACCEPT' | 'REVIEW' | 'ESCALATE' | 'REJECT';
export type RuleStatus         = 'pass'   | 'warning' | 'fail';
export type ExplainabilityType = 'success' | 'warning' | 'error' | 'info';
export type PipelineStepStatus = 'done'    | 'running'  | 'pending' | 'error';
export type AuditAction        =
  | 'PDF_UPLOADED' | 'PIPELINE_COMPLETED' | 'SEMANTIC_ANALYSIS'
  | 'DECISION_OVERRIDDEN' | 'THRESHOLD_UPDATED' | 'ESCALATION_CREATED'
  | 'MODEL_DEPLOYED' | 'RULE_VALIDATION';

// ── Core props ───────────────────────────────────────────────

/** Props for the native SVG Radar Chart component */
export interface RadarChartProps {
  scores: Record<string, number>;
}

/** Props for the Drag-and-Drop file upload zone */
export interface DropzoneProps {
  onFileSelected: (file: File) => void;
  loading: boolean;
}

// ── Domain models ────────────────────────────────────────────

/** Manuscript metadata extracted and returned by the backend pipeline */
export interface ManuscriptMetadata {
  title:           string;
  authors:         string;
  institution:     string;
  orcid:           string;
  keywords:        string[];
  num_pages:       number;
  total_word_count:number;
}

/** Semantic evaluation scores produced by the Qwen reasoning layer */
export interface QwenScores {
  abstract_clarity:        number;
  structural_completeness: number;
  methodological_strength: number;
  experimental_strength:   number;
  argumentative_quality:   number;
  scope_alignment:         number;
  overall_quality?:        number;
  detected_issues?:        string[];
  [key: string]:           any;
}

/** Numeric-only keys of QwenScores (excludes optional array fields) */
export type QwenScoreKey = 
  | 'abstract_clarity'
  | 'structural_completeness'
  | 'methodological_strength'
  | 'experimental_strength'
  | 'argumentative_quality'
  | 'scope_alignment';

/** Full JSON response envelope from /api/predict */
export interface PipelineResult {
  success:                        boolean;
  error?:                         string;
  manuscript_id?:                 number | string;
  fallback_used?:                 boolean;
  hard_rules_reject?:             boolean;
  layer1_violations?:             string[];
  missing_sections?:              string[];
  sections_present?:              number;
  violations_count?:              number;
  calibrated_rejection_probability?: number;
  metadata?:                      ManuscriptMetadata;
  qwen_scores?:                   QwenScores;
  layer2_scores?:                 QwenScores;
  recommendation?:                string;
  reason?:                        string;
}

/** A single structural validation rule with its evaluation outcome */
export interface StructuralRule {
  id:     string;
  label:  string;
  status: RuleStatus;
  detail: string;
}

/** One entry in the explainability / evidence log */
export interface ExplainabilityEntry {
  id:         string;
  section:    string;
  issue:      string;
  reasoning:  string;
  confidence: number;
  type:       ExplainabilityType;
  evidence:   string;
}

/** A single step in the processing pipeline timeline */
export interface PipelineStep {
  id:       string;
  label:    string;
  status:   PipelineStepStatus;
  duration: string;
}

/** A recent manuscript shown in the sidebar */
export interface RecentManuscript {
  id:         string;
  title:      string;
  conference: string;
  riskScore:  number;
  status:     ManuscriptStatus;
}

/** Explicit alias so external components looking for RecentPaper do not fail type-checks */
export type RecentPaper = RecentManuscript;

/** One row in the editorial queue table */
export interface QueueEntry {
  id:             string;
  title:          string;
  conference:     string;
  riskScore:      number;
  recommendation: Recommendation;
  status:         ManuscriptStatus;
  lastUpdated:    string;
  submittedBy:    string;
}

/** One row in the audit log table */
export interface AuditLogEntry {
  id:           string;
  timestamp:    string;
  action:       AuditAction;
  manuscriptId: string;
  user:         string;
  details:      string;
  modelVersion: string;
}

/** Union of valid model variant identifiers */
export type ModelVariantId = 'baseline' | 'qwen-zero' | 'qwen-prompt' | 'lora-fine';

/** A selectable AI model variant */
export interface ModelVariant {
  id:   ModelVariantId;
  name: string;
  desc: string;
}

// ============================================================
// Layer 4 Report — canonical JSON envelope
// Matches storage/reports/report_*.json exactly
// ============================================================

/** Layer 3 prediction outcome */
export interface Prediction {
  manuscript_id:          string;
  predicted_class:        number;           // 0 = accept, 1 = reject
  verdict:                string;           // "DESK_REJECT" | "ACCEPT"
  desk_reject_probability: number;          // 0.0 – 1.0
  layer3_verdict:         string;
  layer3_probability:     number;
  [key: string]:          any;
}

/** One SHAP-ranked feature from Layer 4 */
export interface RankedFeature {
  name:             string;
  shap_value:       number;
  absolute_impact:  number;
  direction:        'INCREASED_REJECT_RISK' | 'DECREASED_REJECT_RISK';
  rank:             number;
}

/** Full feature importance block */
export interface FeatureImportance {
  shap_values:          Record<string, number>;
  ranked_features:      RankedFeature[];
  integrated_evidence?: unknown[];
  shap_metadata?:       Record<string, unknown>;
  [key: string]:        any;
}

/** Layer 1 rule violations */
export interface EditorialRules {
  violations:         string[];
  total_violations:   number;
  critical_violations: number;
  layer1_violations?: string[];
  [key: string]:      any;
}

/** Flat semantic score dict (all keys from Qwen Layer 2) */
export interface SemanticScoreDict {
  abstract_clarity:        number;
  structural_completeness: number;
  methodological_strength: number;
  experimental_strength:   number;
  argumentative_quality:   number;
  scope_alignment:         number;
  overall_quality?:        number;
  [key: string]:           any; // forward-compat
}

/** Semantic scores block */
export interface SemanticScores {
  scores:           SemanticScoreDict;
  detected_issues?: string[];
  evidence_spans?:  { section: string; reason: string }[];
  [key: string]:    any;
}

export interface ExplanationObject {
  text?:               string;
  layer4_explanation?: string;
  [key: string]:       string | undefined;
}

/** Canonical Layer 4 JSON report — single source of truth for the dashboard */
export interface ReportData {
  prediction:                   Prediction;
  feature_importance:           FeatureImportance;
  editorial_rules:              EditorialRules;
  semantic_scores:              SemanticScores;
  natural_language_explanation: string | ExplanationObject;
  layer4_explanation?:          string | ExplanationObject;
  [key: string]:                any;
}

