"""
schemas.py — Layer 4 Explanation Engine DTOs & Contracts
Defines explicit typed request and result structures for controlled explainable AI.
Enforces that Layer 4 explains without re-deciding Layer 3 verdicts.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import time


@dataclass
class ExplanationRequest:
    """Input payload for generating a controlled explanation."""
    manuscript_id: str
    model_run_id: Optional[int] = None
    layer1_result: Any = None
    layer2_result: Any = None
    layer3_prediction: Any = None
    model_input_dataframe: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manuscript_id": self.manuscript_id,
            "model_run_id": self.model_run_id,
            "layer1_result": self.layer1_result if isinstance(self.layer1_result, dict) else (self.layer1_result.to_dict() if hasattr(self.layer1_result, "to_dict") else str(self.layer1_result)),
            "layer2_result": self.layer2_result if isinstance(self.layer2_result, dict) else (self.layer2_result.to_dict() if hasattr(self.layer2_result, "to_dict") else str(self.layer2_result)),
            "layer3_prediction": self.layer3_prediction if isinstance(self.layer3_prediction, dict) else (self.layer3_prediction.dict() if hasattr(self.layer3_prediction, "dict") else str(self.layer3_prediction)),
        }


@dataclass
class AttributionResult:
    """SHAP quantitative feature attribution output."""
    shap_values: Dict[str, float] = field(default_factory=dict)
    ranked_features: List[Any] = field(default_factory=list)
    attribution_method: str = "tree_shap"
    explained_output: str = "accept_probability"
    class_label: int = 1
    class_index: int = 1
    base_value: float = 0.0
    model_output: float = 0.0
    attribution_sum: float = 0.0
    reconstructed_output: float = 0.0
    additivity_error: float = 0.0
    additivity_status: str = "PASS"
    background_strategy: str = "tree_path_dependent"
    degraded_mode: bool = False
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shap_values": self.shap_values,
            "ranked_features": [
                f.to_dict() if hasattr(f, "to_dict") else (f if isinstance(f, dict) else str(f))
                for f in self.ranked_features
            ],
            "attribution_method": self.attribution_method,
            "explained_output": self.explained_output,
            "class_label": self.class_label,
            "class_index": self.class_index,
            "base_value": self.base_value,
            "model_output": self.model_output,
            "attribution_sum": self.attribution_sum,
            "reconstructed_output": self.reconstructed_output,
            "additivity_error": self.additivity_error,
            "additivity_status": self.additivity_status,
            "background_strategy": self.background_strategy,
            "degraded_mode": self.degraded_mode,
            "warning": self.warning,
        }


@dataclass
class ExplanationResult:
    """Master output DTO encapsulating the 5 required top-level report keys plus audit metadata."""
    manuscript_id: str
    prediction: Dict[str, Any]
    feature_importance: Dict[str, Any]
    editorial_rules: Dict[str, Any]
    semantic_scores: Dict[str, Any]
    natural_language_explanation: Dict[str, Any]
    attribution: Optional[AttributionResult] = None
    model_run_id: Optional[int] = None
    explanation_version: str = "v4.0"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Returns the dictionary format required by backend API, reports table, and frontend dashboard."""
        res = {
            "manuscript_id": self.manuscript_id,
            "prediction": self.prediction,
            "feature_importance": self.feature_importance,
            "editorial_rules": self.editorial_rules,
            "semantic_scores": self.semantic_scores,
            "natural_language_explanation": self.natural_language_explanation,
            "model_run_id": self.model_run_id,
            "explanation_version": self.explanation_version,
            "created_at": self.created_at,
        }
        if self.attribution:
            res["attribution"] = self.attribution.to_dict()
        return res

    def to_master_report_dict(self) -> Dict[str, Any]:
        """Returns strictly the 5 required top-level master report sections (`prediction`, `feature_importance`, `editorial_rules`, `semantic_scores`, `natural_language_explanation`)."""
        return {
            "prediction": self.prediction,
            "feature_importance": self.feature_importance,
            "editorial_rules": self.editorial_rules,
            "semantic_scores": self.semantic_scores,
            "natural_language_explanation": self.natural_language_explanation,
        }
