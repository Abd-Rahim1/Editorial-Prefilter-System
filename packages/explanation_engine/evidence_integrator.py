"""
Evidence Integrator Module for Layer 4 Explainable AI Engine.

Responsible for linking quantitative SHAP attributions with qualitative
Layer 1 structural rule violations and Layer 2 semantic LLM observations.
Uses explicit domain mappings from C2_FEATURE_EVIDENCE_MAP and separates exact provenance.
"""

from dataclasses import dataclass, asdict
import logging
from typing import Dict, List, Any, Union
from .feature_ranker import RankedFeature
from .evidence.evidence_mapping import C2_FEATURE_EVIDENCE_MAP, ExplanationPolicy

logger = logging.getLogger(__name__)


@dataclass
class EvidenceItem:
    """Explicit evidence record with strict provenance."""
    content: str
    source_type: str  # 'layer1_rule', 'layer2_observation', 'manuscript_quote', 'layer3_attribution'
    domain: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntegratedEvidence:
    """Represents a SHAP feature explicitly connected to supporting domain evidence."""
    feature_name: str
    shap_value: float
    impact_direction: str
    linked_rule_violations: List[str]
    linked_semantic_evidence: List[str]
    synthesis_summary: str
    provenance_items: List[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.provenance_items is None:
            res["provenance_items"] = []
        return res


class EvidenceIntegrator:
    """
    Synthesizes quantitative feature attributions with qualitative domain findings.
    Enforces single responsibility by connecting Layer 1/2 outputs to Layer 3 drivers.
    """

    @classmethod
    def integrate_evidence(
        cls,
        ranked_features: List[RankedFeature],
        layer1_violations: Union[List[Any], Dict[str, Any]],
        semantic_evidence: Dict[str, Any],
        prediction: Any,
        accept_probability: float,
        desk_reject_probability: float,
        thresholds_profile: Dict[str, Any] = None,
    ) -> List[IntegratedEvidence]:
        """
        Merge top SHAP features with Layer 1 rule infractions and Layer 2 semantic observations.
        """
        integrated_list = []
        policy = ExplanationPolicy()
        if thresholds_profile and isinstance(thresholds_profile, dict):
            if "low_score_threshold" in thresholds_profile:
                policy.low_score_threshold = float(thresholds_profile["low_score_threshold"])

        # Normalize layer 1 violations to strings and records
        l1_strings = []
        l1_records = []
        violations_list = layer1_violations
        if isinstance(layer1_violations, dict):
            if "violations" in layer1_violations:
                violations_list = layer1_violations["violations"]
            elif "rule_violations" in layer1_violations:
                violations_list = layer1_violations["rule_violations"]
            else:
                violations_list = []

        for v in (violations_list or []):
            if hasattr(v, "rule_name"):
                r_name = getattr(v, "rule_name", "")
                r_det = getattr(v, "details", getattr(v, "description", "Violation detected"))
                l1_strings.append(f"{r_name}: {r_det}")
                l1_records.append((r_name, f"{r_name}: {r_det}"))
            elif isinstance(v, dict) and "rule_name" in v:
                r_name = v["rule_name"]
                r_det = v.get("details", v.get("description", "Violation detected"))
                l1_strings.append(f"{r_name}: {r_det}")
                l1_records.append((r_name, f"{r_name}: {r_det}"))
            else:
                l1_strings.append(str(v))
                l1_records.append(("", str(v)))

        # Normalize layer 2 observations and manuscript quotes
        l2_records = []
        if isinstance(semantic_evidence, dict):
            if isinstance(semantic_evidence.get("detected_issues"), list):
                for i in semantic_evidence["detected_issues"]:
                    l2_records.append((str(i), "layer2_observation"))
            if isinstance(semantic_evidence.get("evidence_spans"), list):
                for s in semantic_evidence["evidence_spans"]:
                    if isinstance(s, dict):
                        section = s.get("section", "")
                        reason = s.get("reason", "")
                        text = f"[{section}] {reason}" if section else reason
                    else:
                        text = str(s)
                    l2_records.append((text, "manuscript_quote"))
            if isinstance(semantic_evidence.get("justifications"), dict):
                for k, just in semantic_evidence["justifications"].items():
                    if just:
                        l2_records.append((f"Observation for {k}: {just}", "layer2_observation"))

            for key, score in semantic_evidence.items():
                if isinstance(score, (int, float)) and any(k in key for k in ["quality", "strength", "alignment", "completeness", "score"]):
                    if score <= policy.low_score_threshold:
                        l2_records.append((f"Low evaluation observation for {key}: {score:.2f}", "layer2_observation"))

        for feat in ranked_features:
            fname = feat.name
            f_meta = C2_FEATURE_EVIDENCE_MAP.get(fname, {})
            domain = f_meta.get("domain", "General Feature")
            target_l1_rules = f_meta.get("layer1_rules", [])
            target_l2_keys = f_meta.get("layer2_keys", [fname])

            matched_l1 = []
            matched_l2 = []
            prov_items = []

            # 1. Match exact Layer 1 rules
            if target_l1_rules == ["*"]:
                matched_l1 = l1_strings[:]
                for r_name, r_str in l1_records:
                    prov_items.append(EvidenceItem(content=r_str, source_type="layer1_rule", domain=domain).to_dict())
            else:
                for r_name, r_str in l1_records:
                    if any(tr in r_name for tr in target_l1_rules if tr):
                        matched_l1.append(r_str)
                        prov_items.append(EvidenceItem(content=r_str, source_type="layer1_rule", domain=domain).to_dict())

            # 2. Match exact Layer 2 observations
            for obs_text, s_type in l2_records:
                if any(tk in obs_text.lower() for tk in target_l2_keys if tk):
                    matched_l2.append({"content": obs_text, "source_type": s_type})
                    prov_items.append(EvidenceItem(content=obs_text, source_type=s_type, domain=domain).to_dict())

            # Fallback for semantic score features if no direct observations found
            if not matched_l2 and domain == "Semantic Quality":
                if fname in semantic_evidence and isinstance(semantic_evidence[fname], (int, float)):
                    sc_val = semantic_evidence[fname]
                    obs_str = f"Evaluated {f_meta.get('display_name', fname)} score: {sc_val:.2f}/1.0"
                    matched_l2.append({"content": obs_str, "source_type": "layer2_observation"})
                    prov_items.append(EvidenceItem(content=obs_str, source_type="layer2_observation", domain=domain).to_dict())

            # Add quantitative attribution provenance
            prov_items.append(
                EvidenceItem(
                    content=f"Feature '{fname}' SHAP impact={feat.shap_value:+.4f} ({feat.direction})",
                    source_type="layer3_attribution",
                    domain=domain
                ).to_dict()
            )

            if matched_l1 or matched_l2:
                synthesis = (
                    f"Quantitative driver '{fname}' (SHAP={feat.shap_value:+.4f}) is corroborated by "
                    f"{len(matched_l1)} Layer 1 structural check(s) and {len(matched_l2)} Layer 2 observation(s)."
                )
            else:
                synthesis = (
                    f"Quantitative driver '{fname}' (SHAP={feat.shap_value:+.4f}) shifted P(Accept) "
                    f"based on model thresholds."
                )

            integrated_list.append(
                IntegratedEvidence(
                    feature_name=fname,
                    shap_value=feat.shap_value,
                    impact_direction=feat.direction,
                    linked_rule_violations=matched_l1,
                    linked_semantic_evidence=matched_l2,
                    synthesis_summary=synthesis,
                    provenance_items=prov_items,
                )
            )

        logger.info("Integrated evidence across %d top features using exact domain mapping.", len(integrated_list))
        return integrated_list
