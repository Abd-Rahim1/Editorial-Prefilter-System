"""
model_selection.py — Two-Stage Classifier & Calibration Selection
Implements scientifically sound two-stage selection:
  - Phase 1a: Classifier & hyperparameter selection on validation splits (uncalibrated).
  - Phase 1b: Calibration method selection for the Phase 1a winner based on ECE & Brier score.
"""

from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from .trainer import train_model
from .calibration_methods import calibrate_model
from .evaluator import evaluate_model
from ..common.exceptions import Layer3Error


def select_best_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    candidate_classifiers: Optional[List[str]] = None,
    candidate_calibrations: Optional[List[str]] = None,
    random_seed: int = 42
) -> Dict[str, Any]:
    """Runs Phase 1a (Classifier selection) and Phase 1b (Calibration selection).

    Args:
        X_train: Training split features.
        y_train: Training split targets.
        X_val: Validation split features.
        y_val: Validation split targets.
        candidate_classifiers: List of classifier names to evaluate.
        candidate_calibrations: List of calibration methods for Phase 1b.
        random_seed: Seed.

    Returns:
        Dict[str, Any]: Selection report with winning model, method, metrics, and phase logs.
    """
    classifiers = candidate_classifiers or ["Random_Forest", "Logistic_Regression"]
    calibrations = candidate_calibrations or ["none", "sigmoid", "isotonic"]

    phase1a_logs = []
    best_clf_name = classifiers[0]
    best_clf_model = None
    best_clf_score = -1.0
    best_clf_metrics: Dict[str, Any] = {}

    for clf_name in classifiers:
        try:
            model, t_ms = train_model(X_train, y_train, classifier_name=clf_name, random_seed=random_seed)
            metrics = evaluate_model(model, X_val, y_val)
            metrics["training_time_ms"] = t_ms
            phase1a_logs.append({"classifier": clf_name, "metrics": metrics})

            # Primary rank: ROC AUC, Secondary: MCC
            rank_score = metrics["roc_auc"] + 0.1 * metrics["mcc"]
            if rank_score > best_clf_score:
                best_clf_score = rank_score
                best_clf_name = clf_name
                best_clf_model = model
                best_clf_metrics = metrics
        except Exception as e:
            phase1a_logs.append({"classifier": clf_name, "error": str(e)})

    if not best_clf_model:
        raise Layer3Error("[ModelSelection Error] Phase 1a failed across all candidate classifiers.")

    phase1b_logs = []
    best_cal_method = "none"
    best_cal_model = best_clf_model
    best_cal_metrics = best_clf_metrics
    # Rank calibration primarily by lowest ECE + Brier score, provided ROC AUC does not drop > 0.02
    best_cal_rank = best_clf_metrics["ece"] + best_clf_metrics["brier_score"]

    for cal_method in calibrations:
        try:
            if cal_method == "none":
                cal_model = best_clf_model
                metrics = best_clf_metrics
            else:
                cal_model = calibrate_model(best_clf_model, cal_method, X_val, y_val, cv=3)
                metrics = evaluate_model(cal_model, X_val, y_val)

            phase1b_logs.append({"method": cal_method, "metrics": metrics})

            if metrics["roc_auc"] >= (best_clf_metrics["roc_auc"] - 0.02):
                cal_rank = metrics["ece"] + metrics["brier_score"]
                if cal_rank < best_cal_rank:
                    best_cal_rank = cal_rank
                    best_cal_method = cal_method
                    best_cal_model = cal_model
                    best_cal_metrics = metrics
        except Exception as e:
            phase1b_logs.append({"method": cal_method, "error": str(e)})

    return {
        "winning_classifier": best_clf_name,
        "winning_calibration": best_cal_method,
        "winning_model": best_cal_model,
        "winning_metrics": best_cal_metrics,
        "phase1a_logs": phase1a_logs,
        "phase1b_logs": phase1b_logs
    }
