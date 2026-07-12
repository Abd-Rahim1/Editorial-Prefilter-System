import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    confusion_matrix, roc_curve, auc, 
    precision_recall_curve, average_precision_score
)
from sklearn.calibration import calibration_curve

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
INPUT_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "dataset.csv")
EXPERIMENTS_MODELS_DIR = os.path.join(PROJECT_ROOT, "experiments", "models")
REPORTS_COMPARISON_DIR = os.path.join(PROJECT_ROOT, "reports", "model_comparison")

HYPERPARAMETERS = {
    "logistic_regression": {
        "baseline": [{"C": 1.0, "class_weight": "balanced", "max_iter": 1000}],
        "tuned": [
            {"C": 0.01, "class_weight": "balanced", "max_iter": 1000},
            {"C": 0.1, "class_weight": "balanced", "max_iter": 1000},
            {"C": 10.0, "class_weight": "balanced", "max_iter": 1000},
            {"C": 1.0, "class_weight": None, "max_iter": 1000}
        ]
    },
    "random_forest": {
        "baseline": [{"n_estimators": 100, "max_depth": None, "class_weight": "balanced"}],
        "tuned": [
            {"n_estimators": 100, "max_depth": 3, "min_samples_leaf": 8, "class_weight": "balanced"},
            {"n_estimators": 200, "max_depth": 4, "min_samples_leaf": 6, "class_weight": "balanced"},
            {"n_estimators": 150, "max_depth": 5, "min_samples_leaf": 4, "class_weight": "balanced"},
            {"n_estimators": 100, "max_depth": 4, "min_samples_leaf": 10, "class_weight": None}
        ]
    },
    "xgboost": {
        "baseline": [{"max_depth": 6, "learning_rate": 0.1, "n_estimators": 100}],
        "tuned": [
            {"max_depth": 3, "learning_rate": 0.05, "n_estimators": 200, "min_child_weight": 5},
            {"max_depth": 4, "learning_rate": 0.1, "n_estimators": 150, "min_child_weight": 8},
            {"max_depth": 3, "learning_rate": 0.01, "n_estimators": 300, "min_child_weight": 10},
            {"max_depth": 5, "learning_rate": 0.05, "n_estimators": 150, "min_child_weight": 6}
        ]
    }
}

def get_feature_tiers():
    """Dynamically sorts dataset.csv columns into the requested Experiment Groups."""
    df = pd.read_csv(INPUT_CSV)
    
    # Exp A: Layer 1 Features (Hard Rules & Counts)
    rule_cols = sorted([c for c in df.columns if c.startswith("rule_")])
    l1_counts = [c for c in ["total_rules_failed", "critical_rules_failed"] if c in df.columns]
    layer1_features = rule_cols + l1_counts
    
    # Exp B: Layer 2 Features (Qwen LLM Scores)
    layer2_features = [
        "abstract_clarity", "structural_completeness", "methodological_strength",
        "experimental_strength", "argumentative_quality", "scope_alignment",
        "overall_quality"
    ]
    layer2_features = [c for c in layer2_features if c in df.columns]
    
    # Exp D Meta Additions: Word counts, pages (Dropped - replaced with risk_multiplier)
    meta_features = ["risk_multiplier"]
    meta_features = [c for c in meta_features if c in df.columns]
    
    return {
        "A": layer1_features,
        "B": layer2_features,
        "C": layer1_features + layer2_features + ["risk_multiplier"],   # Hybrid Model (22 features)
        "D": layer1_features + layer2_features + ["risk_multiplier"]     # All available data
    }

def load_and_split_data(exp_tier, scale=True):
    """Loads the dataset, selects specific experiment features, and splits/scales."""
    df = pd.read_csv(INPUT_CSV)
    
    # Handle any potential remaining missing values safely
    numeric_cols = df.select_dtypes(include=['number']).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
    
    feature_tiers = get_feature_tiers()
    selected_features = feature_tiers[exp_tier]
    
    X = df[selected_features]
    y = df["ground_truth"]
    
    # Strict deterministic split (Identical to 06_eda_and_preprocessing.py)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    scaler = StandardScaler() if scale else None
    if scaler:
        X_train = pd.DataFrame(scaler.fit_transform(X_train), columns=X.columns)
        X_test = pd.DataFrame(scaler.transform(X_test), columns=X.columns)
        
    return X_train, X_test, y_train, y_test, scaler, selected_features

def generate_run_plots(model, X_test, y_test, y_pred, y_proba, feature_names, plots_dir, model_name):
    """Generates all 5 standard ML evaluation artifacts automatically."""
    os.makedirs(plots_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    # 1. Confusion Matrix
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Rejected (0)", "Accepted (1)"], 
                yticklabels=["Rejected (0)", "Accepted (1)"],
                annot_kws={"size": 16, "weight": "bold"})
    plt.title(f"Confusion Matrix: {model_name}", pad=15, weight="bold")
    plt.ylabel('Actual Label (Ground Truth)')
    plt.xlabel('AI Predicted Label')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "01_confusion_matrix.png"), dpi=300)
    plt.close()

    # 2. ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'ROC Curve: {model_name}', weight="bold")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "02_roc_curve.png"), dpi=300)
    plt.close()

    # 3. Precision-Recall Curve
    precision, recall, _ = precision_recall_curve(y_test, y_proba)
    pr_auc = average_precision_score(y_test, y_proba)
    plt.figure(figsize=(6, 5))
    plt.plot(recall, precision, color='blue', lw=2, label=f'PR curve (AUC = {pr_auc:.3f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title(f'Precision-Recall Curve: {model_name}', weight="bold")
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "03_precision_recall_curve.png"), dpi=300)
    plt.close()

    # 4. Calibration Curve (Reliability Diagram)
    prob_true, prob_pred = calibration_curve(y_test, y_proba, n_bins=10)
    plt.figure(figsize=(6, 5))
    plt.plot(prob_pred, prob_true, marker='o', linewidth=2, label=model_name)
    plt.plot([0, 1], [0, 1], linestyle='--', color='black', label='Perfectly Calibrated')
    plt.xlabel('Mean predicted probability (Confidence)')
    plt.ylabel('Fraction of actual positives')
    plt.title(f'Calibration Curve: {model_name}', weight="bold")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "04_calibration_curve.png"), dpi=300)
    plt.close()

    # 5. Feature Importance
    plt.figure(figsize=(10, 6))
    est = model
    if hasattr(model, 'calibrated_classifiers_') and len(model.calibrated_classifiers_) > 0:
        est = model.calibrated_classifiers_[0].estimator
    elif hasattr(model, 'estimator'):
        est = model.estimator

    if hasattr(est, 'feature_importances_'):
        importances = est.feature_importances_
        indices = np.argsort(importances)[::-1][:15] # Top 15 features
        sns.barplot(x=importances[indices], y=[feature_names[i] for i in indices], palette="viridis")
        plt.title(f'Feature Importance: {model_name}', weight="bold")
        plt.xlabel('Relative Importance')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "05_feature_importance.png"), dpi=300)
    elif hasattr(est, 'coef_'):
        importances = np.abs(est.coef_[0])
        indices = np.argsort(importances)[::-1][:15]
        sns.barplot(x=importances[indices], y=[feature_names[i] for i in indices], hue=[feature_names[i] for i in indices], palette="mako", legend=False)
        plt.title(f'Feature Importance (Absolute Coefficients): {model_name}', weight="bold")
        plt.xlabel('Absolute Coefficient Value')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "05_feature_importance.png"), dpi=300)
    plt.close()