"""
pipeline_repository.py — Pipeline Repository
Manages all database read queries for manuscripts, status, predictions, explanations, and reports.
Consolidates direct SQL connection strategies into a clean boundary.
"""

import json
from typing import Dict, Any, Optional, List
from database.connection import get_connection
from database.save import get_manuscript_complete_history

class PipelineRepository:
    """Consolidates read operations for manuscripts and pipeline runs."""

    @staticmethod
    def get_manuscript_status(manuscript_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves manuscript status and stage progress from DB."""
        history = get_manuscript_complete_history(manuscript_id)
        if not history:
            return None
            
        return {
            "status": history.get("status", "unknown"),
            "stage_progress": history.get("stage_progress", {
                "stage_0": "completed",
                "stage_1": "completed",
                "stage_2": "completed",
                "stage_3": "completed",
                "stage_4": "completed"
            })
        }

    @staticmethod
    def get_prediction(manuscript_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves raw classification prediction records from DB."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            query = """
            SELECT p.id, p.model_run_id, p.predicted_label, p.desk_reject_probability, p.confidence
            FROM public.predictions p
            JOIN public.model_runs mr ON p.model_run_id = mr.id
            WHERE mr.manuscript_id = %s
            ORDER BY mr.id DESC
            LIMIT 1;
            """
            cur.execute(query, (manuscript_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "model_run_id": row[1],
                "predicted_label": row[2],
                "desk_reject_probability": float(row[3]) if row[3] is not None else None,
                "confidence": float(row[4]) if row[4] is not None else None
            }
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_explanation(manuscript_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves explanation audit records from DB."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            query = """
            SELECT e.id, e.model_run_id, e.explanation_text, e.detected_issues, e.evidence_spans
            FROM public.explanations e
            JOIN public.model_runs mr ON e.model_run_id = mr.id
            WHERE mr.manuscript_id = %s
            ORDER BY mr.id DESC
            LIMIT 1;
            """
            cur.execute(query, (manuscript_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "model_run_id": row[1],
                "explanation_text": row[2],
                "detected_issues": row[3],
                "evidence_spans": row[4]
            }
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_report(manuscript_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the pre-generated master report from reports table."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            query = "SELECT report_json FROM public.reports WHERE manuscript_id = %s LIMIT 1;"
            cur.execute(query, (manuscript_id,))
            row = cur.fetchone()
            if row and row[0]:
                raw_report = row[0]
                if isinstance(raw_report, str):
                    return json.loads(raw_report)
                elif isinstance(raw_report, dict):
                    return raw_report
            return None
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def list_editor_manuscripts(user_id: int, is_admin: bool) -> List[Dict[str, Any]]:
        """Lists manuscripts, filtering by editor ownership unless user is admin."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            query = """
            SELECT
                m.id,
                m.filename,
                m.title,
                m.upload_date,
                m.status,
                m.num_pages,
                m.total_word_count,
                COALESCE(mr.parsed_output, '{}'::jsonb) AS qwen_scores,
                mr.parsed_output->> 'final_integrity_decision' AS final_integrity_decision,
                mr.parsed_output->> 'recommendation' AS recommendation
            FROM public.manuscripts m
            LEFT JOIN LATERAL (
                SELECT parsed_output
                FROM public.model_runs
                WHERE manuscript_id = m.id
                ORDER BY id DESC
                LIMIT 1
            ) mr ON true
            """
            
            # Admins see everything, editors see only their own uploads
            if not is_admin:
                query += " WHERE m.user_id = %s"
                query += " ORDER BY m.upload_date DESC;"
                cur.execute(query, (user_id,))
            else:
                query += " ORDER BY m.upload_date DESC;"
                cur.execute(query)
                
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
        finally:
            cur.close()
            conn.close()
