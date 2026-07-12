"""
schemas.py — Online Production Data Transfer Objects (DTOs)
Defines strict, typed input request and output prediction schemas for the fast online path (< 30ms latency).
Uses Pydantic BaseModel (or dataclasses fallback) following repository standards.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


if PYDANTIC_AVAILABLE:
    class PredictionRequest(BaseModel):
        """Incoming payload containing Layer 1 and Layer 2 outputs for a manuscript."""
        manuscript_id: Optional[str] = Field(None, description="Unique manuscript identifier")
        layer1_rules: Dict[str, Any] = Field(default_factory=dict, description="Layer 1 rule check results or counts")
        layer2_scores: Dict[str, Any] = Field(default_factory=dict, description="Layer 2 LLM quality scores (0.0 to 5.0)")
        raw_features_override: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional pre-extracted raw features")

        class Config:
            arbitrary_types_allowed = True

    class Layer3Prediction(BaseModel):
        """Final structured prediction response returned by Layer3Service to the backend."""
        manuscript_id: Optional[str] = None
        accept_probability: float = Field(..., description="Explicit positive class probability P(Accept) [0.0, 1.0]")
        desk_reject_probability: float = Field(..., description="Explicit negative class probability P(Desk Reject) [0.0, 1.0]")
        decision: str = Field(..., description="Actionable recommendation: Desk Reject, Send to Peer Review, etc.")
        confidence_level: str = Field("HIGH", description="Confidence rating: HIGH vs MODERATE")
        model_id: Optional[int] = Field(1, description="Database or registry ID of the active model")
        model_version: str = Field("v1.0", description="Version of the active deployment pipeline")
        classifier: str = Field("Random_Forest", description="Name of the underlying ML classifier")
        feature_schema_version: str = Field("1.0", description="Version of the feature schema used during inference")
        calibration_method: str = Field("none", description="Probability calibration method applied (`none` for study winner)")
        threshold_profile_version: str = Field("1.0", description="Version/ID of the threshold policy applied")
        inference_time_ms: float = Field(..., description="End-to-end Layer 3 inference execution duration in milliseconds")
        feature_vector: Dict[str, float] = Field(default_factory=dict, description="Preprocessed C2 feature vector fed into model")

        class Config:
            arbitrary_types_allowed = True

else:
    @dataclass
    class PredictionRequest:
        manuscript_id: Optional[str] = None
        layer1_rules: Dict[str, Any] = field(default_factory=dict)
        layer2_scores: Dict[str, Any] = field(default_factory=dict)
        raw_features_override: Optional[Dict[str, Any]] = field(default_factory=dict)

    @dataclass
    class Layer3Prediction:
        accept_probability: float
        desk_reject_probability: float
        decision: str
        inference_time_ms: float
        confidence_level: str = "HIGH"
        manuscript_id: Optional[str] = None
        model_id: Optional[int] = 1
        model_version: str = "v1.0"
        classifier: str = "Random_Forest"
        feature_schema_version: str = "1.0"
        calibration_method: str = "none"
        threshold_profile_version: str = "1.0"
        feature_vector: Dict[str, float] = field(default_factory=dict)

        def dict(self) -> Dict[str, Any]:
            return {
                "manuscript_id": self.manuscript_id,
                "accept_probability": self.accept_probability,
                "desk_reject_probability": self.desk_reject_probability,
                "decision": self.decision,
                "confidence_level": self.confidence_level,
                "model_id": self.model_id,
                "model_version": self.model_version,
                "classifier": self.classifier,
                "feature_schema_version": self.feature_schema_version,
                "calibration_method": self.calibration_method,
                "threshold_profile_version": self.threshold_profile_version,
                "inference_time_ms": self.inference_time_ms,
                "feature_vector": self.feature_vector
            }

        def model_dump(self) -> Dict[str, Any]:
            return self.dict()
