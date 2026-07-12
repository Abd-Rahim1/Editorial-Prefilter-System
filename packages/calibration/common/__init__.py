"""
packages.calibration.common
Shared contracts, exceptions, constants, and feature definitions accessible across both
online production inference and offline development/retraining workflows.
"""

from .contracts import (
    Layer1OutputContract,
    Layer2OutputContract,
    FeatureSchemaContract,
    ModelMetadataContract
)
from .feature_contract import (
    CANONICAL_C2_FEATURES,
    FEATURE_DATA_TYPES,
    FEATURE_DEFAULT_VALUES
)
from .feature_aliases import resolve_feature_alias
from .constants import (
    DEFAULT_MODEL_VERSION,
    DEFAULT_FEATURE_SET,
    DEFAULT_CLASSIFIER,
    DEFAULT_CALIBRATION_METHOD,
    PACKAGE_ROOT,
    MODELS_DIR,
    BEST_PIPELINE_PATH,
    FEATURE_SCHEMA_PATH,
    METADATA_PATH,
    CHECKSUMS_PATH
)
from .exceptions import (
    Layer3Error,
    ModelLoadError,
    ModelIntegrityError,
    FeatureValidationError,
    MissingRequiredFeatureError,
    ThresholdPolicyError
)

__all__ = [
    "Layer1OutputContract",
    "Layer2OutputContract",
    "FeatureSchemaContract",
    "ModelMetadataContract",
    "CANONICAL_C2_FEATURES",
    "FEATURE_DATA_TYPES",
    "FEATURE_DEFAULT_VALUES",
    "resolve_feature_alias",
    "DEFAULT_MODEL_VERSION",
    "DEFAULT_FEATURE_SET",
    "DEFAULT_CLASSIFIER",
    "DEFAULT_CALIBRATION_METHOD",
    "PACKAGE_ROOT",
    "MODELS_DIR",
    "BEST_PIPELINE_PATH",
    "FEATURE_SCHEMA_PATH",
    "METADATA_PATH",
    "CHECKSUMS_PATH",
    "Layer3Error",
    "ModelLoadError",
    "ModelIntegrityError",
    "FeatureValidationError",
    "MissingRequiredFeatureError",
    "ThresholdPolicyError"
]
