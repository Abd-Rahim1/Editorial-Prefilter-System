"""
compare_llms.py — LLM Model Comparison for Chapter 5 TFG.

Queries MLflow to compare how the choice of LLM scorer affects downstream
classifier performance.  Expected LLM variants correspond to the four dataset
variants:

  dataset    → Qwen3 4B   (default prompt scoring)
  v1         → Qwen3 4B   (v1 prompts)
  freetext   → Qwen3 4B   (free-text structured prompt)
  qwen_35b   → Qwen3 35B  (larger model)

When runs are enriched with --llm-model metadata, the llm_model_name tag is
also available for direct comparison.

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
    TAG_LLM_MODEL_NAME, TAG_LLM_PROVIDER,
    DATASET_DEFAULT, DATASET_V1, DATASET_FREETEXT, DATASET_QWEN_35B,
)
from experiments.models.common.utils import print_section

DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
DEFAULT_OUTPUT    = PROJECT_ROOT / "experiments" / "reports" / "outputs"

# Canonical mapping from dataset variant to LLM description
DATASET_TO_LLM = {
    DATASET_DEFAULT:  "Qwen3 4B (default prompts)",
    DATASET_V1:       "Qwen3 4B (v1 prompts)",
    DATASET_FREETEXT: "Qwen3 4B (free-text prompt)",
    DATASET_QWEN_35B: "Qwen3 35B",
}


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
            dataset = tags.get("dataset", "Unknown")

            # LLM label: prefer explicit tag, fall back to dataset→LLM mapping
            llm_label = tags.get(TAG_LLM_MODEL_NAME, "") or DATASET_TO_LLM.get(dataset, dataset)
            rows.append({
                "run_id":      run.info.run_id,
                "llm_label":   llm_label,
                "llm_provider":tags.get(TAG_LLM_PROVIDER, ""),
                "dataset":     dataset,
                "classifier":  tags.get("classifier", "Unknown"),
                "feature_set": tags.get("feature_set", "Unknown"),
                "roc_auc":     metrics.get("roc_auc", np.nan),
                "f1":          metrics.get("f1", np.nan),
                "accuracy":    metrics.get("accuracy", np.nan),
                "ece":         metrics.get("ece", np.nan),
            })
    return pd.DataFrame(rows)


def compare_llms(tracking_uri: str = None, output_dir: Path = None) -> pd.DataFrame:
    """Groups runs by LLM label and computes aggregate performance."""
    print_section("LLM MODEL COMPARISON (Chapter 5)")
    df = load_runs(tracking_uri)

    if df.empty:
        print("[!] No completed runs found.")
        return df

    llm_comp = (
        df.groupby(["llm_label", "dataset"])
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

    print("\n" + llm_comp.to_string(index=False, float_format="{:.4f}".format))

    out = Path(output_dir or DEFAULT_OUTPUT)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "compare_llms.csv"
    llm_comp.to_csv(csv_path, index=False)
    print(f"\n[+] Saved: {csv_path}")
    return llm_comp


def main():
    parser = argparse.ArgumentParser(description="Compare LLM scorers across Chapter 5 experiments.")
    parser.add_argument("--tracking-uri", type=str, default=None)
    parser.add_argument("--output-dir",   type=str, default=None)
    args = parser.parse_args()
    compare_llms(args.tracking_uri, args.output_dir)


if __name__ == "__main__":
    main()
