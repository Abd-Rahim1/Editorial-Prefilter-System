"""
service.py — Layer3Service Production Orchestration Boundary
The single entry point for backend services (`Layer 4`, API routes, background workers) to execute
online editorial predictions using the verified Tier C2 Random Forest model.

Orchestrates:
  1. Active model bundle resolution & loading (`ModelLoader`)
  2. Raw feature construction (`feature_builder.build_raw_features`)
  3. Strict schema validation (`feature_preprocessor.preprocess_features`)
  4. Probability inference (`Predictor.predict_probabilities`)
  5. Editorial threshold policy mapping (`ThresholdPolicy.evaluate_decision`)
  6. Typed response generation (`Layer3Prediction`) with latency monitoring.
"""

import time
from typing import Dict, Any, Union, Optional
from .schemas import PredictionRequest, Layer3Prediction, PYDANTIC_AVAILABLE
from .model_loader import ModelLoader
from .predictor import Predictor
from .threshold_policy import ThresholdPolicy
from .feature_builder import build_raw_features
from .feature_preprocessor import preprocess_features
from ..common.exceptions import Layer3Error


class Layer3Service:
    """Production service Boundary for Layer 3 online inference."""

    def __init__(
        self,
        loader: Optional[ModelLoader] = None,
        predictor: Optional[Predictor] = None,
        policy: Optional[ThresholdPolicy] = None,
        db_session: Optional[Any] = None
    ):
        self.loader = loader or ModelLoader(resolver=None if db_session is None else None)
        self.predictor = predictor or Predictor()
        self.policy = policy or ThresholdPolicy(db_session=db_session)

    def get_active_model(self) -> Any:
        """Returns the active loaded scikit-learn model instance."""
        bundle = self.loader.load_active_bundle()
        return bundle.get("model")

    def get_feature_names(self) -> list[str]:
        """Returns the canonical ordered feature names list."""
        bundle = self.loader.load_active_bundle()
        schema = bundle.get("schema", {})
        if isinstance(schema, dict) and "ordered_features" in schema:
            return list(schema["ordered_features"])
        model = bundle.get("model")
        if hasattr(model, "feature_names_in_"):
            return list(model.feature_names_in_)
        return []

    def predict(
        self,
        manuscript_id: Optional[str] = None,
        layer1_result: Optional[Union[Dict[str, Any], Any]] = None,
        layer2_result: Optional[Union[Dict[str, Any], Any]] = None,
        request: Optional[PredictionRequest] = None,
        custom_thresholds: Optional[Dict[str, Any]] = None,
        strict_missing_check: bool = False
    ) -> Layer3Prediction:
        """Executes full end-to-end Layer 3 online prediction.

        Args:
            manuscript_id: Unique identifier string for the manuscript.
            layer1_result: Upstream Layer 1 rule outputs.
            layer2_result: Upstream Layer 2 Qwen LLM scores.
            request: Optional pre-constructed `PredictionRequest` DTO encapsulating the above.
            custom_thresholds: Optional override dict for threshold policy bands.
            strict_missing_check: If True, raises exceptions when required features are missing from payload.

        Returns:
            Layer3Prediction: Fully populated, typed prediction response DTO.
        """
        t0 = time.perf_counter()

        # 1. Parse incoming arguments / request DTO
        if request is not None:
            ms_id = request.manuscript_id or manuscript_id
            l1 = request.layer1_rules
            l2 = request.layer2_scores
            raw_override = request.raw_features_override
        else:
            ms_id = manuscript_id
            l1 = layer1_result or {}
            l2 = layer2_result or {}
            raw_override = None

        # 2. Load cached model bundle
        bundle = self.loader.load_active_bundle()

        # 3. Build raw feature dictionary
        raw_dict = build_raw_features(layer1_output=l1, layer2_output=l2, raw_override=raw_override)

        # 4. Preprocess features to exact artifact schema order
        X, fv_dict, schema_ver = preprocess_features(
            raw_features=raw_dict,
            schema_definition=bundle.get("schema"),
            strict_missing_check=strict_missing_check
        )

        # 5. Predict probabilities
        p_accept, p_reject = self.predictor.predict_probabilities(X, bundle)

        # 6. Apply threshold policy via orchestration linkage
        decision, confidence, prof_ver, _ = self.policy.evaluate_decision(p_accept, profile=custom_thresholds, model_record=bundle)

        # 7. Compute latency
        dt_ms = (time.perf_counter() - t0) * 1000.0

        # 8. Return typed DTO
        if PYDANTIC_AVAILABLE:
            return Layer3Prediction(
                manuscript_id=ms_id,
                accept_probability=p_accept,
                desk_reject_probability=p_reject,
                decision=decision,
                confidence_level=confidence,
                model_id=bundle.get("model_id", 1),
                model_version=str(bundle.get("model_version", "v1.0")),
                classifier=str(bundle.get("model_name", "Random_Forest")),
                feature_schema_version=schema_ver,
                calibration_method=str(bundle.get("calibration_method", "none")),
                threshold_profile_version=prof_ver,
                inference_time_ms=dt_ms,
                feature_vector=fv_dict
            )
        else:
            return Layer3Prediction(
                manuscript_id=ms_id,
                accept_probability=p_accept,
                desk_reject_probability=p_reject,
                decision=decision,
                confidence_level=confidence,
                model_id=bundle.get("model_id", 1),
                model_version=str(bundle.get("model_version", "v1.0")),
                classifier=str(bundle.get("model_name", "Random_Forest")),
                feature_schema_version=schema_ver,
                calibration_method=str(bundle.get("calibration_method", "none")),
                threshold_profile_version=prof_ver,
                inference_time_ms=dt_ms,
                feature_vector=fv_dict
            )
