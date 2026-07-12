"""
compare_models.py — Classifier Comparison for Chapter 5 TFG.

Queries MLflow to compare the three classifiers:
  - Logistic Regression
  - Random Forest
  - XGBoost

Groups results by classifier and computes aggregate statistics
(mean/max ROC AUC, F1, ECE) across all datasets and feature tiers.

Output: printed ranking table + CSV saved to experiments/reports/outputs/.
"""

import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import mlflow
from mlflow.tracking import MlflowClient

from experiments.models.common.constants import (
    MLFLOW_EXPERIMENT_NAME, EXPERIMENT_TYPE_GRID_SEARCH,
    ALL_CLASSIFIERS, CLF_DISPLAY_NAMES,
)
from experiments.models.common.utils import print_section

DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
DEFAULT_OUTPUT    = PROJECT_ROOT / "experiments" / "reports" / "outputs"


def load_runs(tracking_uri: str = None, experiment_type_filter: str = None) -> pd.DataFrame:
    """Loads all FINISHED MLflow runs and returns a flat DataFrame."""
    uri = tracking_uri or DEFAULT_MLFLOW_DB
    mlflow.set_tracking_uri(uri)
    client = MlflowClient(tracking_uri=uri)

    rows = []
    for exp in client.search_experiments():
        for run in client.search_runs(experiment_ids=[exp.experiment_id]):
            if run.info.status != "FINISHED":
                continue
            tags    = run.data.tags
            metrics = run.data.metrics
            if experiment_type_filter and tags.get("experiment_type") != experiment_type_filter:
                continue
            rows.append({
                "run_id":             run.info.run_id,
                "classifier":         tags.get("classifier", "Unknown"),
                "dataset":            tags.get("dataset", "Unknown"),
                "feature_set":        tags.get("feature_set", "Unknown"),
                "calibration_method": tags.get("calibration_method", "none"),
                "accuracy":           metrics.get("accuracy", np.nan),
                "precision":          metrics.get("precision", np.nan),
                "recall":             metrics.get("recall", np.nan),
                "f1":                 metrics.get("f1", np.nan),
                "roc_auc":            metrics.get("roc_auc", np.nan),
                "pr_auc":             metrics.get("pr_auc", np.nan),
                "ece":                metrics.get("ece", np.nan),
                "brier_score":        metrics.get("brier_score", np.nan),
                "training_time_ms":   metrics.get("training_time_ms", np.nan),
            })
    return pd.DataFrame(rows)


def compare_models(tracking_uri: str = None, output_dir: Path = None) -> pd.DataFrame:
    """Builds and prints the classifier ranking table."""
    print_section("CLASSIFIER COMPARISON (Chapter 5)")
    df = load_runs(tracking_uri, experiment_type_filter=EXPERIMENT_TYPE_GRID_SEARCH)

    if df.empty:
        print("[!] No completed grid-search runs found in MLflow.")
        return df

    ranking = (
        df.groupby("classifier")
        .agg(
            runs        = ("run_id",          "count"),
            mean_roc_auc = ("roc_auc",        "mean"),
            max_roc_auc  = ("roc_auc",        "max"),
            mean_f1      = ("f1",             "mean"),
            mean_accuracy= ("accuracy",       "mean"),
            mean_ece     = ("ece",            "mean"),
            mean_train_ms= ("training_time_ms","mean"),
        )
        .reset_index()
        .sort_values("mean_roc_auc", ascending=False)
    )

    print("\n" + ranking.to_string(index=False, float_format="{:.4f}".format))

    out = Path(output_dir or DEFAULT_OUTPUT)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "compare_classifiers.csv"
    ranking.to_csv(csv_path, index=False)
    print(f"\n[+] Saved: {csv_path}")
    return ranking


def main():
    parser = argparse.ArgumentParser(description="Compare classifiers across Chapter 5 experiments.")
    parser.add_argument("--tracking-uri", type=str, default=None)
    parser.add_argument("--output-dir",   type=str, default=None)
    args = parser.parse_args()
    compare_models(args.tracking_uri, args.output_dir)


if __name__ == "__main__":
    main()
