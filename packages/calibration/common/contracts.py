"""
contracts.py — Data Contracts across Online and Offline Stages
Defines protocols and dataclasses shared across package boundaries.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class Layer1OutputContract:
    """Represents expected input keys from Layer 1."""
    critical_rules_failed: int = 0
    total_rules_failed: int = 0
    conference: int = 0
    extra_rule_checks: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "critical_rules_failed": self.critical_rules_failed,
            "total_rules_failed": self.total_rules_failed,
            "conference": self.conference,
        }
        d.update(self.extra_rule_checks)
        return d


@dataclass
class Layer2OutputContract:
    """Represents expected input keys from Layer 2 Qwen LLM evaluations."""
    argumentative_quality: float = 3.0
    experimental_strength: float = 3.0
    methodological_strength: float = 3.0
    overall_quality: float = 3.0
    scope_alignment: float = 3.0
    structural_completeness: float = 3.0
    extra_scores: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "argumentative_quality": self.argumentative_quality,
            "experimental_strength": self.experimental_strength,
            "methodological_strength": self.methodological_strength,
            "overall_quality": self.overall_quality,
            "scope_alignment": self.scope_alignment,
            "structural_completeness": self.structural_completeness,
        }
        d.update(self.extra_scores)
        return d


@dataclass
class FeatureSchemaContract:
    """Represents the feature_schema.json artifact specification."""
    feature_set: str = "C2"
    feature_set_version: str = "1.0"
    ordered_features: List[str] = field(default_factory=list)
    number_of_features: int = 10
    target_column: str = "ground_truth"


@dataclass
class ModelMetadataContract:
    """Represents the metadata.json artifact specification."""
    classifier: str = "Random_Forest"
    feature_set: str = "C2"
    calibration_method: str = "none"
    version: str = "1.0"
    roc_auc: float = 0.6733
    mcc: float = 0.2403
    f1: float = 0.6822
    ece: float = 0.0589
