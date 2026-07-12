"""
orchestrator.py — Shared Pipeline Orchestrator
Orchestrates sequential 4-layer evaluation workflow for PDF manuscripts.
Common execution code shared between scripts/run_full_pipeline.py and the FastAPI backend.
"""

import os
import time
import logging
import pandas as pd
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("PipelineOrchestrator")

from .schemas import PipelineResult
from .exceptions import LayerExecutionError
from .persistence import save_pipeline_outputs

# Import Layer 1 components
from parsing_engine.extractor import extract_text_and_metadata
from parsing_engine.section_parser import segment_sections
from parsing_engine.text_cleaning import extract_title_from_first_lines
from editorial_rules.hard_rules import run_editorial_rules
from editorial_rules.editorial_features import compute_editorial_features

# Import Layer 2 components
from llm_scoring.qwen_client import run_qwen_scoring

# Import Layer 3 components
from calibration.online.service import Layer3Service
from calibration.online.schemas import PredictionRequest

# Import Layer 4 components
from explanation_engine.generator import ExplanationGenerator
from explanation_engine.schemas import ExplanationRequest


class PipelineOrchestrator:
    """Shared coordinator running the four-layer pre-filter pipeline."""

    @staticmethod
    def run(
        pdf_path: str,
        conference: str = "iclr_2017",
        mode: str = "real",
        persist: bool = False,
        manuscript_id: Optional[str] = None,
        user_id: Optional[int] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> PipelineResult:
        """
        Runs the 4 layers sequentially on a single manuscript.
        """
        p_path = os.path.abspath(pdf_path)
        ms_id = manuscript_id or os.path.splitext(os.path.basename(p_path))[0]
        
        # Helper to update progress callback
        def _update_progress(stage: str, status: str):
            if progress_callback:
                try:
                    progress_callback(stage, status)
                except Exception as cb_err:
                    logger.error(f"Progress callback failed: {cb_err}")

        _update_progress("stage_0", "active")
        try:
            extraction_result = extract_text_and_metadata(p_path) or {}
            raw_text = extraction_result.get("full_text") or extraction_result.get("text", "")
            if not raw_text.strip():
                raise ValueError("Zero text extracted from PDF manuscript.")

            meta = extraction_result.get("metadata", {})

            # Title resolution: 4-tier fallback with invalid-value rejection
            # Placeholders that must never be persisted as the title
            _INVALID_TITLES = {
                "removed", "untitled", "anonymous", "anonymized", "n/a",
                "none", "unknown", "unavailable", "untitled document",
                "microsoft word", "null", "",
            }

            def _is_valid_title(candidate: str) -> bool:
                if not candidate:
                    return False
                c = candidate.strip().lower()
                if c in _INVALID_TITLES:
                    return False
                if len(candidate.strip()) < 5:
                    return False
                return True

            # Tier 1: PDF extractor's 3-tier result (metadata → largest font → first line)
            _t1 = (meta.get("title") or "").strip()
            # Tier 2: simple first-line heuristic from cleaned text
            _t2 = extract_title_from_first_lines(raw_text)
            # Tier 3: manuscript ID / filename stem (only when it is not a plain integer)
            _t3 = ms_id if ms_id and not str(ms_id).isdigit() else ""
            # Tier 4: safe catch-all
            _t4 = "Unavailable / anonymized"

            if _is_valid_title(_t1):
                title = _t1
            elif _is_valid_title(_t2):
                title = _t2
            elif _is_valid_title(_t3):
                title = _t3
            else:
                title = _t4

            sections = segment_sections(raw_text)

            # Clean sections
            cleaned_sections = {k: (v if v is not None else "") for k, v in sections.items()}
            _update_progress("stage_0", "completed")
        except Exception as exc:
            _update_progress("stage_0", "failed")
            raise LayerExecutionError(0, f"Ingestion failed: {exc}", exc)


        _update_progress("stage_1", "active")
        try:
            hard_flags, _, _ = run_editorial_rules(cleaned_sections, meta, raw_text)
            l1_features = compute_editorial_features(cleaned_sections, meta, raw_text)
            _update_progress("stage_1", "completed")
        except Exception as exc:
            _update_progress("stage_1", "failed")
            raise LayerExecutionError(1, f"Editorial rules failed: {exc}", exc)

        _update_progress("stage_2", "active")
        try:
            if mode == "real":
                # Strict missing logic configuration lookup
                qwen_scores = run_qwen_scoring(
                    sections=cleaned_sections,
                    features=l1_features,
                    mode="real",
                    full_text=raw_text,
                    layer1_violations=[getattr(v, "description", str(v)) for v in hard_flags]
                )
            else:
                # Deterministic mock score mapping matching terminal pipeline
                word_count = len(raw_text.split())
                sec_count = len(cleaned_sections)
                base_qual = min(0.90, max(0.50, 0.60 + (min(word_count, 6000) / 20000.0) - (len(hard_flags) * 0.08)))
                qwen_scores = {
                    "abstract_clarity": round(min(0.95, base_qual + 0.05), 4),
                    "structural_completeness": round(min(0.95, 0.65 + (sec_count * 0.06)), 4),
                    "methodological_strength": round(base_qual, 4),
                    "experimental_strength": round(max(0.40, base_qual - 0.05), 4),
                    "argumentative_quality": round(min(0.95, base_qual + 0.03), 4),
                    "scope_alignment": 0.90,
                    "overall_quality": round(base_qual, 4),
                    "detected_issues": [f"{getattr(v, 'rule_name', 'Rule')}: {getattr(v, 'description', '')}" for v in hard_flags[:3]],
                    "evidence_spans": [f"[{sec}] Section verified intact." for sec in list(cleaned_sections.keys())[:2]],
                    "mode": "mock_deterministic",
                    "prompt_version": "v5",
                    "raw_output": "Mock scoring completed successfully."
                }
            _update_progress("stage_2", "completed")
        except Exception as exc:
            _update_progress("stage_2", "failed")
            raise LayerExecutionError(2, f"Semantic evaluation failed: {exc}", exc)

        _update_progress("stage_3", "active")
        try:
            layer3_service = Layer3Service(db_session=None)
            
            layer1_dict = {
                "total_rules_failed": len(hard_flags),
                "critical_rules_failed": sum(1 for getattr_v in hard_flags if getattr(getattr_v, 'severity', '') == 'critical'),
                "violations": hard_flags,
                **l1_features
            }
            req_dto = PredictionRequest(
                manuscript_id=ms_id,
                layer1_rules=layer1_dict,
                layer2_scores=qwen_scores,
                raw_features_override={"conference": conference}
            )
            l3_prediction = layer3_service.predict(request=req_dto)
            _update_progress("stage_3", "completed")
        except Exception as exc:
            _update_progress("stage_3", "failed")
            raise LayerExecutionError(3, f"Layer 3 prediction failed: {exc}", exc)

        _update_progress("stage_4", "active")
        try:
            feature_names = layer3_service.get_feature_names()
            model_instance = layer3_service.get_active_model()
            df_inference = pd.DataFrame([l3_prediction.feature_vector])
            if feature_names:
                df_inference = df_inference.reindex(columns=feature_names, fill_value=0.0)

            generator = ExplanationGenerator(model=model_instance, feature_names=feature_names)
            xai_request = ExplanationRequest(
                manuscript_id=ms_id,
                layer1_result=hard_flags,
                layer2_result=qwen_scores,
                layer3_prediction=l3_prediction,
                model_input_dataframe=df_inference
            )
            xai_result = generator.generate_explanation(xai_request)
            report_dict = xai_result.to_master_report_dict()
            _update_progress("stage_4", "completed")
        except Exception as exc:
            _update_progress("stage_4", "failed")
            raise LayerExecutionError(4, f"Layer 4 explanation failed: {exc}", exc)

        # Build output result DTO
        result = PipelineResult(
            manuscript_id=ms_id,
            filename=os.path.basename(p_path),
            title=title,
            sections=cleaned_sections,
            layer1_violations=hard_flags,
            editorial_features=l1_features,
            layer2_scores=qwen_scores,
            layer3_prediction=l3_prediction,
            report_json=report_dict
        )
        
        # Add metadata alias mapping for persistence helper
        result.layer1_metadata = {
            "title": title,
            "num_pages": meta.get("num_pages", meta.get("page_count", 1)),
            "total_word_count": meta.get("total_word_count", len(raw_text.split()))
        }

        if persist:
            save_pipeline_outputs(int(ms_id) if ms_id.isdigit() else 0, result)

        return result
