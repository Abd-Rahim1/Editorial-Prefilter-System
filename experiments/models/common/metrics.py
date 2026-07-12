"""
Evaluation Metrics Engine for the Chapter 5 TFG Experimentation Framework.
Computes Accuracy, Precision, Recall, F1, ROC AUC, PR AUC, Balanced Accuracy,
Matthews Correlation Coefficient (MCC), Brier Score, Expected Calibration Error (ECE),
Confusion Matrix, Training Time, and Inference Time.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, balanced_accuracy_score,
    matthews_corrcoef, brier_score_loss, confusion_matrix
)

def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """
    Computes Expected Calibration Error (ECE) across n_bins uniform probability intervals.
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total_samples = len(y_prob)
    
    if total_samples == 0:
        return 0.0
        
    for i in range(n_bins):
        bin_lower = bin_edges[i]
        bin_upper = bin_edges[i + 1]
        
        # Include upper bound in last bin
        if i == n_bins - 1:
            in_bin = (y_prob >= bin_lower) & (y_prob <= bin_upper)
        else:
            in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper)
            
        bin_count = np.sum(in_bin)
        if bin_count > 0:
            bin_acc = np.mean(y_true[in_bin])
            bin_conf = np.mean(y_prob[in_bin])
            ece += (bin_count / total_samples) * np.abs(bin_acc - bin_conf)
            
    return float(ece)

def compute_all_metrics(
    y_true: Any,
    y_pred: Any,
    y_prob: Optional[Any] = None,
    train_time_ms: float = 0.0,
    inference_time_ms: float = 0.0
) -> Dict[str, Any]:
    """
    Computes all 13 required evaluation metrics for Chapter 5 experiments.
    Returns a dictionary of float values and the confusion matrix list.
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_pred_arr = np.asarray(y_pred).astype(int)
    
    if y_prob is None:
        y_prob_arr = y_pred_arr.astype(float)
    else:
        y_prob_arr = np.asarray(y_prob).astype(float)
        
    # Safety check for single-class edge case in validation splits
    unique_classes = np.unique(y_true_arr)
    
    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    prec = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))
    bal_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    mcc = float(matthews_corrcoef(y_true_arr, y_pred_arr))
    
    if len(unique_classes) > 1:
        try:
            roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
        except Exception:
            roc_auc = acc
        try:
            pr_auc = float(average_precision_score(y_true_arr, y_prob_arr))
        except Exception:
            pr_auc = prec
    else:
        roc_auc = 0.5
        pr_auc = prec
        
    brier = float(brier_score_loss(y_true_arr, y_prob_arr))
    ece = compute_ece(y_true_arr, y_prob_arr, n_bins=10)
    
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
    
    return {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "balanced_accuracy": bal_acc,
        "mcc": mcc,
        "brier_score": brier,
        "ece": ece,
        "confusion_matrix": cm.tolist(),
        "training_time_ms": float(train_time_ms),
        "inference_time_ms": float(inference_time_ms)
    }
