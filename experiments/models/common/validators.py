"""
validators.py — Input Validation for the Chapter 5 Experimentation Framework.

All functions raise clear, descriptive exceptions early — before expensive
training begins — so that misconfigured CLI runs fail fast with actionable
messages.

Validates:
  - Dataset integrity (required columns, ground_truth balance)
  - Feature-set tier identifiers
  - CLI argument combinations
  - Model output interface (predict_proba presence)
  - Metrics dict completeness
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional

from .constants import ALL_TIERS, ALL_CALIBRATIONS, ALL_CLASSIFIERS, NUMERIC_METRICS


def validate_dataset(df: pd.DataFrame, require_ground_truth: bool = True) -> None:
    """
    Validates a loaded dataset DataFrame.

    Checks:
      - DataFrame is not empty.
      - ``ground_truth`` column exists (if *require_ground_truth*).
      - ``ground_truth`` contains only 0/1 integers.
      - Both classes (0 and 1) are present (warns if severely imbalanced).
      - At least one numeric feature column is present.

    Raises
    ------
    ValueError
        If any hard constraint is violated.
    """
    if df is None or df.empty:
        raise ValueError("Dataset is empty or None.")

    if require_ground_truth:
        if "ground_truth" not in df.columns:
            raise ValueError(
                "Dataset must contain a 'ground_truth' column. "
                "Rename from 'label', 'accepted', or 'decision' before loading."
            )
        unique_vals = df["ground_truth"].dropna().unique()
        if not set(unique_vals).issubset({0, 1}):
            raise ValueError(
                f"'ground_truth' must contain only 0/1 integer values. "
                f"Found: {sorted(unique_vals)}"
            )
        class_counts = df["ground_truth"].value_counts()
        if len(class_counts) < 2:
            raise ValueError(
                "Dataset has only one class in 'ground_truth'. "
                "Both 0 (rejected) and 1 (accepted) must be present."
            )
        minority_ratio = class_counts.min() / len(df)
        if minority_ratio < 0.05:
            print(
                f"[WARN] Severe class imbalance detected: minority class "
                f"is {minority_ratio*100:.1f}% of the dataset. "
                f"Consider oversampling or class_weight='balanced'."
            )

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c != "ground_truth"]
    if not feature_cols:
        raise ValueError(
            "Dataset contains no numeric feature columns. "
            "Ensure LLM scores and rule features are present."
        )


def validate_feature_matrix(X: pd.DataFrame, min_features: int = 1) -> None:
    """
    Validates the feature matrix X returned by ``select_features()``.

    Raises
    ------
    ValueError
        If X is empty or has fewer than *min_features* columns.
    """
    if X is None or X.empty:
        raise ValueError("Feature matrix is empty after selection.")
    if len(X.columns) < min_features:
        raise ValueError(
            f"Feature matrix has only {len(X.columns)} column(s); "
            f"at least {min_features} required."
        )
    if X.isnull().any().any():
        null_cols = X.columns[X.isnull().any()].tolist()
        raise ValueError(
            f"Feature matrix contains NaN values in columns: {null_cols}. "
            f"Run clean_and_impute() before feature selection."
        )


def validate_tier(tier: str) -> str:
    """
    Returns the normalised (uppercase, stripped) tier letter, or raises.

    Parameters
    ----------
    tier : str
        User-supplied tier, e.g. ``"c"``, ``"A"``.

    Returns
    -------
    str
        Uppercase tier letter.

    Raises
    ------
    ValueError
        If *tier* is not one of A, B, C, D.
    """
    t = tier.strip().upper()
    if t not in ALL_TIERS:
        raise ValueError(
            f"Unknown feature-set tier '{tier}'. "
            f"Must be one of: {ALL_TIERS}."
        )
    return t


def validate_calib_method(method: str) -> str:
    """
    Returns the normalised (lowercase, stripped) calibration method, or raises.

    Raises
    ------
    ValueError
        If *method* is not a recognised calibration strategy.
    """
    m = method.strip().lower()
    if m not in ALL_CALIBRATIONS:
        raise ValueError(
            f"Unknown calibration method '{method}'. "
            f"Must be one of: {ALL_CALIBRATIONS}."
        )
    return m


def validate_classifier_name(name: str) -> str:
    """
    Returns the normalised classifier name, or raises.

    Raises
    ------
    ValueError
        If *name* is not a recognised classifier key.
    """
    n = name.strip().lower()
    if n not in ALL_CLASSIFIERS:
        raise ValueError(
            f"Unknown classifier '{name}'. "
            f"Must be one of: {ALL_CLASSIFIERS}."
        )
    return n


def validate_has_predict_proba(model: Any, model_name: str = "model") -> None:
    """
    Warns if *model* does not expose ``predict_proba``.
    Some metrics (ROC AUC, ECE, Brier Score) require probability outputs;
    fallback to hard predictions will degrade calibration metrics.
    """
    if not hasattr(model, "predict_proba"):
        print(
            f"[WARN] {model_name} does not have predict_proba(). "
            f"Probability-based metrics (ECE, Brier, PR AUC) will use "
            f"hard predictions as a fallback and will be inaccurate."
        )


def validate_metrics_dict(metrics: Dict[str, Any], strict: bool = False) -> List[str]:
    """
    Checks that a metrics dict produced by ``compute_all_metrics()`` contains
    all expected numeric metric keys.

    Parameters
    ----------
    metrics : dict
        Output of ``compute_all_metrics()``.
    strict : bool
        If True, raises ValueError on missing keys; otherwise returns a list
        of missing key names.

    Returns
    -------
    list[str]
        Names of any missing metric keys (empty list if all present).

    Raises
    ------
    ValueError
        If *strict=True* and any key is missing.
    """
    missing = [k for k in NUMERIC_METRICS if k not in metrics]
    if missing and strict:
        raise ValueError(
            f"Metrics dict is incomplete. Missing keys: {missing}"
        )
    return missing
