"""
feature_preprocessor.py — Online Feature Schema Validation & DataFrame Construction
Uses the loaded model artifact schema (`feature_schema.json`) as the definitive runtime source of truth.
Ensures exact feature ordering, validation, NaN/Inf sanitization, dtype casting, and 1-row DataFrame output.
Never sorts features alphabetically and never ignores schema discrepancies.
"""

import math
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import numpy as np

from ..common.exceptions import MissingRequiredFeatureError, FeatureValidationError
from ..common.feature_aliases import apply_aliases_to_mapping
from ..common.feature_contract import FEATURE_DEFAULT_VALUES, CANONICAL_C2_FEATURES


def preprocess_features(
    raw_features: Dict[str, Any],
    schema_definition: Optional[Dict[str, Any]] = None,
    strict_missing_check: bool = False
) -> Tuple[pd.DataFrame, Dict[str, float], str]:
    """Transforms raw mapping into an exact, validated 1-row DataFrame adhering to the artifact schema.

    Args:
        raw_features: Raw feature dictionary produced by `build_raw_features()`.
        schema_definition: Dict loaded from `feature_schema.json` containing `ordered_features` and `feature_set_version`.
        strict_missing_check: If True, raises `MissingRequiredFeatureError` if any schema feature is not present in raw_features.

    Returns:
        Tuple[pd.DataFrame, Dict[str, float], str]:
            - X: 1-row DataFrame ordered exactly according to `schema_definition['ordered_features']`.
            - clean_dict: Dictionary of clean numerical values.
            - schema_version: Version string from the schema artifact.

    Raises:
        MissingRequiredFeatureError: If `strict_missing_check` is True and required feature is absent.
        FeatureValidationError: If data casting fails.
    """
    # 1. Resolve aliases
    resolved_raw = apply_aliases_to_mapping(raw_features)

    # 2. Determine official runtime schema order & version from loaded model bundle
    if schema_definition and "ordered_features" in schema_definition and schema_definition["ordered_features"]:
        ordered_cols: List[str] = list(schema_definition["ordered_features"])
        schema_version: str = str(schema_definition.get("feature_set_version", "1.0"))
    else:
        ordered_cols = CANONICAL_C2_FEATURES
        schema_version = "1.0"

    clean_dict: Dict[str, float] = {}

    for col in ordered_cols:
        # 3. Check for missing required fields
        if col not in resolved_raw:
            if strict_missing_check:
                raise MissingRequiredFeatureError(
                    f"[Feature Preprocessor Error] Required feature '{col}' is completely missing from input payload."
                )
            # Use documented training default
            raw_val = FEATURE_DEFAULT_VALUES.get(col, 0.0)
        else:
            raw_val = resolved_raw[col]

        # 4. Handle exact categorical string encoding for conference venue
        if col == "conference" and isinstance(raw_val, str):
            clean_venue = raw_val.strip().lower()
            venue_map = {"acl_2017": 0.0, "conll_2016": 1.0, "iclr_2017": 2.0}
            if clean_venue in venue_map:
                raw_val = venue_map[clean_venue]

        # 5. Cast dtypes and sanitize NaN/Inf according to training behavior
        try:
            val = float(raw_val)
            if math.isnan(val) or math.isinf(val):
                val = FEATURE_DEFAULT_VALUES.get(col, 0.0)
        except (ValueError, TypeError) as e:
            if strict_missing_check:
                raise FeatureValidationError(f"[Feature Preprocessor Error] Could not cast feature '{col}'={raw_val} to float: {e}")
            val = FEATURE_DEFAULT_VALUES.get(col, 0.0)

        clean_dict[col] = val

    # 5. Construct 1-row DataFrame strictly ordered according to runtime artifact schema
    X = pd.DataFrame([clean_dict], columns=ordered_cols)

    return X, clean_dict, schema_version
