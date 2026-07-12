"""
compare_feature_sets.py — Ablation Study Comparison for Chapter 5 TFG.

Queries MLflow to compare the four feature-set tiers across all classifiers:
  Exp A — Layer 1 structural rule features only
  Exp B — Layer 2 LLM semantic scores only
  Exp C — Hybrid (Layer 1 + Layer 2) — Proposed System
  Exp D — Full (Hybrid + Engineered features)

Produces the Chapter 5 ablation table showing how each information source
contributes to classifier performance.

Output: printed table + CSV in experiments/reports/outputs/.
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
    EXPERIMENT_TYPE_GRID_SEARCH, ALL_TIERS,
)
from experiments.models.common.utils import print_section

DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
DEFAULT_OUTPUT    = PROJECT_ROOT / "experiments" / "reports" / "outputs"

TIER_ORDER = ["Exp_A", "Exp_B", "Exp_C", "Exp_D"]


def load_runs(tracking_uri: str = None) -> pd.DataFrame:
    """Loads all FINISHED grid-search MLflow runs."""
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
            if tags.get("experiment_type") != EXPERIMENT_TYPE_GRID_SEARCH:
                continue
            rows.append({
                "run_id":      run.info.run_id,
                "feature_set": tags.get("feature_set", "Unknown"),
                "classifier":  tags.get("classifier", "Unknown"),
                "dataset":     tags.get("dataset", "Unknown"),
                "roc_auc":     metrics.get("roc_auc", np.nan),
                "f1":          metrics.get("f1", np.nan),
                "accuracy":    metrics.get("accuracy", np.nan),
                "ece":         metrics.get("ece", np.nan),
                "pr_auc":      metrics.get("pr_auc", np.nan),
            })
    return pd.DataFrame(rows)


def compare_feature_sets(tracking_uri: str = None, output_dir: Path = None) -> pd.DataFrame:
    """Builds the ablation study table grouped by feature set."""
    print_section("FEATURE SET ABLATION STUDY (Chapter 5)")
    df = load_runs(tracking_uri)

    if df.empty:
        print("[!] No completed runs found.")
        return df

    ablation = (
        df.groupby("feature_set")
        .agg(
            runs         = ("run_id",  "count"),
            mean_roc_auc = ("roc_auc", "mean"),
            max_roc_auc  = ("roc_auc", "max"),
            mean_f1      = ("f1",      "mean"),
            mean_accuracy= ("accuracy","mean"),
            mean_ece     = ("ece",     "mean"),
        )
        .reset_index()
    )

    # Sort by the canonical tier order A → B → C → D
    ablation["_order"] = ablation["feature_set"].apply(
        lambda x: TIER_ORDER.index(x) if x in TIER_ORDER else 99
    )
    ablation = ablation.sort_values("_order").drop(columns=["_order"])

    print("\n" + ablation.to_string(index=False, float_format="{:.4f}".format))

    # Per-classifier breakdown
    per_clf = (
        df.groupby(["feature_set", "classifier"])
        .agg(
            mean_roc_auc = ("roc_auc", "mean"),
            mean_f1      = ("f1",      "mean"),
            mean_ece     = ("ece",     "mean"),
        )
        .reset_index()
        .sort_values(["feature_set", "mean_roc_auc"], ascending=[True, False])
    )

    out = Path(output_dir or DEFAULT_OUTPUT)
    out.mkdir(parents=True, exist_ok=True)
    ablation.to_csv(out / "compare_feature_sets.csv", index=False)
    per_clf.to_csv(out / "compare_feature_sets_per_classifier.csv", index=False)
    print(f"\n[+] Saved: {out / 'compare_feature_sets.csv'}")
    print(f"[+] Saved: {out / 'compare_feature_sets_per_classifier.csv'}")
    return ablation


def main():
    parser = argparse.ArgumentParser(description="Ablation study: compare feature sets Exp A–D.")
    parser.add_argument("--tracking-uri", type=str, default=None)
    parser.add_argument("--output-dir",   type=str, default=None)
    args = parser.parse_args()
    compare_feature_sets(args.tracking_uri, args.output_dir)


if __name__ == "__main__":
    main()
