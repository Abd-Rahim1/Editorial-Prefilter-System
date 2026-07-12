"""
db_metadata.py — Read-Only Database Metadata Helper (Chapter 5 TFG).

Provides lightweight, read-only query functions that enrich MLflow experiment
runs with contextual metadata from the production PostgreSQL database (models
and prompt_templates tables).

Design principles:
  - STRICTLY READ-ONLY: only SELECT queries, no INSERT/UPDATE/DELETE.
  - NEVER controls experiment execution (dataset, feature set, classifier,
    calibration). Those remain owned by CLI arguments and experiments/config.py.
  - Gracefully returns empty dicts when the DB is unavailable so experiments
    can proceed without a live database connection.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_DIR = PROJECT_ROOT / "apps" / "api"

# Internal helpers

def _get_session():
    """
    Returns a SQLAlchemy SessionLocal instance from the production API config.
    Raises ImportError if the API layer cannot be imported.
    """
    if str(API_DIR) not in sys.path:
        sys.path.insert(0, str(API_DIR))
    from config import SessionLocal  # noqa: PLC0415  (local import by design)
    return SessionLocal()


# Public read-only query functions

def fetch_llm_metadata(llm_model_name: str) -> Dict[str, Any]:
    """
    Queries the ``models`` table for an LLM entry matching *llm_model_name*.

    Returns a dict with the following keys (values may be None if not stored):
      - llm_model_name   (str)  : as queried
      - llm_provider     (str)  : e.g. "Ollama", "OpenAI"
      - llm_version      (str)  : model version tag
      - llm_model_type   (str)  : e.g. "LLM Scorer"
      - llm_context_length (int): context window in tokens
      - llm_parameters   (int)  : parameter count
      - llm_latency_ms   (int)  : average inference latency

    Returns an empty dict if the model name is not found or the DB is
    unreachable.  Callers should treat missing keys gracefully.
    """
    if not llm_model_name:
        return {}

    try:
        if str(API_DIR) not in sys.path:
            sys.path.insert(0, str(API_DIR))
        from config import SessionLocal, ModelRegistry  # noqa: PLC0415

        db = SessionLocal()
        try:
            # Case-insensitive substring match so "qwen3:4b" and "Qwen3:4b" both work
            record = (
                db.query(ModelRegistry)
                .filter(ModelRegistry.model_name.ilike(f"%{llm_model_name}%"))
                .first()
            )
            if record is None:
                return {}
            return {
                "llm_model_name":    record.model_name,
                "llm_provider":      record.provider,
                "llm_version":       record.version,
                "llm_model_type":    record.model_type,
                "llm_context_length": record.context_length,
                "llm_parameters":    record.parameters,
                "llm_latency_ms":    record.latency_ms,
            }
        finally:
            db.close()

    except Exception as exc:  # noqa: BLE001
        # DB unavailable or config not importable — degrade gracefully
        print(
            f"[db_metadata] WARNING: Could not fetch LLM metadata for "
            f"'{llm_model_name}': {exc}"
        )
        return {}


def fetch_prompt_metadata(prompt_version: str) -> Dict[str, Any]:
    """
    Queries the ``prompt_templates`` table for a record matching *prompt_version*.

    Returns a dict with the following keys:
      - prompt_id          (int) : database primary key
      - prompt_name        (str) : human-readable template name
      - prompt_version     (str) : as queried
      - prompt_description (str) : first 200 chars of system_prompt as a
                                   human-readable summary (truncated for MLflow)

    Falls back to the currently active prompt template if the exact version is
    not found.  Returns an empty dict if the DB is unreachable.
    """
    try:
        if str(API_DIR) not in sys.path:
            sys.path.insert(0, str(API_DIR))
        from config import SessionLocal, PromptTemplate  # noqa: PLC0415

        db = SessionLocal()
        try:
            record: Optional[Any] = None

            if prompt_version:
                record = (
                    db.query(PromptTemplate)
                    .filter(PromptTemplate.version == prompt_version)
                    .first()
                )

            if record is None:
                # Fall back to active prompt
                record = (
                    db.query(PromptTemplate)
                    .filter(PromptTemplate.is_active == True)  # noqa: E712
                    .first()
                )

            if record is None:
                return {}

            # Truncate system_prompt to 200 chars so it fits in an MLflow tag
            sys_prompt_summary = ""
            if record.system_prompt:
                sys_prompt_summary = record.system_prompt[:200].replace("\n", " ").strip()
                if len(record.system_prompt) > 200:
                    sys_prompt_summary += "..."

            return {
                "prompt_id":          record.id,
                "prompt_name":        record.name,
                "prompt_version":     record.version,
                "prompt_description": sys_prompt_summary,
            }
        finally:
            db.close()

    except Exception as exc:  # noqa: BLE001
        print(
            f"[db_metadata] WARNING: Could not fetch prompt metadata for "
            f"version '{prompt_version}': {exc}"
        )
        return {}
