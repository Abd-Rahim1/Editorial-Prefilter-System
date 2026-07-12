"""
exporter.py — Offline Candidate Bundle Exporter
Exports a newly trained/selected candidate model along with its schema, metadata, metrics,
and SHA-256 checksums into a designated candidate folder (`artifacts/candidates/<run_id>/`).
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import joblib

from ..common.constants import PACKAGE_ROOT, DEFAULT_SCHEMA_VERSION, DEFAULT_FEATURE_SET
from ..common.feature_contract import CANONICAL_C2_FEATURES


def _compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def export_model_bundle(
    model: Any,
    metrics: Dict[str, Any],
    output_dir: Path,
    classifier_name: str = "Random_Forest",
    calibration_method: str = "none",
    model_version: str = "v1.0-candidate"
) -> Dict[str, str]:
    """Serializes model, schema, metadata, metrics, and checksums into `output_dir`.

    Args:
        model: Fitted estimator/pipeline object.
        metrics: Evaluation metrics dictionary.
        output_dir: Target directory path.
        classifier_name: Name of classifier.
        calibration_method: Calibration method applied.
        model_version: Version identifier.

    Returns:
        Dict[str, str]: Map of exported file names to absolute file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save joblib model
    model_p = output_dir / "model.joblib"
    joblib.dump(model, model_p)

    # 2. Save feature schema
    schema_data = {
        "feature_set": DEFAULT_FEATURE_SET,
        "feature_set_version": DEFAULT_SCHEMA_VERSION,
        "ordered_features": CANONICAL_C2_FEATURES,
        "number_of_features": len(CANONICAL_C2_FEATURES),
        "target_column": "ground_truth"
    }
    schema_p = output_dir / "feature_schema.json"
    with open(schema_p, "w", encoding="utf-8") as f:
        json.dump(schema_data, f, indent=2)

    # 3. Save metrics JSON
    metrics_p = output_dir / "metrics.json"
    with open(metrics_p, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # 4. Save metadata JSON
    meta_data = {
        "classifier": classifier_name,
        "feature_set": DEFAULT_FEATURE_SET,
        "calibration_method": calibration_method,
        "model_version": model_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "roc_auc": metrics.get("roc_auc", 0.0),
        "mcc": metrics.get("mcc", 0.0),
        "f1": metrics.get("f1", 0.0),
        "ece": metrics.get("ece", 0.0)
    }
    meta_p = output_dir / "metadata.json"
    with open(meta_p, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)

    # 5. Compute SHA-256 digests and save checksums.json
    checksums = {
        "model": _compute_sha256(model_p),
        "schema": _compute_sha256(schema_p),
        "metadata": _compute_sha256(meta_p),
        "metrics": _compute_sha256(metrics_p)
    }
    chk_p = output_dir / "checksums.json"
    with open(chk_p, "w", encoding="utf-8") as f:
        json.dump(checksums, f, indent=2)

    return {
        "model": str(model_p),
        "schema": str(schema_p),
        "metadata": str(meta_p),
        "metrics": str(metrics_p),
        "checksums": str(chk_p)
    }
