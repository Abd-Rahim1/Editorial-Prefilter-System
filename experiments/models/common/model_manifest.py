"""
model_manifest.py — Self-Describing Model Manifest Generator for Chapter 5 TFG.

Generates the three mandatory JSON files required in every trained model folder:
  1. feature_schema.json : Canonical ordered feature schema for production inference.
  2. metadata.json       : Audit, lineage, git commit, MLflow run ID, and timestamps.
  3. metrics.json        : Canonical summary of all 13 evaluation metrics.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from .feature_selector import FEATURE_SETS
from .utils import get_git_commit_hash, ensure_dir


def save_model_manifests(
    output_dir: Path,
    experiment_id: str,
    classifier: str,
    dataset: str,
    feature_set_tier: str,
    calibration_method: str,
    feature_names: List[str],
    metrics: Dict[str, Any],
    prompt_version: Optional[str] = None,
    llm_model: Optional[str] = None,
    random_seed: int = 42,
    mlflow_run_id: str = "",
    hyperparameters: Optional[Dict[str, Any]] = None,
    scaler_present: bool = False,
) -> Dict[str, Path]:
    """
    Generates and writes feature_schema.json, metadata.json, and metrics.json
    into output_dir. Returns a dict mapping filename to saved Path.
    """
    output_dir = ensure_dir(output_dir)
    saved_paths = {}

    tier_upper = feature_set_tier.upper().strip()
    feat_meta = FEATURE_SETS.get(tier_upper, {})
    version_str = feat_meta.get("version", "1.0")

    # 1. feature_schema.json
    schema_data = {
        "feature_set": tier_upper,
        "feature_set_version": version_str,
        "ordered_features": list(feature_names),
        "number_of_features": len(feature_names),
        "target_column": "ground_truth",
    }
    schema_path = output_dir / "feature_schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema_data, f, indent=2)
    saved_paths["feature_schema.json"] = schema_path

    # 2. metadata.json
    meta_data = {
        "experiment_id": experiment_id,
        "classifier": classifier,
        "dataset": dataset,
        "feature_set": tier_upper,
        "feature_set_version": version_str,
        "calibration_method": calibration_method,
        "prompt_version": prompt_version or "default",
        "llm_model": llm_model or "default",
        "random_seed": random_seed,
        "git_commit": get_git_commit_hash(),
        "mlflow_run_id": mlflow_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "training_time": metrics.get("training_time_ms", 0.0),
        "inference_time": metrics.get("inference_time_ms", 0.0),
        "scaler_present": scaler_present,
        "hyperparameters": hyperparameters or {},
    }
    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)
    saved_paths["metadata.json"] = meta_path

    # 3. metrics.json
    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    saved_paths["metrics.json"] = metrics_path

    return saved_paths


def update_metadata_mlflow_id(output_dir: Path, mlflow_run_id: str) -> None:
    """
    Updates an existing metadata.json with the generated MLflow run ID after logging.
    """
    meta_path = Path(output_dir) / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["mlflow_run_id"] = mlflow_run_id
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to update mlflow_run_id in metadata.json: {e}")
