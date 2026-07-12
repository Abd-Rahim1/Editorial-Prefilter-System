"""
Feature Ranker Module — Layer 4 Explainable AI Engine.

Responsible for sorting raw SHAP attribution values (produced by
``ShapExplainer``) into a ranked, human-comprehensible list of
:class:`RankedFeature` objects.

Direction semantics (relative to the neutral baseline):
  * ``INCREASED_REJECT_RISK``  — positive SHAP; feature pushed the
    rejection probability *above* what the baseline predicts.
  * ``DECREASED_REJECT_RISK``  — negative SHAP; feature pulled the
    rejection probability *below* the baseline (mitigating factor).
  * ``NEUTRAL``                — attribution magnitude < 1e-6;
    feature had negligible influence on this prediction.
"""

from dataclasses import dataclass, asdict
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Threshold below which an attribution is considered mathematically negligible
_ZERO_THRESHOLD: float = 1e-6


@dataclass
class RankedFeature:
    """
    Represents a single model feature ranked by its explainability attribution.

    Attributes:
        name:            Feature column name as used during training.
        shap_value:      Signed SHAP attribution (positive = increases reject
                         probability; negative = decreases it).
        absolute_impact: ``abs(shap_value)`` — used for ranking.
        direction:       Human-readable impact direction label.
        rank:            1-based position in the ranked list (1 = most
                         influential).
    """

    name: str
    shap_value: float
    absolute_impact: float
    direction: str
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary for JSON serialization."""
        return asdict(self)


class FeatureRanker:
    """
    Ranks tabular features by the absolute magnitude of their SHAP values and
    annotates each with a semantic direction label.
    """

    @staticmethod
    def rank_features(
        shap_values: Dict[str, float],
        top_n: int = 5,
    ) -> List[RankedFeature]:
        """
        Sort SHAP attributions and return the ``top_n`` most influential
        features with direction labels.

        Args:
            shap_values: Dictionary mapping feature names to **signed** SHAP
                         values produced by :class:`ShapExplainer`.  Positive
                         values indicate factors that increase the probability
                         of desk rejection; negative values are mitigating
                         factors that lower it.
            top_n:       Maximum number of top features to return.

        Returns:
            List of :class:`RankedFeature` objects sorted from most to least
            influential, each labelled with a human-readable direction.

        Notes:
            * All features receive a direction label regardless of whether
              they appear in the top-N list; only the top-N are returned.
            * Features with ``|shap_value| < 1e-6`` are labelled ``NEUTRAL``
              and will naturally sort to the bottom.
        """
        if not shap_values:
            logger.warning("Empty SHAP values dictionary provided to FeatureRanker.")
            return []

        ranked_list: List[RankedFeature] = []
        for name, val in shap_values.items():
            abs_val = abs(val)

            if abs_val < _ZERO_THRESHOLD:
                direction = "NEUTRAL"
            elif val > 0:
                direction = "INCREASED_ACCEPT_PROBABILITY"
            else:
                direction = "DECREASED_ACCEPT_PROBABILITY"

            ranked_list.append(
                RankedFeature(
                    name=name,
                    shap_value=round(val, 6),
                    absolute_impact=round(abs_val, 6),
                    direction=direction,
                    rank=0,  # assigned after sort
                )
            )

        # Sort descending by absolute impact
        ranked_list.sort(key=lambda item: item.absolute_impact, reverse=True)

        # Assign 1-based ranks and take top-N
        for position, feature in enumerate(ranked_list, start=1):
            feature.rank = position

        top_ranked = ranked_list[:top_n]

        n_nonzero = sum(1 for rf in top_ranked if rf.direction != "NEUTRAL")
        logger.info(
            "Ranked %d features (top-%d selected, %d with non-zero SHAP).",
            len(ranked_list),
            len(top_ranked),
            n_nonzero,
        )
        return top_ranked
