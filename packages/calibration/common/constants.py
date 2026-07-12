"""
constants.py — Shared Layer 3 Constants and Filesystem Paths
Defines immutable paths and configuration defaults shared between online and offline modules.
"""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent.parent.resolve()
MODELS_DIR = PACKAGE_ROOT / "models"

# Production frozen model paths
BEST_PIPELINE_PATH = MODELS_DIR / "best_pipeline.joblib"
FEATURE_SCHEMA_PATH = MODELS_DIR / "feature_schema.json"
METADATA_PATH = MODELS_DIR / "metadata.json"
CHECKSUMS_PATH = MODELS_DIR / "checksums.json"

DEFAULT_MODEL_VERSION = "v1.0"
DEFAULT_FEATURE_SET = "C2"
DEFAULT_CLASSIFIER = "Random_Forest"
DEFAULT_CALIBRATION_METHOD = "none"
DEFAULT_SCHEMA_VERSION = "1.0"

# Exact verified metrics of the selected TFG_Evaluation winner
WINNER_ROC_AUC = 0.6733
WINNER_MCC = 0.2403
WINNER_F1 = 0.6822
WINNER_ECE = 0.0589
