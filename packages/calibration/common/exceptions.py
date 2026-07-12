"""
exceptions.py — Layer 3 Exception Hierarchy
Centralized exceptions raised during online inference or offline training/model loading.
"""

class Layer3Error(Exception):
    """Base exception for all errors within the Layer 3 package."""
    pass


class ModelLoadError(Layer3Error):
    """Raised when a required model artifact, schema, or metadata file cannot be loaded or resolved."""
    pass


class ModelIntegrityError(ModelLoadError):
    """Raised when SHA-256 checksum validation or artifact integrity check fails."""
    pass


class FeatureValidationError(Layer3Error):
    """Raised when feature validation, type conversion, or schema matching fails."""
    pass


class MissingRequiredFeatureError(FeatureValidationError):
    """Raised when a required canonical feature is completely missing and cannot be imputed/resolved."""
    pass


class ThresholdPolicyError(Layer3Error):
    """Raised when threshold policy configuration or bounds checking fails."""
    pass


class ConfigurationError(Layer3Error):
    """Raised when configuration resolution, multiple active models, or DB schema integration fails."""
    pass


class NoActiveModelError(ConfigurationError):
    """Raised when no active model is found in production environment."""
    pass


class MultipleActiveModelsError(ConfigurationError):
    """Raised when multiple active trained models (is_active=True) are found."""
    pass

