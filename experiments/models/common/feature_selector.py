"""
Feature Selector for the Chapter 5 TFG Experimentation Framework.
Implements Ablation Tiers A, B, C, and D with versioning and deterministic
feature ordering for production inference compatibility.
"""

import pandas as pd
import numpy as np
from typing import List, Dict

# Standard feature sets for TFG Chapter 5 Experiments (canonical ordering)
LAYER1_CANDIDATES = [
    "pages", "num_pages", "page_count",
    "words", "word_count", "total_word_count",
    "references", "reference_count",
    "section_count", "missing_sections", "missing_critical_sections",
    "total_rules_failed", "critical_rules_failed",
    "has_abstract", "has_introduction", "has_methodology", "has_experiments", "has_conclusions",
    "methodology_missing_confirmed", "methodology_like_content_found_elsewhere",
    "l1_total_violations", "l1_medium_critical_violations"
]

LAYER2_CANDIDATES = [
    "abstract_clarity", "structural_completeness", "methodological_strength",
    "experimental_strength", "argumentative_quality", "scope_alignment",
    "overall_quality", "suspicious_score", "credibility_score",
    "evidence_strength", "coherence_score", "reproducibility_score",
    "theoretical_rigor_score", "novelty", "significance", "writing_quality",
    "recommendation_score", "research_paper_likelihood", "integrity_risk_score",
    "structure_validity_score", "citation_quality_score", "content_coherence_score"
]

IGNORE_COLS = {
    "ground_truth", "true_label", "label", "accepted", "decision", "status", "target",
    "id", "manuscript_id", "ms_id", "model_run_id", "run_id", "experiment_id",
    "filename", "title", "prompt_version", "error", "success", "raw_output", "parsed_output",
    "qwen_recommendation", "recommendation"
}

# Feature-set metadata dictionary with versioning.
# The runtime feature selection logic is defined in get_available_features().
FEATURE_SETS = {
    "A": {
        "version":     "1.0",
        "name":        "Layer 1 — Structural Rules",
        "description": (
            "Hard structural rule violations and document-level counts extracted "
            "by the rule-based Layer 1 pre-filter (section presence, word count, "
            "page count, reference count, critical rule failures)."
        ),
        "layers":      ["Layer 1"],
        "source":      "Rule engine",
    },
    "B": {
        "version":     "1.0",
        "name":        "Layer 2 — Semantic LLM Scores",
        "description": (
            "Continuous quality scores produced by the Qwen LLM scorer "
            "(abstract clarity, structural completeness, methodological strength, "
            "experimental strength, argumentative quality, scope alignment, "
            "overall quality, credibility, reproducibility, etc.)."
        ),
        "layers":      ["Layer 2"],
        "source":      "LLM scorer",
    },
    "C": {
        "version":     "1.0",
        "name":        "Hybrid — Layer 1 + Layer 2 (Proposed System)",
        "description": (
            "Full hybrid feature set combining Layer 1 structural rule features "
            "with Layer 2 LLM semantic scores. This is the proposed system "
            "configuration for Chapter 5."
        ),
        "layers":      ["Layer 1", "Layer 2"],
        "source":      "Rule engine + LLM scorer",
    },
    "D": {
        "version":     "1.0",
        "name":        "Full — Hybrid + Engineered Features",
        "description": (
            "All numeric features including Layer 1, Layer 2, plus engineered "
            "interaction features (words_per_page, violations_per_page, "
            "risk_multiplier) and any additional document metadata."
        ),
        "layers":      ["Layer 1", "Layer 2", "Engineered"],
        "source":      "Rule engine + LLM scorer + feature engineering",
    },
}

def get_available_features(df: pd.DataFrame, tier: str) -> List[str]:
    """
    Returns the list of column names present in df that belong to the specified ablation tier.
    Enforces a strict, deterministic canonical ordering so training and inference feature vectors
    are guaranteed to align.
    
    Tiers:
      - 'A': Layer 1 structural features only
      - 'B': Layer 2 semantic scores only
      - 'C': Hybrid model (Layer 1 + Layer 2) - Proposed system
      - 'D': Hybrid + Document statistics + Metadata + Engineered features
    """
    tier_upper = tier.upper().strip()
    all_num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in IGNORE_COLS]
    
    # 1. Gather Layer 1 features in deterministic order: canonical candidates first, then sorted rule_ columns
    l1_canon = [c for c in LAYER1_CANDIDATES if c in all_num_cols]
    l1_rules = sorted([c for c in all_num_cols if c.startswith("rule_") and c not in l1_canon])
    l1_present = l1_canon + l1_rules
    
    # 2. Gather Layer 2 features in deterministic canonical order
    l2_present = [c for c in LAYER2_CANDIDATES if c in all_num_cols]
    
    if tier_upper == "A":
        selected = l1_present
    elif tier_upper == "B":
        selected = l2_present
    elif tier_upper == "C":
        # Preserve order: L1 first, then L2
        selected = l1_present + [c for c in l2_present if c not in l1_present]
    elif tier_upper == "D":
        # L1 + L2 + sorted remaining numeric/engineered features
        selected = l1_present + [c for c in l2_present if c not in l1_present]
        other_num = sorted([c for c in all_num_cols if c not in selected])
        selected = selected + other_num
    else:
        raise ValueError(f"Unknown experiment tier '{tier}'. Must be one of: 'A', 'B', 'C', 'D'.")
        
    # Emergency fallback if tier selected 0 columns in a minimal dataset
    if not selected:
        selected = sorted(all_num_cols)
        
    return selected

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds engineered features for Experiment D (e.g. risk multipliers, words per page).
    """
    df = df.copy()
    
    # Words per page
    words_col = next((c for c in ["total_word_count", "word_count", "words"] if c in df.columns), None)
    pages_col = next((c for c in ["num_pages", "page_count", "pages"] if c in df.columns), None)
    
    if words_col and pages_col:
        df["words_per_page"] = df[words_col] / (df[pages_col].replace(0, 1))
        
    # Violations per page
    violations_col = next((c for c in ["total_rules_failed", "l1_total_violations"] if c in df.columns), None)
    if violations_col and pages_col:
        df["violations_per_page"] = df[violations_col] / (df[pages_col].replace(0, 1))
        
    # Risk multiplier
    quality_col = next((c for c in ["overall_quality", "credibility_score"] if c in df.columns), None)
    if quality_col and violations_col:
        df["risk_multiplier"] = (1.0 - df[quality_col]) * (df[violations_col] + 1.0)
        
    return df

def select_features(df: pd.DataFrame, tier: str) -> pd.DataFrame:
    """
    Selects and returns the feature matrix X for the requested experiment tier.
    If tier is 'D', engineered features are generated and added.
    """
    tier_upper = tier.upper().strip()
    if tier_upper == "D":
        df = add_engineered_features(df)
        
    selected_cols = get_available_features(df, tier_upper)
    return df[selected_cols].copy()
