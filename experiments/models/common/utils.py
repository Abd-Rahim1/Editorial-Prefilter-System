"""
utils.py — Shared Helper Utilities for the Chapter 5 Experimentation Framework.

Provides:
  - Reproducibility: seed setting & git commit hash retrieval
  - I/O: directory creation helpers
  - Timing: context manager for measuring elapsed time
  - Logging: structured console print helpers & per-experiment file logging
  - Paths: experiment output path builder
"""

import os
import time
import random
import logging
import subprocess
import numpy as np
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Union, Tuple


# Reproducibility

def set_global_seed(seed: int = 42) -> None:
    """
    Sets the random seed for Python, NumPy, and (if available) PyTorch and
    TensorFlow so that all randomness in an experiment is reproducible.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)

    try:
        import torch  # noqa: F401 (optional dependency)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass

    try:
        import tensorflow as tf  # noqa: F401 (optional dependency)
        tf.random.set_seed(seed)
    except ImportError:
        pass


def get_git_commit_hash() -> str:
    """Returns the current git commit hash, or 'unknown' if not in a git repo."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


# Directory helpers

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Creates *path* (and any missing parents) if it does not already exist.
    Returns the resolved Path.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_run_output_dir(
    project_root: Path,
    classifier_subdir: str,
    dataset_variant: str,
    tier: str,
    calib_method: str,
    base_subdir: str = "runs",
) -> Path:
    """
    Returns the canonical output directory for a single experiment run:

      <project_root>/experiments/models/<classifier_subdir>/runs/
          <dataset_variant>_Exp<tier>_<calib_method>/

    The directory is created automatically.
    """
    out = (
        project_root
        / "experiments"
        / "models"
        / classifier_subdir
        / base_subdir
        / f"{dataset_variant}_Exp{tier}_{calib_method}"
    )
    return ensure_dir(out)


# Logging utilities

def setup_experiment_logger(
    experiment_id: str,
    project_root: Optional[Path] = None,
    log_dir: Optional[Path] = None,
) -> Tuple[logging.Logger, Path]:
    """
    Configures and returns a dedicated file logger for an experiment run.
    Logs are written to experiments/logs/<experiment_id>.log.
    """
    if log_dir is None:
        if project_root is None:
            project_root = Path(__file__).resolve().parents[3]
        log_dir = ensure_dir(project_root / "experiments" / "logs")
    else:
        log_dir = ensure_dir(log_dir)

    log_path = log_dir / f"{experiment_id}.log"
    
    logger = logging.getLogger(f"exp_{experiment_id}")
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers if re-initializing
    if logger.handlers:
        logger.handlers.clear()
        
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger, log_path


# Timing utilities

@contextmanager
def timer():
    """
    Context manager that measures elapsed wall-clock time in milliseconds.

    Usage::

        with timer() as t:
            model.fit(X_train, y_train)
        print(t.elapsed_ms)   # float, milliseconds
    """
    class _T:
        elapsed_ms: float = 0.0

    t = _T()
    start = time.perf_counter()
    try:
        yield t
    finally:
        t.elapsed_ms = (time.perf_counter() - start) * 1000.0


# Console logging helpers

def print_section(title: str, width: int = 74) -> None:
    """Prints a bold section header."""
    print("\n" + "=" * width)
    print(f"   {title}")
    print("=" * width)


def print_subsection(title: str, width: int = 74) -> None:
    """Prints a subsection divider."""
    print(f"\n{'-' * width}")
    print(f"   {title}")
    print(f"{'-' * width}")


def print_metrics(metrics: dict, indent: int = 5) -> None:
    """
    Prints the standard 7 primary metrics from a metrics dict produced by
    ``compute_all_metrics()``.
    """
    pad = " " * indent
    pairs = [
        ("Accuracy",          "accuracy"),
        ("Precision",         "precision"),
        ("Recall",            "recall"),
        ("F1 Score",          "f1"),
        ("ROC AUC",           "roc_auc"),
        ("PR AUC",            "pr_auc"),
        ("ECE (Calibration)", "ece"),
    ]
    for label, key in pairs:
        val = metrics.get(key)
        if val is not None:
            print(f"{pad}{label:<22}: {val:.4f}")


def print_experiment_header(
    classifier: str,
    dataset: str,
    tier: str,
    calib: str,
    width: int = 74,
) -> None:
    """Prints a standardized experiment start header."""
    print("\n" + "=" * width)
    print(f"   TRAINING {classifier.upper()}")
    print(f"   Dataset={dataset} | Tier=Exp_{tier} | Calib={calib}")
    print("=" * width)
