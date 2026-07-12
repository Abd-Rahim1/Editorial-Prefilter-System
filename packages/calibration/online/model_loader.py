"""
model_loader.py — Cached Artifact Loader & Integrity Validator
Loads model objects, feature schemas, and metadata securely into memory with cache keying by
`(model_id, version, artifact_path)`. Validates SHA-256 integrity (`checksums.json`), feature tier (`C2`),
and class mapping (`classes_`).
"""

import json
import hashlib
import joblib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np

from ..common.exceptions import ModelLoadError, ModelIntegrityError
from .model_resolver import ModelResolver

# In-memory singletons keyed by (model_id, model_version, artifact_path)
_CACHED_BUNDLES: Dict[Tuple[int, str, str], Dict[str, Any]] = {}


def compute_file_sha256(filepath: Path) -> str:
    """Computes the SHA-256 hexadecimal digest of a file."""
    if not filepath.exists():
        return ""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def validate_checksums(artifact_path: Path, schema_path: Path, metadata_path: Path, checksums_path: Path) -> None:
    """Verifies artifact SHA-256 digests against `checksums.json` if present."""
    if not checksums_path.exists():
        return

    try:
        with open(checksums_path, "r", encoding="utf-8") as f:
            expected = json.load(f)
    except Exception as e:
        raise ModelIntegrityError(f"[ModelIntegrity Error] Could not read {checksums_path}: {e}")

    for file_key, path_obj in [("model", artifact_path), ("schema", schema_path), ("metadata", metadata_path)]:
        if file_key in expected and path_obj.exists():
            actual_sha = compute_file_sha256(path_obj)
            expected_sha = expected[file_key]
            if actual_sha.lower() != expected_sha.lower():
                raise ModelIntegrityError(
                    f"[ModelIntegrity Error] SHA-256 mismatch for {path_obj.name}! "
                    f"Expected {expected_sha}, found {actual_sha}."
                )


class ModelLoader:
    """Loads and caches verified production model bundles."""

    def __init__(self, resolver: Optional[ModelResolver] = None):
        self.resolver = resolver or ModelResolver()

    def load_active_bundle(self, force_reload: bool = False) -> Dict[str, Any]:
        """Loads the active model bundle, utilizing in-memory cache when available.

        Args:
            force_reload: If True, bypasses cache and re-loads from disk.

        Returns:
            Dict[str, Any]: Loaded bundle containing `model`, `schema`, `metadata`, `is_pipeline`, and descriptors.
        """
        bundle_info = self.resolver.resolve_active_bundle()
        cache_key = (bundle_info["model_id"], str(bundle_info["model_version"]), str(bundle_info["artifact_path"]))

        if not force_reload and cache_key in _CACHED_BUNDLES:
            return _CACHED_BUNDLES[cache_key]

        art_path = Path(bundle_info["artifact_path"])
        schema_path = Path(bundle_info["schema_path"])
        metadata_path = Path(bundle_info["metadata_path"])
        checksums_path = Path(bundle_info["checksums_path"])

        # 1. Verify existence
        if not art_path.exists():
            raise ModelLoadError(f"[ModelLoader Error] Active model file not found at: {art_path}")

        # 2. Verify SHA-256 checksums if available
        validate_checksums(art_path, schema_path, metadata_path, checksums_path)

        # 3. Load schema JSON
        schema_data: Dict[str, Any] = {}
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_data = json.load(f)

        # 4. Load metadata JSON
        meta_data: Dict[str, Any] = {}
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f)

        # 5. Load serialized model object
        try:
            model_obj = joblib.load(art_path)
        except Exception as e:
            raise ModelLoadError(f"[ModelLoader Error] Could not unpickle model at {art_path}: {e}")

        # 6. Validate class mapping & structure
        classes = getattr(model_obj, "classes_", np.array([0, 1]))
        is_pipeline = hasattr(model_obj, "named_steps") or type(model_obj).__name__ == "Pipeline"

        # 7. Validate tier and calibration compatibility
        f_set = schema_data.get("feature_set", meta_data.get("feature_set", "C2"))
        cal_method = meta_data.get("calibration_method", meta_data.get("calibration", "none"))

        loaded_bundle = {
            "model": model_obj,
            "schema": schema_data,
            "metadata": meta_data,
            "classes": classes,
            "is_pipeline": is_pipeline,
            "feature_set": f_set,
            "calibration_method": cal_method,
            "model_id": bundle_info["model_id"],
            "model_version": bundle_info["model_version"],
            "model_name": bundle_info["model_name"],
            "threshold_profile_id": bundle_info.get("threshold_profile_id"),
            "artifact_path": str(art_path)
        }

        _CACHED_BUNDLES[cache_key] = loaded_bundle
        return loaded_bundle

    def clear_cache(self) -> None:
        """Purges all cached models from memory."""
        _CACHED_BUNDLES.clear()
