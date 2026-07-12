export interface RuleCheckResult {
  rule_name: string;
  severity: "high" | "medium" | "low";
  passed: boolean;
  description: string;
}

export interface EvidenceSpan {
  section: string;
  detected_issue: string;
  reason: string;
}

export interface QwenScores {
  abstract_clarity: number;
  structural_completeness: number;
  methodological_strength: number;
  experimental_strength: number;
  argumentative_quality: number;
  scope_alignment: number;
  overall_quality?: number;
  detected_issues: string[];
  evidence_spans: EvidenceSpan[];
  [key: string]: any;
}

export interface PipelineResponse {
  success: boolean;
  filename: string;
  hard_rules_reject: boolean;
  hard_rules_probability: number;
  violations_count: number;
  missing_sections: string[];
  sections_present: number;
  qwen_scores: QwenScores;
  calibrated_rejection_probability: number; // Layer 3 output
}
