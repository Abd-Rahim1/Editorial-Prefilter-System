"""
metrics.py — Offline Evaluation Metric Computation
Computes rigorous statistical and calibration metrics required for thesis verification and reporting:
ROC AUC, PR AUC, MCC, F1, Accuracy, Precision, Recall, ECE (Expected Calibration Error), Brier Score, and Confusion Matrix.
"""

from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    auc,
    matthews_corrcoef,
    f1_score,
    accuracy_score,
    precision_score,
    recall_score,
    brier_score_loss,
    confusion_matrix
)


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) with equal-width probability bins."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total_samples = len(y_true)

    if total_samples == 0:
        return 0.0

    for i in range(n_bins):
        bin_lower = bin_edges[i]
        bin_upper = bin_edges[i + 1]
        mask = (y_prob >= bin_lower) & (y_prob <= bin_upper if i == n_bins - 1 else y_prob < bin_upper)
        bin_count = np.sum(mask)

        if bin_count > 0:
            avg_conf = np.mean(y_prob[mask])
            avg_acc = np.mean(y_true[mask])
            ece += (bin_count / total_samples) * np.abs(avg_conf - avg_acc)

    return float(ece)


def compute_all_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """Computes complete dictionary of offline classification and calibration metrics."""
    y_true_arr = np.array(y_true, dtype=int)
    y_prob_arr = np.array(y_prob, dtype=float)
    y_pred_arr = (y_prob_arr >= threshold).astype(int)

    # Handle single-class edge case gracefully
    if len(np.unique(y_true_arr)) < 2:
        roc = 0.5
        pr = 0.5
    else:
        roc = float(roc_auc_score(y_true_arr, y_prob_arr))
        prec_vec, rec_vec, _ = precision_recall_curve(y_true_arr, y_prob_arr)
        pr = float(auc(rec_vec, prec_vec))

    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1]).tolist()

    return {
        "accuracy": float(accuracy_score(y_true_arr, y_pred_arr)),
        "precision": float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
        "roc_auc": roc,
        "pr_auc": pr,
        "mcc": float(matthews_corrcoef(y_true_arr, y_pred_arr)),
        "brier_score": float(brier_score_loss(y_true_arr, y_prob_arr)),
        "ece": compute_ece(y_true_arr, y_prob_arr),
        "confusion_matrix": cm
    }
