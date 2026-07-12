"""
Editorial Pipeline Orchestrator (Official Guideline Mapped)
Connects PDF extraction -> Section parsing -> Hard rules -> Qwen scoring -> Persistence
"""

from pathlib import Path
from typing import Dict, List, Optional

from src.ingestion.validate import validate_pdf
from src.ingestion.extractor import extract_text_and_metadata
from src.parsing.section_parser import segment_sections
from src.rules.hard_rules import run_editorial_rules, HardRulesEngine, HardRulesResult
from src.features.editorial_features import compute_editorial_features
from src.database.save import (
    save_manuscript,
    save_sections,
    save_editorial_features,
    save_rule_checks,
    save_model_run,
)
from src.llm.qwen_client import run_qwen_scoring


def _normalize_sections(sections: Dict) -> Dict[str, str]:
    normalized = {}
    for key, value in sections.items():
        if value is None:
            normalized[key] = ""
        elif isinstance(value, str):
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized


def _save_outputs_to_db(
    metadata: Dict,
    sections: Dict[str, str],
    editorial_features: Dict,
    hard_flags: List,
    qwen_scores: Dict,
) -> tuple[Optional[int], Optional[int]]:
    manuscript_id: Optional[int] = None
    model_run_id: Optional[int] = None

    try:
        manuscript_id = save_manuscript(metadata)

        save_sections(manuscript_id, sections)
        save_editorial_features(manuscript_id, editorial_features)
        save_rule_checks(manuscript_id, hard_flags)

        meta = qwen_scores.get("_meta", {}) if isinstance(qwen_scores, dict) else {}

        model_run_id = save_model_run(
            manuscript_id=manuscript_id,
            model_version=meta.get("model", "qwen3.5:35b"),
            prompt_version=meta.get("prompt_version"),
            prompt_text=meta.get("prompt_text"),
            input_payload=meta.get("input_payload"),
            raw_output=meta.get("raw_output"),
            parsed_output=qwen_scores,
        )

    except Exception as e:
        print("DATABASE SAVE ERROR:", str(e))
        manuscript_id = None
        model_run_id = None
        metadata["db_warning"] = f"Could not save manuscript/model data: {str(e)}"

    return manuscript_id, model_run_id


def process_manuscript(manuscript_pdf: str, save_to_db: bool = False, prompt_version: str = "v2") -> Dict:
    try:
        validate_pdf(manuscript_pdf)
        extracted = extract_text_and_metadata(manuscript_pdf)
        if isinstance(extracted, dict):
            text = extracted.get("full_text", "")
            metadata = extracted.get("metadata", {})
        else:
            text, metadata = extracted
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "metadata": {"filename": Path(manuscript_pdf).name},
            "decision": "error",
            "probability": 0.0,
            "reason": f"PDF processing failed: {str(e)}",
        }

    sections = _normalize_sections(segment_sections(text))

    try:
        hard_flags, decision, probability = run_editorial_rules(sections, metadata, text)
        editorial_features = compute_editorial_features(sections, metadata, text)

        qwen_scores = run_qwen_scoring(
            sections=sections,
            features=editorial_features,
            mode="real",
            prompt_version=prompt_version,
            full_text=text,
            layer1_violations=[v.description for v in hard_flags],
        )

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "metadata": metadata,
            "sections": sections,
            "decision": "error",
            "probability": 0.0,
            "reason": f"Pipeline processing failed: {str(e)}",
        }

    manuscript_id: Optional[int] = None
    model_run_id: Optional[int] = None

    if save_to_db:
        manuscript_id, model_run_id = _save_outputs_to_db(
            metadata=metadata,
            sections=sections,
            editorial_features=editorial_features,
            hard_flags=hard_flags,
            qwen_scores=qwen_scores,
        )

    engine = HardRulesEngine()
    fake_result = HardRulesResult(
        passed=not any(v.severity.value == "high" for v in hard_flags),
        violations=hard_flags,
        desk_reject_probability=probability,
    )
    reason = engine.get_summary_report(fake_result)

    return {
        "success": True,
        "metadata": metadata,
        "sections": sections,
        "hard_flags": hard_flags,
        "editorial_features": editorial_features,
        "qwen_scores": qwen_scores,
        "decision": decision,
        "probability": probability,
        "reason": reason,
        "manuscript_id": manuscript_id,
        "model_run_id": model_run_id,
    }


class EditorialPipeline:
    def process_peerread_batch(
        self,
        split: str = "train",
        limit: Optional[int] = None,
        data_dir: str = "./data/peerread/",
        save_to_db: bool = False,
        prompt_version: str = "v2",
    ) -> List[Dict]:

        try:
            from src.dataset.loader import ICLRLoader
            loader = ICLRLoader(data_dir)
            papers = loader.load_split(split)
        except ImportError:
            print("Warning: ICLRLoader not found in src.dataset.loader. Bypassing batch load.")
            papers = []

        if limit is not None:
            papers = papers[:limit]

        results: List[Dict] = []

        for paper in papers:
            text = getattr(paper, "full_text", "") or ""
            paper_id = getattr(paper, "paper_id", "unknown")

            word_count = len(text.split()) if text else 0
            estimated_pages = max(1, word_count // 500) if word_count > 0 else 0

            metadata = {
                "filename": f"{paper_id}.pdf",
                "num_pages": estimated_pages,
                "total_word_count": word_count,
                "title": getattr(paper, "title", None),
                "ground_truth": getattr(paper, "label", None),
            }

            sections = _normalize_sections(segment_sections(text))

            try:
                hard_flags, decision, probability = run_editorial_rules(sections, metadata, text)
                editorial_features = compute_editorial_features(sections, metadata, text)

                qwen_scores = run_qwen_scoring(
                    sections=sections,
                    features=editorial_features,
                    mode="real",
                    prompt_version=prompt_version,
                    full_text=text,
                    layer1_violations=[v.description for v in hard_flags],
                )

            except Exception as e:
                results.append({
                    "paper_id": paper_id,
                    "true_label": getattr(paper, "label", None),
                    "true_decision": getattr(paper, "decision", None),
                    "success": False,
                    "error": str(e),
                })
                continue

            manuscript_id: Optional[int] = None
            model_run_id: Optional[int] = None

            if save_to_db:
                manuscript_id, model_run_id = _save_outputs_to_db(
                    metadata=metadata,
                    sections=sections,
                    editorial_features=editorial_features,
                    hard_flags=hard_flags,
                    qwen_scores=qwen_scores,
                )

            sections_present = editorial_features.get("sections_present", {})
            quality_indicators = editorial_features.get("quality_indicators", {})

            results.append({
                "paper_id": paper_id,
                "true_label": getattr(paper, "label", None),
                "true_decision": getattr(paper, "decision", None),
                "success": True,
                "hard_rules_reject": decision == "reject",
                "hard_rules_probability": probability,
                "violations_count": len(hard_flags),
                "missing_sections": quality_indicators.get("missing_critical_sections", []),
                "sections_present": sum(1 for v in sections_present.values() if v),
                "qwen_scores": qwen_scores,
                "manuscript_id": manuscript_id,
                "model_run_id": model_run_id,
            })

        return results
        