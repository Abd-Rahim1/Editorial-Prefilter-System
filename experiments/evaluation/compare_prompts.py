"""
compare_prompts.py — Prompt Version Comparison for Chapter 5 TFG.

Queries MLflow to compare how different prompt template versions affect
classifier performance.  Prompt version is logged as a tag on each MLflow
run (enriched via db_metadata.py).

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

from experiments.models.common.constants import TAG_PROMPT_VERSION
from experiments.models.common.utils import print_section

DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
DEFAULT_OUTPUT    = PROJECT_ROOT / "experiments" / "reports" / "outputs"


def load_runs(tracking_uri: str = None) -> pd.DataFrame:
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
            prompt_ver = tags.get(TAG_PROMPT_VERSION, "")
            rows.append({
                "run_id":         run.info.run_id,
                "prompt_version": prompt_ver,
                "prompt_name":    tags.get("prompt_name", ""),
                "classifier":     tags.get("classifier", "Unknown"),
                "dataset":        tags.get("dataset", "Unknown"),
                "feature_set":    tags.get("feature_set", "Unknown"),
                "roc_auc":        metrics.get("roc_auc", np.nan),
                "f1":             metrics.get("f1", np.nan),
                "accuracy":       metrics.get("accuracy", np.nan),
                "ece":            metrics.get("ece", np.nan),
            })
    return pd.DataFrame(rows)


def compare_prompts(tracking_uri: str = None, output_dir: Path = None) -> pd.DataFrame:
    """Groups runs by prompt version and computes aggregate performance."""
    print_section("PROMPT VERSION COMPARISON (Chapter 5)")
    df = load_runs(tracking_uri)

    if df.empty:
        print("[!] No completed runs found.")
        return df

    # Only include runs that have a non-empty prompt_version tag
    df_with_prompt = df[df["prompt_version"].str.strip() != ""]
    if df_with_prompt.empty:
        print("[!] No runs with prompt_version tags found. Run experiments with --prompt-version.")
        return df_with_prompt

    prompt_comp = (
        df_with_prompt.groupby(["prompt_version", "prompt_name"])
        .agg(
            runs         = ("run_id",  "count"),
            mean_roc_auc = ("roc_auc", "mean"),
            max_roc_auc  = ("roc_auc", "max"),
            mean_f1      = ("f1",      "mean"),
            mean_accuracy= ("accuracy","mean"),
            mean_ece     = ("ece",     "mean"),
        )
        .reset_index()
        .sort_values("mean_roc_auc", ascending=False)
    )

    print("\n" + prompt_comp.to_string(index=False, float_format="{:.4f}".format))

    out = Path(output_dir or DEFAULT_OUTPUT)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "compare_prompts.csv"
    prompt_comp.to_csv(csv_path, index=False)
    print(f"\n[+] Saved: {csv_path}")
    return prompt_comp


def main():
    parser = argparse.ArgumentParser(description="Compare prompt versions across Chapter 5 experiments.")
    parser.add_argument("--tracking-uri", type=str, default=None)
    parser.add_argument("--output-dir",   type=str, default=None)
    args = parser.parse_args()
    compare_prompts(args.tracking_uri, args.output_dir)


if __name__ == "__main__":
    main()
