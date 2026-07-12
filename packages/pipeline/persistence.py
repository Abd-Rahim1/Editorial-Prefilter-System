"""
persistence.py — Shared Database Persistence Operations
"""

import json
from typing import Any
from database.connection import get_connection
from database.save import (
    save_sections,
    save_editorial_features,
    save_rule_checks,
    save_model_run,
    save_prediction,
    save_explanation
)

def create_initial_manuscript(filename: str, title: str, user_id: int = None) -> int:
    """Inserts a manuscript with status='pending' and returns the inserted ID."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        query = """
        INSERT INTO public.manuscripts (filename, title, status, user_id)
        VALUES (%s, %s, 'pending', %s)
        RETURNING id;
        """
        cur.execute(query, (filename, title, user_id))
        m_id = cur.fetchone()[0]
        conn.commit()
        return m_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def save_pipeline_outputs(m_id: int, result: Any, conn=None) -> None:
    """
    Persists all stages of the pipeline results for manuscript m_id.
    """
    # 1. Update metadata in manuscripts table
    metadata = result.layer1_metadata
    num_pages = metadata.get("num_pages", metadata.get("page_count")) or None
    total_word_count = metadata.get("total_word_count") or None
    title = metadata.get("title") or result.title
    
    local_conn = conn or get_connection()
    cur = local_conn.cursor()
    try:
        cur.execute(
            """
            UPDATE public.manuscripts
            SET num_pages = %s, total_word_count = %s, title = %s, status = 'reviewed'
            WHERE id = %s;
            """,
            (num_pages, total_word_count, title, m_id)
        )
        
        # 2. Save sections, rules, and editorial features using packages/database/save.py functions
        save_sections(m_id, result.sections)
        save_editorial_features(m_id, result.editorial_features)
        save_rule_checks(m_id, result.layer1_violations)
        
        # 3. Save Model Run
        l3 = result.layer3_prediction
        run_id = save_model_run(
            manuscript_id=m_id,
            model_version=str(l3.model_version),
            prompt_version=result.layer2_scores.get("prompt_version", "v5"),
            prompt_text=result.layer2_scores.get("prompt_text", ""),
            input_payload=result.layer2_scores.get("input_payload", {}),
            raw_output=result.layer2_scores.get("raw_output", ""),
            parsed_output=result.layer2_scores,
            execution_time_ms=l3.inference_time_ms,
            threshold_profile_id=int(l3.threshold_profile_version) if str(l3.threshold_profile_version).isdigit() else None
        )
        
        # 4. Save Prediction
        conf_val = l3.accept_probability if "PEER" in l3.decision.upper() else l3.desk_reject_probability
        save_prediction(
            model_run_id=run_id,
            predicted_label=0 if "REJECT" in l3.decision.upper() else 1,
            desk_reject_probability=l3.desk_reject_probability,
            confidence=conf_val
        )
        
        # 5. Save Explanation
        save_explanation(
            model_run_id=run_id,
            explanation_text=result.report_json["natural_language_explanation"].get("text", ""),
            detected_issues=[getattr(v, "description", str(v)) for v in result.layer1_violations],
            evidence_spans=result.layer2_scores.get("evidence_spans", [])
        )
        
        # 6. Save Report
        cur.execute(
            """
            INSERT INTO public.reports (manuscript_id, report_json)
            VALUES (%s, %s)
            ON CONFLICT (manuscript_id) DO UPDATE SET report_json = EXCLUDED.report_json;
            """,
            (m_id, json.dumps(result.report_json))
        )
        
        if conn is None:
            local_conn.commit()
    except Exception:
        if conn is None:
            local_conn.rollback()
        raise
    finally:
        cur.close()
        if conn is None:
            local_conn.close()
