"""
feature_aliases.py — Centralized Feature Alias Resolution
Maps upstream Layer 1 and Layer 2 output key variations to canonical Layer 3 feature names.
"""

from typing import Dict, Any, Optional

ALIAS_MAP: Dict[str, str] = {
    # Layer 1 aliases
    "is_conference": "conference",
    "conf_flag": "conference",
    "critical_failures": "critical_rules_failed",
    "l1_critical_violations": "critical_rules_failed",
    "l1_medium_critical_violations": "critical_rules_failed",
    "total_failures": "total_rules_failed",
    "l1_total_violations": "total_rules_failed",
    "violations_count": "total_rules_failed",

    # Layer 2 aliases
    "credibility_score": "overall_quality",
    "overall_score": "overall_quality",
    "arg_quality": "argumentative_quality",
    "argument_quality": "argumentative_quality",
    "exp_strength": "experimental_strength",
    "experiments_strength": "experimental_strength",
    "method_strength": "methodological_strength",
    "methodology_strength": "methodological_strength",
    "scope_score": "scope_alignment",
    "structural_score": "structural_completeness",
    "completeness_score": "structural_completeness"
}


def resolve_feature_alias(key: str) -> str:
    """Returns the canonical feature name if the given key is a known alias, otherwise returns the key unchanged."""
    clean_key = str(key).strip()
    return ALIAS_MAP.get(clean_key, clean_key)


def apply_aliases_to_mapping(raw_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves all keys in a dictionary to canonical feature names without overwriting existing exact keys."""
    resolved = {}
    for k, v in raw_mapping.items():
        can_key = resolve_feature_alias(k)
        # If canonical key not already populated or if k is exact match, store v
        if can_key not in resolved or k == can_key:
            resolved[can_key] = v
    return resolved
