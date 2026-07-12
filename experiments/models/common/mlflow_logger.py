"""
MLflow Logger for the Chapter 5 TFG Experimentation Framework.
Manages MLflow experiment tracking: logging parameters, metrics, tags,
and attaching generated model/plot artifacts to each run.
"""

import os
import uuid
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import mlflow
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

from .constants import MLFLOW_EXPERIMENT_NAME

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"



def log_to_mlflow(
    run_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    tags: Dict[str, Any],
    artifacts: Dict[str, Path],
    experiment_name: str = MLFLOW_EXPERIMENT_NAME,
    tracking_uri: Optional[str] = None,
) -> str:
    """
    Logs an experimental run to MLflow.

    Parameters
    ----------
    run_name      : Human-readable name for the run.
    params        : Hyperparameters and configuration values.
    metrics       : Numeric evaluation metrics.
    tags          : String metadata tags (dataset, classifier, etc.).
    artifacts     : Dict mapping artifact names to their local Path objects.
    experiment_name : MLflow experiment to log under (default: TFG_Chapter5_Experiments).
    tracking_uri  : Optional SQLite or HTTP URI override.

    Returns
    -------
    str : The MLflow run ID.
    """
    if not HAS_MLFLOW:
        print("[WARN] MLflow package not installed. Skipping MLflow tracking (saving local manifests & artifacts only).")
        return f"local_run_{uuid.uuid4().hex[:12]}"

    uri = tracking_uri or DEFAULT_MLFLOW_DB
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name) as run:

        # 1. Log Tags (Metadata)
        clean_tags = {str(k): str(v) for k, v in tags.items()}
        mlflow.set_tags(clean_tags)

        # 2. Log Parameters (Hyperparameters & Setup)
        clean_params = {}
        for k, v in params.items():
            val_str = str(v)
            # MLflow parameter value length limit is 500 chars
            if len(val_str) > 450:
                val_str = val_str[:450] + "..."
            clean_params[str(k)] = val_str
        mlflow.log_params(clean_params)

        # 3. Log Numeric Metrics
        clean_metrics = {
            str(k): float(v)
            for k, v in metrics.items()
            if isinstance(v, (int, float, np.number)) and not isinstance(v, bool)
        }
        mlflow.log_metrics(clean_metrics)

        # 4. Log File Artifacts
        for _art_name, art_path in artifacts.items():
            if art_path and Path(art_path).exists():
                mlflow.log_artifact(str(art_path))

        run_id = run.info.run_id

    return run_id
