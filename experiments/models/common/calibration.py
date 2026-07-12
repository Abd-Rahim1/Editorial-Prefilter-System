"""
Probability Calibration Engine for the Chapter 5 TFG Experimentation Framework.

Provides a unified ``calibrate()`` entry point that supports four explicit strategies:

  ``"auto"``      — Evaluates both Sigmoid and Isotonic, keeps the one with the
                    lower Expected Calibration Error (ECE). (default)
  ``"sigmoid"``   — Applies Platt Scaling (CalibratedClassifierCV method="sigmoid").
  ``"isotonic"``  — Applies Isotonic Regression (CalibratedClassifierCV method="isotonic").
  ``"none"``      — Returns the uncalibrated estimator unchanged.

The calibration strategy is chosen via CLI (``--calib``) by the calling train script;
it is NOT controlled by this module.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Any, Dict
from sklearn.calibration import CalibratedClassifierCV
from .metrics import compute_ece

# Public entry point

def calibrate(
    best_estimator: Any,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    method: str = "auto",
    cv: int = 5,
) -> Tuple[Any, str, Dict[str, float]]:
    """
    Calibrates *best_estimator* using the requested *method*.

    Parameters
    ----------
    best_estimator : sklearn estimator
        The already-fitted best estimator from GridSearchCV.
    X_train, y_train : training data used to fit the calibrator.
    X_val, y_val     : held-out data used to compute ECE scores.
    method : str
        One of ``"auto"``, ``"sigmoid"``, ``"isotonic"``, ``"none"``.
    cv : int
        Number of cross-validation folds for CalibratedClassifierCV.

    Returns
    -------
    calibrated_model : fitted model (may be uncalibrated if method="none")
    method_used      : str name of the method that was applied
    ece_scores       : dict with ECE values for "uncalibrated" and whichever
                       methods were evaluated.
    """
    method_clean = method.strip().lower()

    if method_clean == "none":
        return _calibrate_none(best_estimator, X_val, y_val)

    # Compute safe CV folds based on class distribution
    actual_cv = _safe_cv(y_train, cv)

    if method_clean == "sigmoid":
        return _calibrate_single(best_estimator, X_train, y_train, X_val, y_val, "sigmoid", actual_cv)

    if method_clean == "isotonic":
        return _calibrate_single(best_estimator, X_train, y_train, X_val, y_val, "isotonic", actual_cv)

    # Default: "auto" — try both, keep lower ECE
    return calibrate_and_select_best(best_estimator, X_train, y_train, X_val, y_val, cv)


# Strategy implementations

def _safe_cv(y_train: pd.Series, requested_cv: int) -> int:
    """Returns the maximum safe number of CV folds given class distribution."""
    class_counts = pd.Series(y_train).value_counts()
    min_class_count = class_counts.min() if len(class_counts) > 0 else 1
    actual = min(requested_cv, min_class_count)
    return max(actual, 2)


def _uncalibrated_ece(estimator: Any, X_val: pd.DataFrame, y_val: pd.Series) -> Tuple[float, np.ndarray]:
    """Returns ECE and probability array for the uncalibrated estimator."""
    y_val_arr = np.asarray(y_val).astype(int)
    if hasattr(estimator, "predict_proba"):
        probs = estimator.predict_proba(X_val)[:, 1]
    else:
        probs = estimator.predict(X_val).astype(float)
    return compute_ece(y_val_arr, probs), probs


def _calibrate_none(
    estimator: Any,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> Tuple[Any, str, Dict[str, float]]:
    """Returns the uncalibrated estimator; still computes ECE for reporting."""
    uncal_ece, _ = _uncalibrated_ece(estimator, X_val, y_val)
    ece_scores = {"uncalibrated": float(uncal_ece)}
    print(f"[CALIBRATION] Strategy=none - returning uncalibrated model (ECE: {uncal_ece:.4f})")
    return estimator, "none", ece_scores


def _calibrate_single(
    estimator: Any,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    sklearn_method: str,
    actual_cv: int,
) -> Tuple[Any, str, Dict[str, float]]:
    """Fits a single CalibratedClassifierCV with the given sklearn_method."""
    y_val_arr = np.asarray(y_val).astype(int)
    uncal_ece, _ = _uncalibrated_ece(estimator, X_val, y_val)

    try:
        calib = CalibratedClassifierCV(estimator=estimator, method=sklearn_method, cv=actual_cv)
        calib.fit(X_train, y_train)
        cal_probs = calib.predict_proba(X_val)[:, 1]
        cal_ece = compute_ece(y_val_arr, cal_probs)
    except Exception as exc:
        print(
            f"[CALIBRATION] {sklearn_method.capitalize()} calibration failed ({exc}), "
            f"falling back to uncalibrated."
        )
        calib = estimator
        cal_ece = uncal_ece

    ece_scores = {"uncalibrated": float(uncal_ece), sklearn_method: float(cal_ece)}
    print(
        f"[CALIBRATION] Strategy={sklearn_method} — "
        f"ECE: {cal_ece:.4f} (uncalibrated: {uncal_ece:.4f})"
    )
    return calib, sklearn_method, ece_scores


# Auto strategy (legacy entry point kept for backward compatibility)

def calibrate_and_select_best(
    best_estimator: Any,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    cv: int = 5,
) -> Tuple[Any, str, Dict[str, float]]:
    """
    Fits both Sigmoid (Platt Scaling) and Isotonic Regression calibration
    models using CalibratedClassifierCV.  Evaluates ECE on the validation /
    test set and returns the model with the lower ECE.

    This is identical to ``calibrate(..., method="auto")``.

    Returns
    -------
    best_calibrated_model : Fitted CalibratedClassifierCV instance
    best_method_name      : ``"sigmoid"`` or ``"isotonic"``
    ece_scores            : dict with ``"uncalibrated"``, ``"sigmoid"``,
                            and ``"isotonic"`` ECE values.
    """
    y_val_arr = np.asarray(y_val).astype(int)

    # Uncalibrated ECE
    if hasattr(best_estimator, "predict_proba"):
        uncal_prob = best_estimator.predict_proba(X_val)[:, 1]
    else:
        uncal_prob = best_estimator.predict(X_val).astype(float)
    uncal_ece = compute_ece(y_val_arr, uncal_prob)

    actual_cv = _safe_cv(y_train, cv)

    # Sigmoid
    try:
        calib_sigmoid = CalibratedClassifierCV(estimator=best_estimator, method="sigmoid", cv=actual_cv)
        calib_sigmoid.fit(X_train, y_train)
        sig_prob = calib_sigmoid.predict_proba(X_val)[:, 1]
        sig_ece = compute_ece(y_val_arr, sig_prob)
    except Exception as exc:
        print(f"[CALIBRATION] Sigmoid calibration failed ({exc}), using uncalibrated fallback.")
        calib_sigmoid = best_estimator
        sig_ece = uncal_ece

    # Isotonic
    try:
        calib_isotonic = CalibratedClassifierCV(estimator=best_estimator, method="isotonic", cv=actual_cv)
        calib_isotonic.fit(X_train, y_train)
        iso_prob = calib_isotonic.predict_proba(X_val)[:, 1]
        iso_ece = compute_ece(y_val_arr, iso_prob)
    except Exception as exc:
        print(f"[CALIBRATION] Isotonic calibration failed ({exc}), using uncalibrated fallback.")
        calib_isotonic = best_estimator
        iso_ece = uncal_ece

    ece_scores = {
        "uncalibrated": float(uncal_ece),
        "sigmoid":      float(sig_ece),
        "isotonic":     float(iso_ece),
    }

    if sig_ece <= iso_ece:
        best_model  = calib_sigmoid
        best_method = "sigmoid"
    else:
        best_model  = calib_isotonic
        best_method = "isotonic"

    return best_model, best_method, ece_scores
