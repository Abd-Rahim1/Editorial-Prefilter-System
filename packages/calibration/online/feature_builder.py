"""
feature_builder.py — Online Raw Feature Mapping Builder
Responsible for merging and aggregating raw outputs from Layer 1 and Layer 2 during online inference.
Enforces the exact training-time `risk_multiplier` formula (`(1.0 - overall_quality) * total_rules_failed`)
and delegates alias resolution to common/feature_aliases.py.
Contains no classifier-specific logic and no fabricated features.
"""

from typing import Dict, Any, Union, Optional
from ..common.feature_aliases import apply_aliases_to_mapping
from ..common.contracts import Layer1OutputContract, Layer2OutputContract


def build_raw_features(
    layer1_output: Union[Dict[str, Any], Layer1OutputContract, None] = None,
    layer2_output: Union[Dict[str, Any], Layer2OutputContract, None] = None,
    raw_override: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Combines Layer 1 and Layer 2 results into a raw feature dictionary with canonical key aliases.

    Args:
        layer1_output: Layer 1 rule checks dict or Layer1OutputContract object.
        layer2_output: Layer 2 Qwen LLM scores dict or Layer2OutputContract object.
        raw_override: Optional pre-compiled dictionary of features overriding/supplementing layer outputs.

    Returns:
        Dict[str, Any]: Combined raw feature mapping with alias resolution and exact risk_multiplier.
    """
    raw_map: Dict[str, Any] = {}

    # 1. Extract Layer 1 dictionary
    if layer1_output is not None:
        l1_dict = layer1_output.to_dict() if hasattr(layer1_output, "to_dict") else dict(layer1_output)
        raw_map.update(apply_aliases_to_mapping(l1_dict))

    # 2. Extract Layer 2 dictionary
    if layer2_output is not None:
        l2_dict = layer2_output.to_dict() if hasattr(layer2_output, "to_dict") else dict(layer2_output)
        raw_map.update(apply_aliases_to_mapping(l2_dict))

    # 3. Apply explicit raw feature overrides if supplied
    if raw_override is not None:
        raw_map.update(apply_aliases_to_mapping(raw_override))

    # 4. Compute exact training-time `risk_multiplier` if not explicitly supplied or if derived
    if "risk_multiplier" not in raw_map or raw_map.get("risk_multiplier") is None:
        try:
            oq = float(raw_map.get("overall_quality", 3.0))
            tot_fails = float(raw_map.get("total_rules_failed", 0.0))
            # Exact training-time formula: (1.0 - overall_quality) * total_rules_failed
            raw_map["risk_multiplier"] = (1.0 - oq) * tot_fails
        except (ValueError, TypeError):
            raw_map["risk_multiplier"] = 0.0

    return raw_map
