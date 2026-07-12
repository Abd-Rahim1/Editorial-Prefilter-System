"""
evaluator.py — Offline Model Evaluation & Threshold Verification
Runs evaluation on a test DataFrame and verifies whether metrics meet or exceed target benchmarks.
"""

from typing import Dict, Any, Tuple, List
import pandas as pd
import numpy as np

from .metrics import compute_all_metrics
from ..common.constants import WINNER_ROC_AUC, WINNER_MCC, WINNER_F1, WINNER_ECE
from ..common.exceptions import Layer3Error


def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series, threshold: float = 0.5) -> Dict[str, Any]:
    """Runs inference on test split and computes complete metric evaluation dictionary.

    Args:
        model: Fitted estimator.
        X_test: Test features DataFrame.
        y_test: Test target Series.
        threshold: Decision cutoff probability.

    Returns:
        Dict[str, Any]: Metrics report.
    """
    classes = getattr(model, "classes_", np.array([0, 1]))
    pos_idx = 1 if len(classes) > 1 else 0
    for idx, c in enumerate(classes):
        if str(c).lower() in ["1", "true", "accept"]:
            pos_idx = idx
            break

    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_test)[:, pos_idx]
    elif hasattr(model, "decision_function"):
        scores = model.decision_function(X_test)
        probs = 1.0 / (1.0 + np.exp(-scores))
    else:
        preds = model.predict(X_test)
        probs = np.array([1.0 if str(p).lower() in ["1", "true", "accept"] else 0.0 for p in preds])

    return compute_all_metrics(y_test.values, probs, threshold=threshold)


def verify_against_winner_benchmarks(metrics: Dict[str, Any], tolerance: float = 0.05) -> Tuple[bool, List[str]]:
    """Checks whether candidate model metrics match or exceed the TFG_Evaluation study winner benchmarks within tolerance."""
    reasons = []
    passed = True

    if metrics.get("roc_auc", 0.0) < (WINNER_ROC_AUC - tolerance):
        passed = False
        reasons.append(f"ROC AUC ({metrics.get('roc_auc', 0):.4f}) is below winner benchmark ({WINNER_ROC_AUC} - {tolerance})")

    if metrics.get("mcc", 0.0) < (WINNER_MCC - tolerance):
        passed = False
        reasons.append(f"MCC ({metrics.get('mcc', 0):.4f}) is below winner benchmark ({WINNER_MCC} - {tolerance})")

    if metrics.get("f1", 0.0) < (WINNER_F1 - tolerance):
        passed = False
        reasons.append(f"F1 ({metrics.get('f1', 0):.4f}) is below winner benchmark ({WINNER_F1} - {tolerance})")

    if metrics.get("ece", 1.0) > (WINNER_ECE + tolerance):
        passed = False
        reasons.append(f"ECE ({metrics.get('ece', 1):.4f}) exceeds winner benchmark ({WINNER_ECE} + {tolerance})")

    return passed, reasons
