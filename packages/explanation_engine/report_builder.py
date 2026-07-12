"""
Report Builder Module — Layer 4 Explainable AI Engine.

Responsible for assembling, structuring, and persisting the master JSON
explanation report. The output schema has five required top-level keys:
    {
        "prediction":                   { … },
        "feature_importance":           { … },
        "editorial_rules":              { … },
        "semantic_scores":              { … },
        "natural_language_explanation": { … }
    }
All upstream Layer 3 prediction outputs are strictly preserved without recalculating verdicts.
"""

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Dict, List, Union, Optional

from .feature_ranker import RankedFeature
from .evidence_integrator import IntegratedEvidence
from .schemas import AttributionResult

logger = logging.getLogger(__name__)


class ReportBuilder:
    """
    Constructs and persists the comprehensive Layer 4 Explainable AI report.
    Single responsibility: JSON schema packaging and file I/O only.
    """

    @staticmethod
    def build_report(
        manuscript_id: str,
        prediction: Union[int, str, Any],
        accept_probability: float,
        desk_reject_probability: float,
        shap_values: Dict[str, float],
        ranked_features: List[RankedFeature],
        integrated_evidence: List[IntegratedEvidence],
        layer1_violations: List[Any],
        semantic_scores: Dict[str, Any],
        natural_language_explanation: str,
        thresholds_profile: Dict[str, Any] = None,
        attribution_result: Optional[AttributionResult] = None,
    ) -> Dict[str, Any]:
        """
        Assemble the master explanation dictionary preserving exact Layer 3 outputs.
        """
        now_ts = datetime.now(timezone.utc).isoformat()

        verdict_str = "MANUAL_REVIEW"
        predicted_class = 1
        accept_prob = accept_probability
        reject_prob = desk_reject_probability
        conf_level = "MODERATE"
        cal_method = "none"

        if hasattr(prediction, "decision"):
            verdict_str = str(getattr(prediction, "decision"))
            if hasattr(prediction, "accept_probability"):
                accept_prob = float(getattr(prediction, "accept_probability"))
            if hasattr(prediction, "desk_reject_probability"):
                reject_prob = float(getattr(prediction, "desk_reject_probability"))
            if hasattr(prediction, "confidence_level"):
                conf_level = str(getattr(prediction, "confidence_level"))
            if hasattr(prediction, "calibration_method"):
                cal_method = getattr(prediction, "calibration_method") or "none"
            predicted_class = 1 if ("REJECT" in verdict_str.upper()) else 0
        elif isinstance(prediction, dict):
            verdict_str = prediction.get("decision", "MANUAL_REVIEW")
            accept_prob = float(prediction.get("accept_probability", accept_probability))
            reject_prob = float(prediction.get("desk_reject_probability", desk_reject_probability))
            conf_level = prediction.get("confidence_level", "MODERATE")
            cal_method = prediction.get("calibration_method", "none") or "none"
            predicted_class = 1 if ("REJECT" in verdict_str.upper()) else 0
        elif isinstance(prediction, str):
            verdict_str = prediction
            predicted_class = 1 if ("REJECT" in verdict_str.upper()) else 0
        elif isinstance(prediction, int):
            predicted_class = prediction
            verdict_str = "DESK_REJECT" if prediction == 1 else "PEER_REVIEW"

        # Invariants Check
        assert 0.0 <= accept_prob <= 1.0, f"accept_probability {accept_prob} out of bounds"
        assert 0.0 <= reject_prob <= 1.0, f"desk_reject_probability {reject_prob} out of bounds"
        assert abs(accept_prob + reject_prob - 1.0) < 1e-6, f"Probabilities sum {accept_prob + reject_prob} != 1.0"

        rules_list: List[str] = []
        critical_count = 0
        violations_input = layer1_violations
        if isinstance(layer1_violations, dict):
            if "violations" in layer1_violations:
                violations_input = layer1_violations["violations"]
            elif "rule_violations" in layer1_violations:
                violations_input = layer1_violations["rule_violations"]

        for v in (violations_input or []):
            severity = getattr(v, "severity", "")
            if isinstance(v, dict):
                severity = v.get("severity", "")
            if str(severity).lower() == "critical":
                critical_count += 1
            if hasattr(v, "rule_name"):
                rules_list.append(
                    f"[{str(severity).upper()}] {v.rule_name}: "
                    f"{getattr(v, 'description', getattr(v, 'details', ''))}"
                )
            elif isinstance(v, dict) and "rule_name" in v:
                rules_list.append(
                    f"[{str(severity).upper()}] {v['rule_name']}: "
                    f"{v.get('description', v.get('details', ''))}"
                )
            else:
                rules_list.append(str(v))

        semantic_evidence_list: List[str] = []
        evidence_spans_structured: List[Any] = []

        if isinstance(semantic_scores, dict):
            for item in semantic_scores.get("detected_issues", []):
                semantic_evidence_list.append(str(item))

            raw_spans = semantic_scores.get("evidence_spans", [])
            if isinstance(raw_spans, list):
                evidence_spans_structured = raw_spans
                for span in raw_spans:
                    if isinstance(span, dict):
                        label = span.get("section", "")
                        reason = span.get("reason", "")
                        text = f"[{label}] {reason}" if label else reason
                        if text.strip():
                            semantic_evidence_list.append(text)
                    else:
                        semantic_evidence_list.append(str(span))

        n_nonzero = sum(1 for v in shap_values.values() if abs(v) > 1e-8)
        attr_method = attribution_result.attribution_method if attribution_result else "tree_shap"
        expl_out = attribution_result.explained_output if attribution_result else "accept_probability"
        bg_strat = attribution_result.background_strategy if attribution_result else "tree_path_dependent"

        shap_metadata: Dict[str, Any] = {
            "method":           attr_method,
            "explained_output": expl_out,
            "n_features":       len(shap_values),
            "n_nonzero":        n_nonzero,
            "baseline":         bg_strat,
        }
        if attribution_result:
            shap_metadata["class_label"] = attribution_result.class_label
            shap_metadata["class_index"] = attribution_result.class_index
            shap_metadata["base_value"] = attribution_result.base_value
            shap_metadata["model_output"] = attribution_result.model_output
            shap_metadata["attribution_sum"] = attribution_result.attribution_sum
            shap_metadata["reconstructed_output"] = attribution_result.reconstructed_output
            shap_metadata["additivity_error"] = attribution_result.additivity_error
            shap_metadata["additivity_status"] = attribution_result.additivity_status

        report: Dict[str, Any] = {
            "prediction": {
                "manuscript_id":           str(manuscript_id),
                "predicted_class":         predicted_class,
                "verdict":                 verdict_str,
                "decision":                verdict_str,
                "accept_probability":      round(float(accept_prob), 4),
                "desk_reject_probability": round(float(reject_prob), 4),
                "confidence_level":        conf_level,
                "calibration_method":      cal_method,
                "thresholds_applied":      thresholds_profile or {},
                "timestamp":               now_ts,
                # Backward-compat
                "layer3_verdict":          verdict_str,
                "layer3_probability":      round(float(reject_prob), 4),
            },

            "feature_importance": {
                "shap_values":        shap_values,
                "ranked_features":    [rf.to_dict() if hasattr(rf, "to_dict") else rf for rf in ranked_features],
                "integrated_evidence":[ie.to_dict() if hasattr(ie, "to_dict") else ie for ie in integrated_evidence],
                "shap_metadata":      shap_metadata,
            },

            "editorial_rules": {
                "violations":         rules_list,
                "total_violations":   len(rules_list),
                "critical_violations":critical_count,
                # Backward-compat
                "layer1_violations":  rules_list,
            },

            "semantic_scores": {
                "scores":          semantic_scores,
                "evidence":        semantic_evidence_list,
                "evidence_spans":  evidence_spans_structured,
                "mode":            (
                    semantic_scores.get("mode", "unknown")
                    if isinstance(semantic_scores, dict) else "unknown"
                ),
                "prompt_version":  (
                    semantic_scores.get("_meta", {}).get("prompt_version", "unknown")
                    if isinstance(semantic_scores, dict) else "unknown"
                ),
                # Backward-compat
                "layer2_qwen_scores": semantic_scores,
            },

            "natural_language_explanation": {
                "text":             natural_language_explanation,
                "generated_at":     now_ts,
                # Backward-compat
                "layer4_explanation": natural_language_explanation,
            },
        }

        logger.info(
            "Built report for '%s': verdict=%s, prob=%.4f, SHAP non-zero=%d/%d.",
            manuscript_id,
            verdict_str,
            reject_prob,
            n_nonzero,
            len(shap_values),
        )
        return report

    @staticmethod
    def save_report(report: Dict[str, Any], output_dir: str = "storage/reports/") -> str:
        """Persist the report to disk as formatted JSON."""
        os.makedirs(output_dir, exist_ok=True)

        manuscript_id: str = (
            report.get("prediction", {}).get("manuscript_id", "default")
            if isinstance(report.get("prediction"), dict)
            else str(report.get("manuscript_id", "default"))
        )

        file_path = os.path.join(output_dir, f"report_{manuscript_id}.json")

        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=4, ensure_ascii=False)

        logger.info("Saved report to: %s", file_path)
        return file_path
