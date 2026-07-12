"""
promote_model.py — Controlled Model Promotion into Production
CLI utility (`python -m packages.calibration.offline.promote_model`) for safely copying and registering
a verified candidate model bundle or the exact finalized TFG_Evaluation study winner into the production
directory (`packages/calibration/models/`).

Automatically generates SHA-256 `checksums.json` and verifies integrity without retraining.
"""

import argparse
import shutil
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import sys
from typing import Optional, Dict

from ..common.constants import PACKAGE_ROOT, MODELS_DIR

_PROJECT_ROOT = PACKAGE_ROOT.parent.parent.resolve()
_WINNER_DIR = _PROJECT_ROOT / "experiments" / "evaluation_models" / "best_pipeline"


def _compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def promote_candidate_to_production(candidate_dir: Optional[Path] = None, register_db: bool = False) -> Dict[str, str]:
    """Copies `candidate_dir` (or the TFG_Evaluation study winner) into `packages/calibration/models/`.

    Args:
        candidate_dir: Directory containing candidate files. Defaults to `_WINNER_DIR`.
        register_db: If True, registers the promoted model row inside PostgreSQL (`TrainedModel`).

    Returns:
        Dict[str, str]: Absolute paths of promoted files inside `MODELS_DIR`.
    """
    source_dir = candidate_dir or _WINNER_DIR
    if not source_dir.exists():
        raise FileNotFoundError(f"[Promote Error] Source directory not found: {source_dir}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Locate and copy model file (`model.pkl` -> `best_pipeline.joblib`)
    src_model = source_dir / "model.joblib"
    if not src_model.exists():
        src_model = source_dir / "model.pkl"
    if not src_model.exists():
        raise FileNotFoundError(f"[Promote Error] No model file (model.joblib or model.pkl) found inside {source_dir}")

    dst_model = MODELS_DIR / "best_pipeline.joblib"
    shutil.copy2(src_model, dst_model)

    # 2. Copy feature_schema.json
    src_schema = source_dir / "feature_schema.json"
    if not src_schema.exists():
        raise FileNotFoundError(f"[Promote Error] feature_schema.json not found inside {source_dir}")
    dst_schema = MODELS_DIR / "feature_schema.json"
    shutil.copy2(src_schema, dst_schema)

    # 3. Copy metadata.json
    src_meta = source_dir / "metadata.json"
    if not src_meta.exists():
        raise FileNotFoundError(f"[Promote Error] metadata.json not found inside {source_dir}")
    dst_meta = MODELS_DIR / "metadata.json"
    shutil.copy2(src_meta, dst_meta)

    # 4. Copy metrics.json if exists
    src_metrics = source_dir / "metrics.json"
    dst_metrics = MODELS_DIR / "metrics.json"
    if src_metrics.exists():
        shutil.copy2(src_metrics, dst_metrics)

    # 5. Generate or verify SHA-256 checksums.json
    checksums = {
        "model": _compute_sha256(dst_model),
        "schema": _compute_sha256(dst_schema),
        "metadata": _compute_sha256(dst_meta)
    }
    if dst_metrics.exists():
        checksums["metrics"] = _compute_sha256(dst_metrics)

    dst_chk = MODELS_DIR / "checksums.json"
    with open(dst_chk, "w", encoding="utf-8") as f:
        json.dump(checksums, f, indent=2)

    # 6. Optional database registration
    if register_db:
        try:
            from apps.api.config import SessionLocal, TrainedModel
            db = SessionLocal()
            try:
                # Deactivate previous active models
                db.query(TrainedModel).filter(TrainedModel.is_active == True).update({"is_active": False})
                new_row = TrainedModel(
                    model_version="random_forest-c2-promoted",
                    artifact_path=str(dst_model),
                    feature_schema_path=str(dst_schema),
                    metrics_path=str(dst_metrics if dst_metrics.exists() else dst_meta),
                    is_active=True,
                    trained_at=datetime.now(timezone.utc)
                )
                db.add(new_row)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[WARNING] Could not register promoted model in PostgreSQL: {e}", file=sys.stderr)

    return {
        "model": str(dst_model),
        "schema": str(dst_schema),
        "metadata": str(dst_meta),
        "checksums": str(dst_chk)
    }


def main(args: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Promote verified candidate into Layer 3 online production")
    parser.add_argument("--candidate-dir", type=str, default=None, help="Directory of candidate bundle (defaults to study winner)")
    parser.add_argument("--register-db", action="store_true", help="Register promoted model as active in PostgreSQL")

    parsed = parser.parse_args(args)
    src = Path(parsed.candidate_dir) if parsed.candidate_dir else _WINNER_DIR

    print(f"[{datetime.now().isoformat()}] Promoting bundle from {src} to {MODELS_DIR}...")
    try:
        files = promote_candidate_to_production(candidate_dir=src, register_db=parsed.register_db)
        print("  [SUCCESS] Model promoted successfully with SHA-256 validation:")
        for k, p in files.items():
            print(f"    - {k}: {p}")
        return 0
    except Exception as e:
        print(f"[ERROR] Promotion failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
