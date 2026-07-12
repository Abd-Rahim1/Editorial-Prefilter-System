"""
packages.calibration.offline
Strict offline development and retraining submodule.
Responsible for dataset splitting, cross-validation, hyperparameter tuning, model training,
calibration comparison, verification, exporting, and controlled model promotion into production.

Online inference modules (`packages.calibration.online`) NEVER import anything from this submodule.
"""

from .dataset import load_dataset_splits, load_precomputed_splits
from .classifier_factory import create_classifier
from .calibration_methods import calibrate_model
from .trainer import train_model
from .evaluator import evaluate_model
from .metrics import compute_all_metrics
from .model_selection import select_best_model
from .exporter import export_model_bundle
from .promote_model import promote_candidate_to_production

__all__ = [
    "load_dataset_splits",
    "load_precomputed_splits",
    "create_classifier",
    "calibrate_model",
    "train_model",
    "evaluate_model",
    "compute_all_metrics",
    "select_best_model",
    "export_model_bundle",
    "promote_candidate_to_production"
]
