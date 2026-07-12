"""
Orchestrator Module — Layer 4 Explainable AI Engine.

Maintains a clean architecture by delegating every specialised explainability
task to a dedicated single-responsibility submodule:
    ShapExplainer                 → compute_attribution() / compute_shap()
    FeatureRanker                 → rank_features()
    EvidenceIntegrator            → integrate_evidence()
    EditorialNarrativeGenerator   → generate_narrative()
    ReportBuilder                 → build_report() / save_report()
"""

import logging
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from .explainer import ShapExplainer
from .feature_ranker import FeatureRanker
from .evidence_integrator import EvidenceIntegrator
from .narrative import EditorialNarrativeGenerator
from .report_builder import ReportBuilder
from .schemas import ExplanationRequest, ExplanationResult, AttributionResult

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """
    Orchestrates the Layer 4 Explainable AI workflow:
        compute SHAP attributions (TreeSHAP / exact baseline)
            ↓
        rank features by absolute SHAP impact
            ↓
        merge Layer 1 structural rule checks
            ↓
        merge Layer 2 semantic evaluation observations
            ↓
        generate assisted recommendation explanation narrative
            ↓
        build & save JSON report preserving exact Layer 3 decisions
    """

    def __init__(
        self,
        model: Any,
        feature_names: List[str] = None,
        thresholds_profile: Dict[str, Any] = None,
        pipeline_config: Any = None
    ) -> None:
        self.model = model
        self.thresholds_profile = thresholds_profile
        self.pipeline_config = pipeline_config

        if self.thresholds_profile is None and self.pipeline_config is not None:
            if hasattr(self.pipeline_config, "threshold_profile"):
                self.thresholds_profile = self.pipeline_config.threshold_profile
            elif isinstance(self.pipeline_config, dict):
                self.thresholds_profile = self.pipeline_config.get("threshold_profile")
        if self.thresholds_profile is None:
            self.thresholds_profile = {"reject_upper_bound": 0.35, "peer_review_lower_bound": 0.65}

        if feature_names is not None:
            self._feature_names: List[str] = list(feature_names)
        elif hasattr(model, "feature_names_in_"):
            self._feature_names = list(model.feature_names_in_)
        else:
            self._feature_names = []
            logger.warning(
                "ExplanationGenerator: no feature_names provided and model "
                "does not expose feature_names_in_. SHAP will fall back to heuristic."
            )

        self.explainer = ShapExplainer(model, self._feature_names)

    def generate_explanation(
        self,
        request: ExplanationRequest,
        output_dir: Optional[str] = None
    ) -> ExplanationResult:
        """
        Execute explanation pipeline from a typed ExplanationRequest DTO.
        Strictly preserves exact Layer 3 prediction and probability properties.
        """
        l3_pred = request.layer3_prediction
        accept_probability = 0.5
        desk_reject_probability = 0.5
        decision = "manual_review"
        confidence_level = "MODERATE"
        calibration_method = "none"

        # Extract accept_probability
        if hasattr(l3_pred, "accept_probability"):
            accept_probability = float(getattr(l3_pred, "accept_probability"))
        elif isinstance(l3_pred, dict) and "accept_probability" in l3_pred:
            accept_probability = float(l3_pred["accept_probability"])

        # Extract desk_reject_probability
        if hasattr(l3_pred, "desk_reject_probability"):
            desk_reject_probability = float(getattr(l3_pred, "desk_reject_probability"))
        elif isinstance(l3_pred, dict) and "desk_reject_probability" in l3_pred:
            desk_reject_probability = float(l3_pred["desk_reject_probability"])
        else:
            desk_reject_probability = 1.0 - accept_probability

        # Extract decision
        if hasattr(l3_pred, "decision"):
            decision = str(getattr(l3_pred, "decision"))
        elif isinstance(l3_pred, dict) and "decision" in l3_pred:
            decision = str(l3_pred["decision"])

        # Extract confidence
        if hasattr(l3_pred, "confidence_level"):
            confidence_level = str(getattr(l3_pred, "confidence_level"))
        elif isinstance(l3_pred, dict) and "confidence_level" in l3_pred:
            confidence_level = str(l3_pred["confidence_level"])

        # Extract calibration_method
        if hasattr(l3_pred, "calibration_method"):
            calibration_method = getattr(l3_pred, "calibration_method") or "none"
        elif isinstance(l3_pred, dict) and "calibration_method" in l3_pred:
            calibration_method = l3_pred["calibration_method"] or "none"

        # Invariants Check
        assert 0.0 <= accept_probability <= 1.0, f"accept_probability {accept_probability} out of bounds"
        assert 0.0 <= desk_reject_probability <= 1.0, f"desk_reject_probability {desk_reject_probability} out of bounds"
        assert abs(accept_probability + desk_reject_probability - 1.0) < 1e-6, \
            f"Probabilities sum {accept_probability + desk_reject_probability} != 1.0"

        X = request.model_input_dataframe
        if not isinstance(X, pd.DataFrame) and hasattr(l3_pred, "feature_vector") and l3_pred.feature_vector:
            X = pd.DataFrame([l3_pred.feature_vector])
            if self._feature_names:
                X = X.reindex(columns=self._feature_names, fill_value=0.0)

        # Step 1: Compute SHAP attribution
        if isinstance(X, pd.DataFrame):
            attr_result = self.explainer.compute_attribution(X)
        else:
            attr_result = AttributionResult()

        shap_values = attr_result.shap_values

        # Step 2: Rank features
        ranked_features = FeatureRanker.rank_features(shap_values, top_n=5)
        attr_result.ranked_features = ranked_features

        # Step 3 & 4: Integrate evidence
        integrated_evidence = EvidenceIntegrator.integrate_evidence(
            ranked_features=ranked_features,
            layer1_violations=request.layer1_result,
            semantic_evidence=request.layer2_result if isinstance(request.layer2_result, dict) else {},
            prediction=l3_pred,
            accept_probability=accept_probability,
            desk_reject_probability=desk_reject_probability,
            thresholds_profile=self.thresholds_profile,
        )

        # Step 5: Narrative generation
        narrative = EditorialNarrativeGenerator.generate_narrative(
            decision=decision,
            accept_probability=accept_probability,
            desk_reject_probability=desk_reject_probability,
            confidence_level=confidence_level,
            calibration_method=calibration_method,
            integrated_evidence=integrated_evidence,
            layer1_violations=request.layer1_result if isinstance(request.layer1_result, list) else [],
            semantic_scores=request.layer2_result if isinstance(request.layer2_result, dict) else {},
            ranked_features=ranked_features,
            thresholds_profile=self.thresholds_profile,
        )

        # Step 6: Build master report dictionary
        report_dict = ReportBuilder.build_report(
            manuscript_id=request.manuscript_id,
            prediction=l3_pred,
            accept_probability=accept_probability,
            desk_reject_probability=desk_reject_probability,
            shap_values=shap_values,
            ranked_features=ranked_features,
            integrated_evidence=integrated_evidence,
            layer1_violations=request.layer1_result if isinstance(request.layer1_result, list) else [],
            semantic_scores=request.layer2_result if isinstance(request.layer2_result, dict) else {},
            natural_language_explanation=narrative,
            thresholds_profile=self.thresholds_profile,
            attribution_result=attr_result,
        )

        if output_dir:
            ReportBuilder.save_report(report_dict, output_dir=output_dir)

        return ExplanationResult(
            manuscript_id=request.manuscript_id,
            prediction=report_dict["prediction"],
            feature_importance=report_dict["feature_importance"],
            editorial_rules=report_dict["editorial_rules"],
            semantic_scores=report_dict["semantic_scores"],
            natural_language_explanation=report_dict["natural_language_explanation"],
            attribution=attr_result,
            model_run_id=request.model_run_id
        )

    def generate_report(
        self,
        manuscript_id: str,
        inference_features: pd.DataFrame,
        layer1_violations: List[Any],
        qwen_scores: Dict[str, Any],
        predicted_class: Optional[Union[int, str, Any]] = None,
        desk_reject_prob: Optional[float] = None,
        output_dir: str = "storage/reports/",
        thresholds_profile: Dict[str, Any] = None,
        decision: Optional[str] = None,
        accept_probability: Optional[float] = None,
        desk_reject_probability: Optional[float] = None,
        confidence_level: str = "MODERATE",
        calibration_method: str = "none",
    ) -> Dict[str, Any]:
        """
        Execute complete explainability pipeline and return the master report dictionary.
        Backward-compatible method wrapper.
        """
        logger.info("Layer 4: starting explainability pipeline for manuscript '%s'.", manuscript_id)
        active_thresholds = thresholds_profile or self.thresholds_profile

        # Resolve decision, accept_probability, desk_reject_probability from backward compatibility inputs
        resolved_decision = decision
        resolved_accept_prob = accept_probability
        resolved_desk_reject_prob = desk_reject_probability
        resolved_confidence = confidence_level
        resolved_cal_method = calibration_method

        if predicted_class is not None:
            if hasattr(predicted_class, "decision"):
                resolved_decision = getattr(predicted_class, "decision")
            elif isinstance(predicted_class, dict) and "decision" in predicted_class:
                resolved_decision = predicted_class["decision"]
            elif isinstance(predicted_class, (int, bool)):
                resolved_decision = "desk_reject" if predicted_class else "peer_review"
            else:
                resolved_decision = str(predicted_class)

            if hasattr(predicted_class, "accept_probability"):
                resolved_accept_prob = float(getattr(predicted_class, "accept_probability"))
            elif isinstance(predicted_class, dict) and "accept_probability" in predicted_class:
                resolved_accept_prob = float(predicted_class["accept_probability"])

            if hasattr(predicted_class, "desk_reject_probability"):
                resolved_desk_reject_prob = float(getattr(predicted_class, "desk_reject_probability"))
            elif isinstance(predicted_class, dict) and "desk_reject_probability" in predicted_class:
                resolved_desk_reject_prob = float(predicted_class["desk_reject_probability"])

            if hasattr(predicted_class, "confidence_level"):
                resolved_confidence = getattr(predicted_class, "confidence_level")
            elif isinstance(predicted_class, dict) and "confidence_level" in predicted_class:
                resolved_confidence = predicted_class["confidence_level"]

            if hasattr(predicted_class, "calibration_method"):
                resolved_cal_method = getattr(predicted_class, "calibration_method") or "none"
            elif isinstance(predicted_class, dict) and "calibration_method" in predicted_class:
                resolved_cal_method = predicted_class["calibration_method"] or "none"

        if resolved_desk_reject_prob is None:
            if desk_reject_prob is not None:
                resolved_desk_reject_prob = desk_reject_prob
            elif resolved_accept_prob is not None:
                resolved_desk_reject_prob = 1.0 - resolved_accept_prob
            else:
                resolved_desk_reject_prob = 0.5

        if resolved_accept_prob is None:
            resolved_accept_prob = 1.0 - resolved_desk_reject_prob

        if resolved_decision is None:
            resolved_decision = "manual_review"

        # Invariants Check
        assert 0.0 <= resolved_accept_prob <= 1.0, f"accept_probability {resolved_accept_prob} out of bounds"
        assert 0.0 <= resolved_desk_reject_prob <= 1.0, f"desk_reject_probability {resolved_desk_reject_prob} out of bounds"
        assert abs(resolved_accept_prob + resolved_desk_reject_prob - 1.0) < 1e-6, \
            f"Probabilities sum {resolved_accept_prob + resolved_desk_reject_prob} != 1.0"

        attr_result = self.explainer.compute_attribution(inference_features)
        shap_values = attr_result.shap_values
        ranked_features = FeatureRanker.rank_features(shap_values, top_n=5)
        attr_result.ranked_features = ranked_features

        integrated_evidence = EvidenceIntegrator.integrate_evidence(
            ranked_features=ranked_features,
            layer1_violations=layer1_violations,
            semantic_evidence=qwen_scores,
            prediction=predicted_class,
            accept_probability=resolved_accept_prob,
            desk_reject_probability=resolved_desk_reject_prob,
            thresholds_profile=active_thresholds,
        )

        narrative = EditorialNarrativeGenerator.generate_narrative(
            decision=resolved_decision,
            accept_probability=resolved_accept_prob,
            desk_reject_probability=resolved_desk_reject_prob,
            confidence_level=resolved_confidence,
            calibration_method=resolved_cal_method,
            integrated_evidence=integrated_evidence,
            layer1_violations=layer1_violations,
            semantic_scores=qwen_scores,
            ranked_features=ranked_features,
            thresholds_profile=active_thresholds,
        )

        report = ReportBuilder.build_report(
            manuscript_id=manuscript_id,
            prediction=predicted_class,
            accept_probability=resolved_accept_prob,
            desk_reject_probability=resolved_desk_reject_prob,
            shap_values=shap_values,
            ranked_features=ranked_features,
            integrated_evidence=integrated_evidence,
            layer1_violations=layer1_violations,
            semantic_scores=qwen_scores,
            natural_language_explanation=narrative,
            thresholds_profile=active_thresholds,
            attribution_result=attr_result,
        )

        if output_dir:
            ReportBuilder.save_report(report, output_dir=output_dir)

        logger.info(
            "Layer 4: orchestration complete for '%s' (verdict=%s, P(Accept)=%.4f).",
            manuscript_id,
            report["prediction"]["verdict"],
            resolved_accept_prob,
        )
        return report