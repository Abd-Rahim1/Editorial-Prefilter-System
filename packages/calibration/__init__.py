"""
packages.calibration — Dual-Mode Layer 3 Production Package
Root module exposing ONLY the stable, high-performance online production API (< 30ms latency).
Offline retraining and model evaluation modules are strictly isolated inside `packages.calibration.offline`.

Usage:
    from packages.calibration import Layer3Service, PredictionRequest

    service = Layer3Service()
    prediction = service.predict(manuscript_id="MS-101", layer1_result=l1, layer2_result=l2)
"""

from typing import Dict, Any, Union, Optional
from .online.schemas import PredictionRequest, Layer3Prediction
from .online.service import Layer3Service
from .common.exceptions import (
    Layer3Error,
    ModelLoadError,
    ModelIntegrityError,
    FeatureValidationError,
    MissingRequiredFeatureError,
    ThresholdPolicyError
)

# Global lazy service instance for backward-compatible `predict()` convenience wrapper
_default_service: Optional[Layer3Service] = None


def predict(
    manuscript_id: Optional[str] = None,
    layer1_result: Optional[Union[Dict[str, Any], Any]] = None,
    layer2_result: Optional[Union[Dict[str, Any], Any]] = None,
    request: Optional[PredictionRequest] = None,
    custom_thresholds: Optional[Dict[str, Any]] = None
) -> Layer3Prediction:
    """Convenience wrapper around default `Layer3Service.predict()`."""
    global _default_service
    if _default_service is None:
        _default_service = Layer3Service()
    return _default_service.predict(
        manuscript_id=manuscript_id,
        layer1_result=layer1_result,
        layer2_result=layer2_result,
        request=request,
        custom_thresholds=custom_thresholds
    )


__all__ = [
    "PredictionRequest",
    "Layer3Prediction",
    "Layer3Service",
    "predict",
    "Layer3Error",
    "ModelLoadError",
    "ModelIntegrityError",
    "FeatureValidationError",
    "MissingRequiredFeatureError",
    "ThresholdPolicyError"
]
