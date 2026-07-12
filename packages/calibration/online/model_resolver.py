"""
model_resolver.py — Active Layer 3 Model & Artifact Resolution
Resolves the active production model bundle strictly ensuring:
1. Exactly one active model (raises MultipleActiveModelsError if > 1).
2. Environment-based fallback (NoActiveModelError in production if DB/model missing; local fallback allowed in development).
3. Exposes active model metadata (including threshold_profile_id) for downstream policy resolution.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..common.constants import (
    BEST_PIPELINE_PATH,
    FEATURE_SCHEMA_PATH,
    METADATA_PATH,
    CHECKSUMS_PATH,
    DEFAULT_MODEL_VERSION
)
from ..common.exceptions import (
    ModelLoadError,
    NoActiveModelError,
    MultipleActiveModelsError,
    ConfigurationError
)

try:
    from packages.database.config_repository import ConfigRepository, _project_root
    from apps.api.config import SessionLocal, TrainedModel, ModelRegistry
    DB_AVAILABLE = True
except ImportError:
    try:
        from apps.api.config import SessionLocal, TrainedModel, ModelRegistry
        _project_root = str(Path(__file__).resolve().parents[3])
        DB_AVAILABLE = True
    except ImportError:
        DB_AVAILABLE = False
        SessionLocal = None
        TrainedModel = None
        ModelRegistry = None
        _project_root = str(Path(__file__).resolve().parents[3])


class ModelResolver:
    """Resolves active model bundle paths and identifiers for Layer 3 online inference."""

    def __init__(self, db_session: Optional[Any] = None, env: Optional[str] = None):
        self.db_session = db_session
        self.env = (env or os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development"))).lower()

    def _get_session(self):
        if self.db_session:
            return self.db_session, False
        if SessionLocal:
            try:
                return SessionLocal(), True
            except Exception:
                pass
        return None, False

    def resolve_active_model_record(self) -> Dict[str, Any]:
        """Resolves exactly one active model database record metadata.

        Enforces:
        - Exactly 1 active row (`is_active = True`).
        - If > 1, raises `MultipleActiveModelsError`.
        - If 0 in production environment, raises `NoActiveModelError`.
        - If 0 in development environment, returns local fallback descriptor.

        Returns:
            Dict[str, Any]: Dictionary containing model record metadata (`id`, `model_version`, `threshold_profile_id`, `artifact_path`, etc.)
        """
        session, close_needed = self._get_session()
        try:
            if session and TrainedModel:
                active_tms = session.query(TrainedModel).filter(TrainedModel.is_active == True).all()
                if len(active_tms) > 1:
                    raise MultipleActiveModelsError(
                        f"[ModelResolver Error] Found {len(active_tms)} active models in trained_models "
                        f"table (IDs: {[m.id for m in active_tms]}). Exactly one active model must be configured."
                    )
                if len(active_tms) == 1:
                    tm = active_tms[0]
                    art_path = tm.artifact_path or ""
                    if art_path and not os.path.isabs(art_path):
                        art_path = os.path.join(_project_root, art_path)
                    
                    scaler_p = tm.scaler_path
                    if scaler_p and not os.path.isabs(scaler_p):
                        scaler_p = os.path.join(_project_root, scaler_p)

                    metrics_p = tm.metrics_path
                    if metrics_p and not os.path.isabs(metrics_p):
                        metrics_p = os.path.join(_project_root, metrics_p)

                    model_name = "Random_Forest"
                    if hasattr(tm, "model") and tm.model and tm.model.model_name:
                        model_name = tm.model.model_name

                    return {
                        "id": tm.id,
                        "model_version": tm.model_version or DEFAULT_MODEL_VERSION,
                        "threshold_profile_id": tm.threshold_profile_id,
                        "experiment_id": tm.experiment_id,
                        "model_id": getattr(tm, "model_id", tm.id),
                        "artifact_path": art_path,
                        "scaler_path": scaler_p,
                        "metrics_path": metrics_p,
                        "model_name": model_name,
                        "source": "trained_models"
                    }

            if session and ModelRegistry:
                active_mrs = session.query(ModelRegistry).filter(
                    ModelRegistry.is_active == True,
                    ModelRegistry.model_type.ilike("%classifier%")
                ).all()
                if len(active_mrs) > 1:
                    raise MultipleActiveModelsError(
                        f"[ModelResolver Error] Found {len(active_mrs)} active classifiers in model_registry "
                        f"table. Exactly one active model must be configured."
                    )
                if len(active_mrs) == 1:
                    mr = active_mrs[0]
                    return {
                        "id": mr.id,
                        "model_version": mr.version or DEFAULT_MODEL_VERSION,
                        "threshold_profile_id": None,
                        "experiment_id": 1,
                        "model_id": mr.id,
                        "artifact_path": str(BEST_PIPELINE_PATH),
                        "scaler_path": None,
                        "metrics_path": str(METADATA_PATH),
                        "model_name": mr.model_name or "ML Classifier",
                        "source": "model_registry"
                    }

        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

        # If DB missing or 0 rows found: check environment
        if self.env in ("production", "prod"):
            raise NoActiveModelError(
                f"[ModelResolver Error] No active model found in database (is_active=True) "
                f"and environment is '{self.env}'. Local fallback is forbidden in production."
            )

        # Development / test environment explicit local fallback
        if BEST_PIPELINE_PATH.exists():
            return {
                "id": 1,
                "model_version": DEFAULT_MODEL_VERSION,
                "threshold_profile_id": 2,  # Active Layer 3 default policy id = 2
                "experiment_id": 1,
                "model_id": 1,
                "artifact_path": str(BEST_PIPELINE_PATH),
                "scaler_path": None,
                "metrics_path": str(METADATA_PATH),
                "model_name": "Random_Forest",
                "source": "local_filesystem"
            }

        raise ModelLoadError(
            f"[ModelResolver Error] Could not resolve any active Layer 3 model artifact from database "
            f"or local fallback directory: {BEST_PIPELINE_PATH}"
        )

    def resolve_active_bundle(self) -> Dict[str, Any]:
        """Resolves the currently active Layer 3 classifier model bundle descriptors.

        Returns:
            Dict[str, Any]: Bundle descriptor containing artifact_path, schema_path, metadata_path, model_id, and version.
        """
        record = self.resolve_active_model_record()
        art_path = Path(record["artifact_path"]).resolve()
        parent_dir = art_path.parent if art_path.exists() else BEST_PIPELINE_PATH.parent

        schema_p = parent_dir / "feature_schema.json"
        meta_p = parent_dir / "metadata.json"
        chk_p = parent_dir / "checksums.json"

        if not schema_p.exists():
            schema_p = FEATURE_SCHEMA_PATH
        if not meta_p.exists() and record.get("metrics_path") and os.path.exists(record["metrics_path"]):
            meta_p = Path(record["metrics_path"]).resolve()
        elif not meta_p.exists():
            meta_p = METADATA_PATH
        if not chk_p.exists():
            chk_p = CHECKSUMS_PATH

        return {
            "model_id": record["model_id"],
            "model_version": record["model_version"],
            "model_name": record["model_name"],
            "threshold_profile_id": record.get("threshold_profile_id"),
            "artifact_path": art_path if art_path.exists() else BEST_PIPELINE_PATH,
            "schema_path": schema_p,
            "metadata_path": meta_p,
            "checksums_path": chk_p,
            "source": record["source"]
        }
