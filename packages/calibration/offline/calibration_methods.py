"""
calibration_methods.py — Offline Post-Processing Probability Calibration
Applies post-processing probability calibration (`sigmoid`, `isotonic`, `auto`, `none`)
to a fitted base estimator using cross-validation (`CalibratedClassifierCV`).
Note: The validated TFG_Evaluation study winner selected `none` (`RandomForestClassifier` without wrapper).
"""

from typing import Any
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV


def calibrate_model(base_model: Any, method: str, X_cal: pd.DataFrame, y_cal: pd.Series, cv: int = 5) -> Any:
    """Wraps or returns `base_model` with post-processing calibration.

    Args:
        base_model: Fitted or un-fitted supervised estimator.
        method: 'none', 'sigmoid', 'isotonic', or 'auto'.
        X_cal: Calibration/validation feature matrix.
        y_cal: Calibration/validation binary target vector.
        cv: Cross-validation folds for fitting calibrator.

    Returns:
        Calibrated model or original base_model if method is 'none'.
    """
    clean_method = method.strip().lower()
    if clean_method in ["none", "uncalibrated", ""]:
        return base_model

    if clean_method == "auto":
        # Select isotonic if enough samples (>= 1000), else sigmoid
        chosen = "isotonic" if len(X_cal) >= 1000 else "sigmoid"
    elif clean_method in ["sigmoid", "platt"]:
        chosen = "sigmoid"
    elif clean_method == "isotonic":
        chosen = "isotonic"
    else:
        raise ValueError(f"Unknown calibration method '{method}'. Supported: none, sigmoid, isotonic, auto.")

    calibrated = CalibratedClassifierCV(estimator=base_model, method=chosen, cv=cv)
    calibrated.fit(X_cal, y_cal)
    return calibrated
