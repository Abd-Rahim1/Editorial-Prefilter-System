"""
evidence_mapping.py — Explicit Domain Mappings for Layer 4
Defines the mapping table for the 10 canonical C2 features, linking quantitative attributions
to exact upstream Layer 1 checks and Layer 2 semantic evaluation scores.
Separates semantic evaluation thresholds (`ExplanationPolicy`) from Layer 3 decision thresholds.
"""

from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class ExplanationPolicy:
    """Thresholds for semantic quality interpretation in Layer 4 (distinct from Layer 3 classification thresholds)."""
    low_score_threshold: float = 0.55
    high_score_threshold: float = 0.70


C2_FEATURE_EVIDENCE_MAP: Dict[str, Dict[str, Any]] = {
    "argumentative_quality": {
        "display_name": "Argumentative & Rhetorical Quality",
        "domain": "Semantic Quality",
        "layer2_keys": ["argumentative_quality", "argumentative_quality_score", "arg_quality"],
        "layer1_rules": [],
        "description": "Evaluation of the clarity, logical flow, and persuasive structure of the claims."
    },
    "conference": {
        "display_name": "Target Conference Venue Alignment",
        "domain": "Metadata",
        "layer2_keys": [],
        "layer1_rules": [],
        "description": "Categorical encoding of the intended academic venue (e.g. ICLR, ACL, CoNLL)."
    },
    "critical_rules_failed": {
        "display_name": "Critical Editorial Rule Violations",
        "domain": "Structural Compliance",
        "layer2_keys": [],
        "layer1_rules": ["min_abstract_words", "max_abstract_words", "missing_critical_sections"],
        "description": "Count of high-severity formatting or structural deficiencies detected by Layer 1."
    },
    "experimental_strength": {
        "display_name": "Experimental Rigor & Evaluation Setup",
        "domain": "Semantic Quality",
        "layer2_keys": ["experimental_strength", "experimental_strength_score", "exp_strength"],
        "layer1_rules": [],
        "description": "Assessment of empirical validation, baseline comparisons, and statistical strength."
    },
    "methodological_strength": {
        "display_name": "Methodological Soundness & Rigor",
        "domain": "Semantic Quality",
        "layer2_keys": ["methodological_strength", "methodological_strength_score", "method_strength"],
        "layer1_rules": [],
        "description": "Evaluation of mathematical or theoretical soundness, architectural detail, and reproducibility."
    },
    "overall_quality": {
        "display_name": "Overall Scientific Credibility & Quality",
        "domain": "Semantic Quality",
        "layer2_keys": ["overall_quality", "integrity_risk_score", "credibility_score", "overall_score"],
        "layer1_rules": [],
        "description": "Holistic LLM evaluation score representing scientific value and integrity."
    },
    "risk_multiplier": {
        "display_name": "Compound Integrity Risk Multiplier",
        "domain": "Risk Synthesis",
        "layer2_keys": ["overall_quality"],
        "layer1_rules": ["*"],
        "description": "Exact compound risk indicator formulated during training: (1.0 - overall_quality) * total_rules_failed."
    },
    "scope_alignment": {
        "display_name": "Venue Scope & Topic Alignment",
        "domain": "Semantic Quality",
        "layer2_keys": ["scope_alignment", "scope_alignment_score", "scope_score"],
        "layer1_rules": [],
        "description": "Assessment of how well the topic fits the target conference tracks and audience."
    },
    "structural_completeness": {
        "display_name": "Structural Completeness & Clarity",
        "domain": "Semantic Quality",
        "layer2_keys": ["structural_completeness", "structure_validity_score", "completeness_score"],
        "layer1_rules": ["missing_critical_sections"],
        "description": "Assessment of required section presence (Abstract, Intro, Method, Experiments, Conclusion)."
    },
    "total_rules_failed": {
        "display_name": "Total Editorial Rule Violations",
        "domain": "Structural Compliance",
        "layer2_keys": [],
        "layer1_rules": ["*"],
        "description": "Total count of hard editorial rule violations across all severities."
    }
}
