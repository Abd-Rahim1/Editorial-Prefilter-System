"""
Artifact Manager for the Chapter 5 TFG Experimentation Framework.
Manages model serialization (model.pkl, scaler.pkl, calibration.pkl),
tabular outputs (predictions.csv, test_indices.csv, feature_importance.csv),
publication figures (ROC, PR, Confusion, Calibration, Reliability, Histograms, SHAP),
and calls model_manifest to generate self-describing JSON files.
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend to prevent Tkinter thread crashes
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any, Optional
from sklearn.metrics import (
    confusion_matrix, roc_curve, auc,
    precision_recall_curve, average_precision_score
)
from sklearn.calibration import calibration_curve

from .model_manifest import save_model_manifests
from .utils import ensure_dir

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


def save_all_artifacts(
    output_dir: Path,
    model: Any,
    calibrated_model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    feature_names: List[str],
    model_name: str,
    metrics: Optional[Dict[str, Any]] = None,
    experiment_id: str = "unknown",
    dataset: str = "dataset",
    tier: str = "C",
    calib_method: str = "auto",
    prompt_version: Optional[str] = None,
    llm_model: Optional[str] = None,
    random_seed: int = 42,
    hyperparameters: Optional[Dict[str, Any]] = None,
    scaler: Optional[Any] = None,
) -> Dict[str, Path]:
    """
    Saves serialized models, generates all required evaluation plots and CSVs,
    and creates model manifests.
    Returns a dictionary mapping artifact names to their saved Path objects.
    """
    output_dir = ensure_dir(output_dir)
    saved_paths = {}

    # 1. Save Serialized Models
    model_path = output_dir / "model.pkl"
    joblib.dump(model, model_path)
    saved_paths["model.pkl"] = model_path

    calib_path = output_dir / "calibration.pkl"
    joblib.dump(calibrated_model, calib_path)
    saved_paths["calibration.pkl"] = calib_path

    # Save scaler if provided or if model is a Pipeline with a scaler step
    scaler_to_save = scaler
    if scaler_to_save is None and hasattr(model, "named_steps") and "scaler" in model.named_steps:
        scaler_to_save = model.named_steps["scaler"]
    
    scaler_present = False
    if scaler_to_save is not None:
        scaler_path = output_dir / "scaler.pkl"
        joblib.dump(scaler_to_save, scaler_path)
        saved_paths["scaler.pkl"] = scaler_path
        scaler_present = True

    # 2. Save Tabular CSVs
    # Feature Importance CSV
    fi_path = output_dir / "feature_importance.csv"
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
        fi_df = pd.DataFrame({"feature": feature_names, "importance": imp})
        fi_df = fi_df.sort_values("importance", ascending=False)
    elif hasattr(model, "coef_"):
        coef = model.coef_[0]
        fi_df = pd.DataFrame({"feature": feature_names, "coefficient": coef, "importance": np.abs(coef)})
        fi_df = fi_df.sort_values("importance", ascending=False)
    elif hasattr(model, "named_steps") and hasattr(model.named_steps.get("clf", None), "coef_"):
        coef = model.named_steps["clf"].coef_[0]
        fi_df = pd.DataFrame({"feature": feature_names, "coefficient": coef, "importance": np.abs(coef)})
        fi_df = fi_df.sort_values("importance", ascending=False)
    else:
        fi_df = pd.DataFrame({"feature": feature_names, "importance": [1.0 / len(feature_names)] * len(feature_names)})
    fi_df.to_csv(fi_path, index=False)
    saved_paths["feature_importance.csv"] = fi_path

    # Predictions CSV
    preds_path = output_dir / "predictions.csv"
    preds_df = pd.DataFrame({
        "ground_truth": y_test.values,
        "prediction": y_pred,
        "probability": y_prob
    }, index=y_test.index)
    preds_df.to_csv(preds_path, index=True, index_label="test_index")
    saved_paths["predictions.csv"] = preds_path

    # Test Indices CSV
    indices_path = output_dir / "test_indices.csv"
    indices_df = pd.DataFrame({"test_index": y_test.index})
    indices_df.to_csv(indices_path, index=False)
    saved_paths["test_indices.csv"] = indices_path

    # 3. Configure Plotting Style
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})

    # Confusion Matrix
    cm_path = output_dir / "confusion_matrix.png"
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Rejected (0)", "Accepted (1)"],
                yticklabels=["Rejected (0)", "Accepted (1)"],
                annot_kws={"size": 16, "weight": "bold"})
    plt.title(f"Confusion Matrix: {model_name}", pad=15, weight="bold")
    plt.ylabel("Actual Label (Ground Truth)")
    plt.xlabel("AI Predicted Label")
    plt.tight_layout()
    plt.savefig(cm_path, dpi=300)
    plt.close("all")
    saved_paths["confusion_matrix.png"] = cm_path

    # ROC Curve
    roc_path = output_dir / "roc_curve.png"
    try:
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        roc_auc_val = auc(fpr, tpr)
    except Exception:
        fpr, tpr, roc_auc_val = [0, 1], [0, 1], 0.5
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (AUC = {roc_auc_val:.3f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(f"ROC Curve: {model_name}", weight="bold")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(roc_path, dpi=300)
    plt.close("all")
    saved_paths["roc_curve.png"] = roc_path

    # PR Curve
    pr_path = output_dir / "pr_curve.png"
    try:
        precision, recall, _ = precision_recall_curve(y_test, y_prob)
        pr_auc_val = average_precision_score(y_test, y_prob)
    except Exception:
        precision, recall, pr_auc_val = [0, 1], [0, 1], 0.5
    plt.figure(figsize=(6, 5))
    plt.plot(recall, precision, color="blue", lw=2, label=f"PR curve (AUC = {pr_auc_val:.3f})")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title(f"Precision-Recall Curve: {model_name}", weight="bold")
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(pr_path, dpi=300)
    plt.close("all")
    saved_paths["pr_curve.png"] = pr_path

    # Calibration Curve
    calib_path_img = output_dir / "calibration_curve.png"
    try:
        prob_true, prob_pred = calibration_curve(y_test, y_prob, n_bins=10)
    except Exception:
        prob_true, prob_pred = [0, 1], [0, 1]
    plt.figure(figsize=(6, 5))
    plt.plot(prob_pred, prob_true, marker="o", linewidth=2, label=model_name)
    plt.plot([0, 1], [0, 1], linestyle="--", color="black", label="Perfectly Calibrated")
    plt.xlabel("Mean Predicted Probability (Confidence)")
    plt.ylabel("Fraction of Actual Positives")
    plt.title(f"Calibration Curve: {model_name}", weight="bold")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(calib_path_img, dpi=300)
    plt.close("all")
    saved_paths["calibration_curve.png"] = calib_path_img

    # Reliability Diagram (2-Subplot: Calibration Curve + Confidence Histogram)
    rel_path = output_dir / "reliability_diagram.png"
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    ax1.plot(prob_pred, prob_true, marker="o", linewidth=2, label=model_name, color="#1f77b4")
    ax1.plot([0, 1], [0, 1], linestyle="--", color="black", label="Perfect")
    ax1.set_ylabel("Fraction of Positives")
    ax1.set_title(f"Reliability Diagram: {model_name}", weight="bold")
    ax1.legend(loc="lower right")
    ax2.hist(y_prob, range=(0, 1), bins=10, color="#1f77b4", alpha=0.7, edgecolor="black")
    ax2.set_xlabel("Predicted Probability")
    ax2.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(rel_path, dpi=300)
    plt.close("all")
    saved_paths["reliability_diagram.png"] = rel_path

    # Probability Histogram (by Class)
    hist_path = output_dir / "probability_histogram.png"
    plt.figure(figsize=(7, 5))
    pos_probs = y_prob[y_test == 1]
    neg_probs = y_prob[y_test == 0]
    plt.hist(neg_probs, bins=20, alpha=0.6, label="Rejected (0)", color="red", edgecolor="black")
    plt.hist(pos_probs, bins=20, alpha=0.6, label="Accepted (1)", color="green", edgecolor="black")
    plt.xlabel("Predicted Probability of Acceptance")
    plt.ylabel("Sample Count")
    plt.title(f"Probability Distribution by Class: {model_name}", weight="bold")
    plt.legend(loc="upper center")
    plt.tight_layout()
    plt.savefig(hist_path, dpi=300)
    plt.close("all")
    saved_paths["probability_histogram.png"] = hist_path

    # Feature Importance Plot
    fi_img_path = output_dir / "feature_importance.png"
    plt.figure(figsize=(10, 6))
    top_fi = fi_df.head(15)
    sns.barplot(data=top_fi, x="importance", y="feature", hue="feature", palette="viridis", legend=False)
    plt.title(f"Top Feature Importances: {model_name}", weight="bold")
    plt.xlabel("Relative Importance")
    plt.tight_layout()
    plt.savefig(fi_img_path, dpi=300)
    plt.close("all")
    saved_paths["feature_importance.png"] = fi_img_path

    # SHAP Plots (if available and supported)
    if HAS_SHAP:
        try:
            # Check if model or underlying estimator supports TreeExplainer or LinearExplainer
            est = model
            if hasattr(model, "named_steps") and "clf" in model.named_steps:
                est = model.named_steps["clf"]
            
            explainer = None
            if hasattr(est, "feature_importances_"):
                explainer = shap.TreeExplainer(est)
            elif hasattr(est, "coef_"):
                explainer = shap.LinearExplainer(est, X_test)
                
            if explainer is not None:
                shap_values = explainer.shap_values(X_test)
                if isinstance(shap_values, list):
                    shap_vals_to_plot = shap_values[1] if len(shap_values) > 1 else shap_values[0]
                else:
                    shap_vals_to_plot = shap_values
                
                # SHAP Summary Plot
                shap_sum_path = output_dir / "shap_summary.png"
                plt.figure(figsize=(10, 6))
                shap.summary_plot(shap_vals_to_plot, X_test, feature_names=feature_names, show=False)
                plt.title(f"SHAP Summary: {model_name}", weight="bold")
                plt.tight_layout()
                plt.savefig(shap_sum_path, dpi=300)
                plt.close("all")
                saved_paths["shap_summary.png"] = shap_sum_path
                
                # SHAP Bar Plot
                shap_bar_path = output_dir / "shap_bar.png"
                plt.figure(figsize=(10, 6))
                shap.summary_plot(shap_vals_to_plot, X_test, feature_names=feature_names, plot_type="bar", show=False)
                plt.title(f"SHAP Feature Importance: {model_name}", weight="bold")
                plt.tight_layout()
                plt.savefig(shap_bar_path, dpi=300)
                plt.close("all")
                saved_paths["shap_bar.png"] = shap_bar_path
        except Exception as e:
            print(f"[WARN] Could not generate SHAP plots for {model_name}: {e}")

    # 4. Save Model Manifests (feature_schema, metadata, metrics)
    if metrics is not None:
        manifest_paths = save_model_manifests(
            output_dir=output_dir,
            experiment_id=experiment_id,
            classifier=model_name,
            dataset=dataset,
            feature_set_tier=tier,
            calibration_method=calib_method,
            feature_names=feature_names,
            metrics=metrics,
            prompt_version=prompt_version,
            llm_model=llm_model,
            random_seed=random_seed,
            hyperparameters=hyperparameters,
            scaler_present=scaler_present,
        )
        saved_paths.update(manifest_paths)

    return saved_paths
