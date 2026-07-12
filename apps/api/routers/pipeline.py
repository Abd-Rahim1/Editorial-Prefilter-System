import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from config import SessionLocal, SystemSettings
from database.connection import get_connection
from database.save import (
    get_manuscript_complete_history,
)

from auth import TokenData, get_current_user
from services.pipeline_service import PipelineService
from repositories.pipeline_repository import PipelineRepository
from pipeline.persistence import create_initial_manuscript

router = APIRouter(prefix="/api", tags=["Pipelines"])
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_manuscripts")
os.makedirs(TEMP_DIR, exist_ok=True)


def format_clean_title(filename: str) -> str:
    if not filename:
        return "Untitled Manuscript"
    base = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\_-]+', ' ', base).strip()
    if not cleaned:
        return "Untitled Manuscript"
    return " ".join(word.capitalize() for word in cleaned.split())


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "storage", "reports")


@router.post("/v1/pipelines/evaluate")
async def evaluate_pipeline_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    version: str = Form("v5"),
    mode: str = Form("real"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Accepts one PDF manuscript and schedules sequential 4-layer pre-filter pipeline run.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    clean_version = "v5"
    if version:
        match = re.search(r"(v[1-5])", str(version).lower())
        if match:
            clean_version = match.group(1)

    fd, temp_file_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    clean_title = format_clean_title(file.filename)
    user_id = getattr(current_user, "id", None)
    
    # Save manuscript initial record to DB
    m_id = create_initial_manuscript(file.filename, clean_title, user_id=user_id)
    
    # Start the background task via PipelineService
    PipelineService.start_background_evaluation(
        background_tasks=background_tasks,
        manuscript_id=m_id,
        temp_pdf_path=temp_file_path,
        conference="iclr_2017",
        mode=mode,
        user_id=user_id
    )

    return {
        "success": True,
        "manuscript_id": m_id,
        "status": "processing",
        "message": "Processing started",
        "stage_progress": PipelineService.get_in_memory_progress(m_id) or {
            "stage_0": "active", "stage_1": "pending", "stage_2": "pending", "stage_3": "pending", "stage_4": "pending"
        }
    }


@router.post("/ingest")
async def ingest_manuscript(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    version: str = Form("v5"),
    mode: str = Form("real"),
    current_user: TokenData = Depends(get_current_user)
):
    """Alias for /v1/pipelines/evaluate."""
    return await evaluate_pipeline_file(background_tasks, file, version, mode, current_user)


@router.get("/v1/pipelines/status/{manuscript_id}")
def get_pipeline_status(manuscript_id: int, current_user: TokenData = Depends(get_current_user)):
    """Retrieves current in-memory progress or queries the database status state."""
    progress = PipelineService.get_in_memory_progress(manuscript_id)
    if progress:
        return {
            "success": True,
            "manuscript_id": manuscript_id,
            "status": "processing",
            "stage_progress": progress
        }
    status_info = PipelineRepository.get_manuscript_status(manuscript_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    return {
        "success": True,
        "manuscript_id": manuscript_id,
        "status": status_info["status"],
        "stage_progress": status_info["stage_progress"]
    }


@router.get("/manuscripts")
def list_manuscripts(current_user: TokenData = Depends(get_current_user)):
    """Retrieves list of manuscripts, filtering by owner editor unless user is admin."""
    is_admin = current_user.role == "admin"
    user_id = current_user.id
    try:
        manuscripts = PipelineRepository.list_editor_manuscripts(user_id, is_admin)
        return {"success": True, "manuscripts": manuscripts}
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to list manuscripts: {str(err)}")


@router.get("/manuscripts/{manuscript_id}")
def get_manuscript(manuscript_id: int, current_user: TokenData = Depends(get_current_user)):
    """Retrieves history payload, checking owner authorization."""
    manuscript = get_manuscript_complete_history(manuscript_id)
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    
    # Check authorization
    if current_user.role != "admin":
        m_user_id = manuscript.get("user_id")
        if m_user_id is not None and m_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this manuscript.")
            
    return {"success": True, "manuscript": manuscript}


@router.get("/manuscripts/{manuscript_id}/prediction")
def get_manuscript_prediction(manuscript_id: int, current_user: TokenData = Depends(get_current_user)):
    """Retrieves active raw prediction record."""
    manuscript = get_manuscript_complete_history(manuscript_id)
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    
    if current_user.role != "admin":
        m_user_id = manuscript.get("user_id")
        if m_user_id is not None and m_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this manuscript.")
            
    pred = PipelineRepository.get_prediction(manuscript_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"success": True, "prediction": pred}


@router.get("/manuscripts/{manuscript_id}/explanation")
def get_manuscript_explanation(manuscript_id: int, current_user: TokenData = Depends(get_current_user)):
    """Retrieves active raw explanation record."""
    manuscript = get_manuscript_complete_history(manuscript_id)
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")
    
    if current_user.role != "admin":
        m_user_id = manuscript.get("user_id")
        if m_user_id is not None and m_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this manuscript.")
            
    exp = PipelineRepository.get_explanation(manuscript_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Explanation not found")
    return {"success": True, "explanation": exp}


def _load_report_from_disk(filename: str) -> Optional[dict]:
    """Try to load a pre-generated Layer 4 report JSON from disk."""
    if not filename:
        return None
    stem = os.path.splitext(filename)[0]
    candidate = os.path.join(REPORTS_DIR, f"report_{stem}.json")
    if os.path.isfile(candidate):
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _assemble_report_from_db(manuscript_id: int) -> Optional[dict]:
    """
    Build a Layer 4 report envelope from the database when no disk file exists.
    Joins manuscripts → model_runs → predictions → explanations.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                m.id, m.filename, m.title,
                mr.id            AS model_run_id,
                mr.model_version,
                mr.parsed_output,
                mr.abstract_clarity,
                mr.structural_completeness,
                mr.methodological_strength,
                mr.experimental_strength,
                mr.argumentative_quality,
                mr.scope_alignment,
                mr.overall_quality,
                p.predicted_label,
                p.desk_reject_probability,
                p.confidence,
                e.explanation_text,
                e.detected_issues,
                e.evidence_spans
            FROM public.manuscripts m
            LEFT JOIN LATERAL (
                SELECT * FROM public.model_runs
                WHERE manuscript_id = m.id ORDER BY id DESC LIMIT 1
            ) mr ON true
            LEFT JOIN public.predictions p ON p.model_run_id = mr.id
            LEFT JOIN public.explanations e ON e.model_run_id = mr.id
            WHERE m.id = %s
            LIMIT 1;
            """,
            (manuscript_id,)
        )
        row = cur.fetchone()
        if not row:
            return None

        cols = [d[0] for d in cur.description]
        r = dict(zip(cols, row))

        # Fetch rule checks
        cur.execute(
            """
            SELECT rule_name, severity, passed, description
            FROM public.rule_checks WHERE manuscript_id = %s ORDER BY id;
            """,
            (manuscript_id,)
        )
        rule_rows = cur.fetchall()
        violations = [
            f"[{rw[1].upper()}] {rw[0]}: {rw[3]}"
            for rw in rule_rows if not rw[2]
        ]
        critical_count = sum(1 for rw in rule_rows if not rw[2] and rw[1] == "critical")

        # Parse semantic scores from parsed_output JSONB
        parsed = r.get("parsed_output") or {}
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except Exception:
                parsed = {}

        def _score(key: str, alt: str = "") -> float:
            v = r.get(key) or parsed.get(key) or (parsed.get(alt) if alt else None)
            try:
                return float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        prob = float(r.get("desk_reject_probability") or 0.0)
        predicted = bool(r.get("predicted_label") or False)
        verdict = "DESK_REJECT" if predicted or prob > 0.5 else "ACCEPT"

        detected_issues = r.get("detected_issues") or []
        if isinstance(detected_issues, str):
            try:
                detected_issues = json.loads(detected_issues)
            except Exception:
                detected_issues = [detected_issues]

        narrative = r.get("explanation_text") or ""

        conf_val = r.get("confidence")
        if conf_val is not None:
            try:
                conf_val = float(conf_val)
            except ValueError:
                pass

        return {
            "prediction": {
                "manuscript_id": str(manuscript_id),
                "predicted_class": int(predicted),
                "verdict": verdict,
                "desk_reject_probability": round(prob, 4),
                "layer3_verdict": verdict,
                "layer3_probability": round(prob, 4),
                "confidence": conf_val if conf_val is not None else 0.95,
                "model_version": r.get("model_version") or "random_forest_exp_C",
            },
            "feature_importance": {
                "shap_values": {},
                "ranked_features": [],
                "integrated_evidence": [],
                "shap_metadata": {"method": "db_fallback"},
            },
            "editorial_rules": {
                "violations": violations,
                "total_violations": len(violations),
                "critical_violations": critical_count,
                "layer1_violations": violations,
            },
            "semantic_scores": {
                "scores": {
                    "abstract_clarity":        _score("abstract_clarity", "abstract_clarity_score"),
                    "structural_completeness": _score("structural_completeness", "structure_validity_score"),
                    "methodological_strength": _score("methodological_strength", "methodological_strength_score"),
                    "experimental_strength":   _score("experimental_strength", "experimental_strength_score"),
                    "argumentative_quality":   _score("argumentative_quality", "argumentative_quality_score"),
                    "scope_alignment":         _score("scope_alignment", "scope_alignment_score"),
                    "overall_quality":         _score("overall_quality", "integrity_risk_score"),
                },
                "detected_issues": detected_issues,
                "evidence_spans": r.get("evidence_spans") or [],
            },
            "natural_language_explanation": narrative,
            "layer4_explanation": narrative,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error assembling report: {exc}")
    finally:
        cur.close()
        conn.close()


@router.get("/manuscripts/{manuscript_id}/report")
def get_manuscript_report(manuscript_id: int, current_user: TokenData = Depends(get_current_user)):
    """
    Return the canonical Layer 4 JSON report for a processed manuscript.
    """
    manuscript_meta = get_manuscript_complete_history(manuscript_id)
    if not manuscript_meta:
        raise HTTPException(status_code=404, detail="Manuscript record not found")

    if current_user.role != "admin":
        m_user_id = manuscript_meta.get("user_id")
        if m_user_id is not None and m_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this manuscript.")

    report = PipelineRepository.get_report(manuscript_id)
    if report:
        return report

    filename = manuscript_meta.get("filename")
    report = _load_report_from_disk(filename)
    if report:
        return report

    report = _assemble_report_from_db(manuscript_id)
    if report:
        return report

    raise HTTPException(
        status_code=404,
        detail=f"No Layer 4 report found for manuscript {manuscript_id}."
    )


@router.get("/manuscripts/{manuscript_id}/pdf")
def get_manuscript_pdf(manuscript_id: int, current_user: TokenData = Depends(get_current_user)):
    """Serves the original PDF file for download."""
    manuscript = get_manuscript_complete_history(manuscript_id)
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript record not found")

    if current_user.role != "admin":
        m_user_id = manuscript.get("user_id")
        if m_user_id is not None and m_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this manuscript.")

    filename = manuscript.get("filename")
    if not filename:
        raise HTTPException(status_code=404, detail="Manuscript file not found")

    temp_path = os.path.join(TEMP_DIR, filename)
    if os.path.isfile(temp_path):
        return FileResponse(temp_path, media_type="application/pdf", filename=filename)

    search_dirs = [
        os.path.join(PROJECT_ROOT, "data"),
        os.path.join(PROJECT_ROOT, "storage"),
    ]
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for root, _, files in os.walk(search_dir):
                if filename in files:
                    candidate = os.path.join(root, filename)
                    return FileResponse(candidate, media_type="application/pdf", filename=filename)

    raise HTTPException(
        status_code=404,
        detail=f"Original PDF file '{filename}' was cleaned up or could not be found on server storage."
    )


@router.get("/v1/manuscripts/{manuscript_id}/pdf")
def get_manuscript_pdf_v1(manuscript_id: int, current_user: TokenData = Depends(get_current_user)):
    """Compatibility alias for PDF download."""
    return get_manuscript_pdf(manuscript_id, current_user)
