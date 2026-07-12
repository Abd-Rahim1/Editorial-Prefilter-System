"""
feature_contract.py — Canonical Feature Schema Definitions
Defines the official feature names, order, datatypes, and default values for Tier C2.
"""

from typing import List, Dict

# The exact 10 features required by the Tier C2 model artifact
CANONICAL_C2_FEATURES: List[str] = [
    "argumentative_quality",
    "conference",
    "critical_rules_failed",
    "experimental_strength",
    "methodological_strength",
    "overall_quality",
    "risk_multiplier",
    "scope_alignment",
    "structural_completeness",
    "total_rules_failed"
]

FEATURE_DATA_TYPES: Dict[str, str] = {
    "argumentative_quality": "float",
    "conference": "float",
    "critical_rules_failed": "float",
    "experimental_strength": "float",
    "methodological_strength": "float",
    "overall_quality": "float",
    "risk_multiplier": "float",
    "scope_alignment": "float",
    "structural_completeness": "float",
    "total_rules_failed": "float"
}

# Documented training behavior values used when sanitizing NaN/Inf
FEATURE_DEFAULT_VALUES: Dict[str, float] = {
    "argumentative_quality": 3.0,
    "conference": 0.0,
    "critical_rules_failed": 0.0,
    "experimental_strength": 3.0,
    "methodological_strength": 3.0,
    "overall_quality": 3.0,
    "risk_multiplier": 0.0,  # Computed as (1.0 - overall_quality) * total_rules_failed
    "scope_alignment": 3.0,
    "structural_completeness": 3.0,
    "total_rules_failed": 0.0
}
