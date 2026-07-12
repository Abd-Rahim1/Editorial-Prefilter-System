"""
Narrative Generator Module for Layer 4 Explainable AI Engine.

Synthesizes multi-layer evidence into a professional assisted recommendation narrative.
Strictly preserves upstream Layer 3 decisions without recalculating verdicts from thresholds.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from .evidence_integrator import IntegratedEvidence
from .feature_ranker import RankedFeature
from .evidence.evidence_mapping import ExplanationPolicy

logger = logging.getLogger(__name__)


def probability_label(calibration_method: str) -> str:
    """Returns the descriptive name for the probability based on the calibration method."""
    if str(calibration_method).lower() == "none":
        return "Estimated Accept Probability"
    return "Calibrated Accept Probability"


def _humanise_feature(name: str) -> str:
    """Return a readable label for a raw feature column name."""
    return (
        name.replace("rule_", "")
            .replace("_passed", " (rule check)")
            .replace("_failed", " (failures)")
            .replace("_", " ")
            .title()
    )


class EditorialNarrativeGenerator:
    """
    Synthesizes multi-layer evidence into an assisted editorial recommendation narrative.
    Strictly preserves upstream Layer 3 decisions without independent threshold checks.
    """

    @staticmethod
    def generate_narrative(
        decision: str,
        accept_probability: float,
        desk_reject_probability: float,
        confidence_level: str,
        calibration_method: str,
        integrated_evidence: List[IntegratedEvidence],
        layer1_violations: List[Any],
        semantic_scores: Dict[str, Any],
        ranked_features: Optional[List[RankedFeature]] = None,
        thresholds_profile: Dict[str, Any] = None,
    ) -> str:
        """
        Generate a concise, assisted editorial recommendation narrative.
        """
        decision_str = str(decision).upper().replace("_", " ")
        conf_level = str(confidence_level).upper()

        # Build Negative and Positive Contributions paragraphs
        neg_contribs = []
        pos_contribs = []
        if ranked_features:
            for rf in ranked_features:
                if abs(rf.shap_value) < 1e-6:
                    continue
                h_name = rf.name.replace("_", " ")
                if rf.shap_value < 0:
                    neg_contribs.append(f"{h_name} (SHAP {rf.shap_value:+.4f})")
                else:
                    pos_contribs.append(f"{h_name} (SHAP {rf.shap_value:+.4f})")

        neg_p = ""
        if neg_contribs:
            neg_p = f"The strongest negative local model contributions were {', '.join(neg_contribs[:2])}."
            # Specific invariant: explain contribution without claiming the feature value itself is poor
            neg_shap_features = [r for r in ranked_features if r.shap_value < -1e-6]
            if neg_shap_features:
                first_neg_name = neg_shap_features[0].name.replace("_", " ")
                neg_p += f" For this specific prediction, {first_neg_name} contributed negatively to the model's acceptance estimate."

        pos_p = ""
        if pos_contribs:
            pos_p = f"{', '.join(pos_contribs[:2]).capitalize()} contributed positively to the model's acceptance estimate."

        # Build Structural/Semantic evidence paragraph
        ev_parts = []
        violations_count = len(layer1_violations)
        critical_count = sum(
            1 for v in layer1_violations
            if getattr(v, "severity", "") == "critical" or (isinstance(v, dict) and v.get("severity") == "critical")
        )

        if violations_count > 0:
            ev_parts.append(
                f"The structural checks detected {critical_count} critical failure(s) and "
                f"{violations_count - critical_count} additional rule violation(s)."
            )

        # Separate Layer 2 evaluator observations and direct quotes
        l2_obs_formatted = []
        l2_quotes_formatted = []
        for ie in integrated_evidence:
            for item in ie.linked_semantic_evidence:
                if isinstance(item, dict):
                    content = item.get("content", "")
                    s_type = item.get("source_type", "layer2_observation")
                else:
                    content = str(item)
                    s_type = "layer2_observation"

                if s_type == "layer2_observation":
                    clean_c = content.replace('"', '').replace("'", "")
                    l2_obs_formatted.append(f"The Layer 2 semantic evaluator observed that {clean_c}")
                elif s_type == "manuscript_quote":
                    clean_c = content.strip('"').strip("'")
                    l2_quotes_formatted.append(f"\"{clean_c}\"")

        if l2_obs_formatted:
            ev_parts.append("; ".join(l2_obs_formatted[:2]) + ".")
        if l2_quotes_formatted:
            ev_parts.append("Verified manuscript quotes supporting this assessment: " + ", ".join(l2_quotes_formatted[:2]) + ".")

        ev_p = " ".join(ev_parts)

        # Assemble the 6 paragraphs in preferred structure
        paragraphs: List[str] = []

        # 1. Assisted Recommendation
        paragraphs.append(f"ASSISTED RECOMMENDATION: {decision_str}.")

        # 2. Probability Context
        label = probability_label(calibration_method)
        paragraphs.append(
            f"Layer 3 estimated a {label.lower()} of {accept_probability:.2%}, "
            f"placing the manuscript in the {decision_str.lower().replace('_', '-')} region of the active editorial policy."
        )

        # 3. Main Negative Contributions
        if neg_p:
            paragraphs.append(neg_p)

        # 4. Main Positive Contributions
        if pos_p:
            paragraphs.append(pos_p)

        # 5. Structural/Semantic Evidence
        if ev_p:
            paragraphs.append(ev_p)

        # 6. Human Oversight Statement
        paragraphs.append("Final editorial authority remains with the human editor.")

        full_narrative = "\n\n".join(paragraphs)
        logger.info(
            "Generated assisted recommendation narrative (%d paragraphs, %d chars).",
            len(paragraphs),
            len(full_narrative),
        )
        return full_narrative
