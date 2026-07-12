import os
import logging
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks

from pipeline.orchestrator import PipelineOrchestrator
from pipeline.exceptions import PipelineError
from database.save import update_manuscript_status
from database.connection import get_connection

logger = logging.getLogger("PipelineService")

PIPELINE_PROGRESS_TRACKER: Dict[str, Dict[str, str]] = {}


def _log_activity(
    manuscript_id: int,
    action: str,
    details: str = "",
    user_id: Optional[int] = None,
) -> None:
    """
    Insert one row into public.audit_logs.
    Silently swallows errors so that a logging failure never kills the pipeline.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO public.audit_logs (user_id, manuscript_id, action, details, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING;
                """,
                (user_id, manuscript_id, action, details),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
    except Exception as exc:
        logger.warning(f"Activity log failed for manuscript {manuscript_id}: {exc}")


class PipelineService:

    @staticmethod
    def initialize_progress(manuscript_id: int) -> None:
        m_str = str(manuscript_id)
        PIPELINE_PROGRESS_TRACKER[m_str] = {
            "stage_0": "active",
            "stage_1": "pending",
            "stage_2": "pending",
            "stage_3": "pending",
            "stage_4": "pending",
        }

    @staticmethod
    def get_in_memory_progress(manuscript_id: int) -> Optional[Dict[str, str]]:
        return PIPELINE_PROGRESS_TRACKER.get(str(manuscript_id))

    @staticmethod
    def clear_in_memory_progress(manuscript_id: int) -> None:
        PIPELINE_PROGRESS_TRACKER.pop(str(manuscript_id), None)

    @classmethod
    def start_background_evaluation(
        cls,
        background_tasks: BackgroundTasks,
        manuscript_id: int,
        temp_pdf_path: str,
        conference: str,
        mode: str,
        user_id: Optional[int] = None
    ) -> None:
        cls.initialize_progress(manuscript_id)

        # Log upload event immediately (manuscript row already exists at this point)
        _log_activity(
            manuscript_id=manuscript_id,
            action="manuscript_uploaded",
            details="Manuscript uploaded and queued for four-layer evaluation.",
            user_id=user_id,
        )

        def progress_cb(stage: str, status: str):
            m_str = str(manuscript_id)
            if m_str in PIPELINE_PROGRESS_TRACKER:
                PIPELINE_PROGRESS_TRACKER[m_str][stage] = status

            # Map stage key → human-readable activity event
            if status == "completed":
                _STAGE_ACTIONS = {
                    "stage_0": ("layer1_parsing_completed",
                                "Layer 1 — Text extraction and metadata parsing completed."),
                    "stage_1": ("layer1_rules_completed",
                                "Layer 1 — Deterministic editorial rule checks completed."),
                    "stage_2": ("layer2_completed",
                                "Layer 2 — Qwen semantic evaluation completed."),
                    "stage_3": ("layer3_completed",
                                "Layer 3 — Probabilistic recommendation computed."),
                    "stage_4": ("layer4_completed",
                                "Layer 4 — SHAP-based explanation generated."),
                }
                if stage in _STAGE_ACTIONS:
                    act, desc = _STAGE_ACTIONS[stage]
                    _log_activity(manuscript_id, act, desc, user_id)

        def _execute_worker():
            m_str = str(manuscript_id)
            try:
                update_manuscript_status(manuscript_id, "processing")

                PipelineOrchestrator.run(
                    pdf_path=temp_pdf_path,
                    conference=conference,
                    mode=mode,
                    persist=True,
                    manuscript_id=m_str,
                    user_id=user_id,
                    progress_callback=progress_cb
                )

                update_manuscript_status(manuscript_id, "reviewed")
                _log_activity(
                    manuscript_id=manuscript_id,
                    action="evaluation_completed",
                    details="Four-layer evaluation pipeline completed successfully.",
                    user_id=user_id,
                )

            except Exception as exc:
                logger.error(f"Background task failed for manuscript {manuscript_id}: {exc}")
                update_manuscript_status(manuscript_id, "failed")
                _log_activity(
                    manuscript_id=manuscript_id,
                    action="evaluation_failed",
                    details=f"Evaluation pipeline failed: {str(exc)[:200]}",
                    user_id=user_id,
                )
                if m_str in PIPELINE_PROGRESS_TRACKER:
                    for stage in ["stage_0", "stage_1", "stage_2", "stage_3", "stage_4"]:
                        if PIPELINE_PROGRESS_TRACKER[m_str][stage] == "active":
                            PIPELINE_PROGRESS_TRACKER[m_str][stage] = "failed"
            finally:
                if os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except Exception:
                        pass
                cls.clear_in_memory_progress(manuscript_id)

        background_tasks.add_task(_execute_worker)
