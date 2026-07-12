"""
constants.py — Centralized constants for the Chapter 5 Experimentation Framework.

Single source of truth for:
  - Metric names & ordering
  - Artifact filenames
  - Folder/path names
  - Default values
  - MLflow tag keys & experiment names
  - Calibration & classifier options
  - Feature-set tier identifiers

Nothing in this file performs I/O or has side effects.
"""

# MLflow

MLFLOW_EXPERIMENT_NAME = "TFG_Chapter5_Experiments"

# Standard MLflow tag keys (used consistently across all train scripts)
TAG_DATASET            = "dataset"
TAG_FEATURE_SET        = "feature_set"
TAG_FEATURE_SET_NAME   = "feature_set_name"
TAG_CLASSIFIER         = "classifier"
TAG_CALIBRATION_METHOD = "calibration_method"
TAG_EXPERIMENT_TYPE    = "experiment_type"
TAG_RANDOM_SEED        = "random_seed"
TAG_LLM_MODEL_NAME     = "llm_model_name"
TAG_LLM_PROVIDER       = "llm_provider"
TAG_LLM_VERSION        = "llm_version"
TAG_LLM_CONTEXT_LENGTH = "llm_context_length"
TAG_LLM_PARAMETERS     = "llm_parameters"
TAG_LLM_LATENCY_MS     = "llm_latency_ms"
TAG_PROMPT_ID          = "prompt_id"
TAG_PROMPT_NAME        = "prompt_name"
TAG_PROMPT_VERSION     = "prompt_version"
TAG_PROMPT_DESCRIPTION = "prompt_description"

EXPERIMENT_TYPE_GRID_SEARCH  = "grid_search_calibrated"
EXPERIMENT_TYPE_BASELINE     = "classical_baseline"

# Dataset variants

DATASET_DEFAULT   = "dataset"
DATASET_V1        = "v1"
DATASET_FREETEXT  = "freetext"
DATASET_QWEN_35B  = "qwen_35b"

ALL_DATASETS = [DATASET_DEFAULT, DATASET_V1, DATASET_FREETEXT, DATASET_QWEN_35B]

# Feature-set (ablation) tiers

TIER_A = "A"
TIER_B = "B"
TIER_C = "C"
TIER_D = "D"

ALL_TIERS = [TIER_A, TIER_B, TIER_C, TIER_D]

# Classifiers

CLF_LOGISTIC_REGRESSION = "logistic_regression"
CLF_RANDOM_FOREST       = "random_forest"
CLF_XGBOOST             = "xgboost"

ALL_CLASSIFIERS = [CLF_LOGISTIC_REGRESSION, CLF_RANDOM_FOREST, CLF_XGBOOST]

# Display names used in MLflow tags and reports
CLF_DISPLAY_NAMES = {
    CLF_LOGISTIC_REGRESSION: "Logistic_Regression",
    CLF_RANDOM_FOREST:       "Random_Forest",
    CLF_XGBOOST:             "XGBoost",
}

# Run-name prefixes used in MLflow
CLF_RUN_PREFIXES = {
    CLF_LOGISTIC_REGRESSION: "LR",
    CLF_RANDOM_FOREST:       "RF",
    CLF_XGBOOST:             "XGB",
}

# Calibration strategies

CALIB_AUTO     = "auto"
CALIB_SIGMOID  = "sigmoid"
CALIB_ISOTONIC = "isotonic"
CALIB_NONE     = "none"

ALL_CALIBRATIONS = [CALIB_AUTO, CALIB_SIGMOID, CALIB_ISOTONIC, CALIB_NONE]

# Metric names (in canonical order for tables and CSV exports)

METRIC_ACCURACY          = "accuracy"
METRIC_PRECISION         = "precision"
METRIC_RECALL            = "recall"
METRIC_F1                = "f1"
METRIC_ROC_AUC           = "roc_auc"
METRIC_PR_AUC            = "pr_auc"
METRIC_BALANCED_ACCURACY = "balanced_accuracy"
METRIC_MCC               = "mcc"
METRIC_BRIER_SCORE       = "brier_score"
METRIC_ECE               = "ece"
METRIC_CONFUSION_MATRIX  = "confusion_matrix"
METRIC_TRAINING_TIME_MS  = "training_time_ms"
METRIC_INFERENCE_TIME_MS = "inference_time_ms"

NUMERIC_METRICS = [
    METRIC_ACCURACY,
    METRIC_PRECISION,
    METRIC_RECALL,
    METRIC_F1,
    METRIC_ROC_AUC,
    METRIC_PR_AUC,
    METRIC_BALANCED_ACCURACY,
    METRIC_MCC,
    METRIC_BRIER_SCORE,
    METRIC_ECE,
    METRIC_TRAINING_TIME_MS,
    METRIC_INFERENCE_TIME_MS,
]  # 12 numeric + confusion_matrix = 13 total tracked values

# Artifact filenames

ARTIFACT_MODEL_PKL                 = "model.pkl"
ARTIFACT_SCALER_PKL                = "scaler.pkl"
ARTIFACT_CALIBRATION_PKL           = "calibration.pkl"
ARTIFACT_FEATURE_SCHEMA_JSON       = "feature_schema.json"
ARTIFACT_METADATA_JSON             = "metadata.json"
ARTIFACT_METRICS_JSON              = "metrics.json"
ARTIFACT_FEATURE_IMPORTANCE_CSV    = "feature_importance.csv"
ARTIFACT_PREDICTIONS_CSV           = "predictions.csv"
ARTIFACT_TEST_INDICES_CSV          = "test_indices.csv"
ARTIFACT_TRAINING_LOG              = "training.log"

# Publication figures
ARTIFACT_CONFUSION_MATRIX_PNG      = "confusion_matrix.png"
ARTIFACT_ROC_CURVE_PNG             = "roc_curve.png"
ARTIFACT_PR_CURVE_PNG              = "pr_curve.png"
ARTIFACT_CALIBRATION_CURVE_PNG     = "calibration_curve.png"
ARTIFACT_RELIABILITY_DIAGRAM_PNG   = "reliability_diagram.png"
ARTIFACT_PROBABILITY_HISTOGRAM_PNG = "probability_histogram.png"
ARTIFACT_FEATURE_IMPORTANCE_PNG    = "feature_importance.png"
ARTIFACT_SHAP_SUMMARY_PNG          = "shap_summary.png"
ARTIFACT_SHAP_BAR_PNG              = "shap_bar.png"

# Folder names (relative to project root or experiment root)

RUNS_SUBDIR    = "runs"
OUTPUTS_SUBDIR = "outputs"
LOGS_SUBDIR    = "logs"
RESULTS_SUBDIR = "results"

# Default values

DEFAULT_TEST_SIZE   = 0.2
DEFAULT_RANDOM_SEED = 42
DEFAULT_CV_FOLDS    = 5
DEFAULT_ECE_BINS    = 10
