"""
Manifest-Driven Editorial Pipeline Runner
Integrates Layer 1 (Manifest Routing) and Layer 2 (PDF Extraction) directly with your Orchestrator.
"""

import os
import json
import pdfplumber
from pathlib import Path
from typing import List, Dict, Optional

# Core system function imports from your local src modules
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

# Configuration Paths
PROJECT_ROOT = Path(r"C:\Users\Document\OneDrive\Desktop\TFG\Project")
PEERREAD_DATA_DIR = PROJECT_ROOT / "data" / "peerread"
MANIFEST_PATH = PROJECT_ROOT / "data" / "peerread_pdfs_only_manifest.json"


# ==============================================================================
# CORE PIPELINE HELPER FUNCTIONS
# ==============================================================================

def _normalize_sections(sections: Dict) -> Dict[str, str]:
    """Ensures all extracted section values are standard flat strings."""
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
    """Handles the persistence layer processing into your local database."""
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


# ==============================================================================
# MANIFEST PIPELINE CLASS
# ==============================================================================

class ManifestDrivenEditorialPipeline:
    """Orchestrator that processes manuscripts based on a 3-way virtual manifest split."""

    def _extract_pdf_text_layer2(self, absolute_pdf_path: Path) -> str:
        """LAYER 2: Reads raw binary PDF files and cleans the text stream."""
        try:
            extracted_pages = []
            with pdfplumber.open(absolute_pdf_path) as pdf:
                # Read up to the first 12 pages to preserve system RAM memory
                for page in pdf.pages[:12]:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_pages.append(page_text)
                        
            full_text = " ".join(extracted_pages)
            # Clean up problematic formatting to stabilize text presentation for CSV/JSON
            cleaned_text = full_text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
            return " ".join(cleaned_text.split())
        except Exception as e:
            raise RuntimeError(f"Layer 2 PDF text extraction failed: {str(e)}")

    def process_manifest_batch(
        self,
        split: str = "train",
        limit: Optional[int] = None,
        save_to_db: bool = False,
        prompt_version: str = "v2",
    ) -> List[Dict]:
        """
        LAYER 1: Routes input items from the 3-way manifest split,
        extracts text, and processes them through your core system layers.
        """
        if not MANIFEST_PATH.exists():
            raise FileNotFoundError(f"Manifest not found! Please run your 3-way splitter script first.")

        # Load your virtual 3-way split roadmap
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        # Grab the specific partition list (train, val, or test)
        if split not in manifest_data:
            raise ValueError(f"Invalid split request. Choose from: 'train', 'val', 'test'.")
            
        target_papers = manifest_data[split]
        if limit is not None:
            target_papers = target_papers[:limit]

        results: List[Dict] = []
        total_papers = len(target_papers)

        print(f"\n==========================================================")
        print(f"STARTING PIPELINE PROCESSING FOR SPLIT PARTITION: [{split.upper()}]")
        print(f"==========================================================")
        print(f"Target Queue Size: {total_papers} papers identified via Manifest Router.")

        for idx, entry in enumerate(target_papers, 1):
            # LAYER 1: Extract paths and assign target parameters
            relative_review_path = entry["review_path"]
            relative_asset_path = entry["asset_path"]
            conference_origin = entry["conference"]
            
            absolute_pdf_path = PEERREAD_DATA_DIR / relative_asset_path
            paper_id = absolute_pdf_path.stem
            ground_truth_label = 1 if "accepted" in relative_review_path else 0

            print(f"[{idx}/{total_papers}] Processing File ID: {paper_id} ({conference_origin})")

            if not absolute_pdf_path.exists():
                print(f"   -> WARNING: File missing at path: {absolute_pdf_path.resolve()}. Skipping.")
                continue

            try:
                # LAYER 2: Extract text from PDF binary
                text_content = self._extract_pdf_text_layer2(absolute_pdf_path)
                
                # Metadata calculation block matching your pipeline footprint
                word_count = len(text_content.split()) if text_content else 0
                estimated_pages = max(1, word_count // 500) if word_count > 0 else 0

                metadata = {
                    "filename": absolute_pdf_path.name,
                    "num_pages": estimated_pages,
                    "total_word_count": word_count,
                    "title": paper_id.replace("_", " "), # Placeholder title fallback
                    "ground_truth": ground_truth_label,
                }

                # Core Pipeline Segment Operations Hand-off
                sections = _normalize_sections(segment_sections(text_content))
                
                # Execute your custom system metrics and rules
                hard_flags, decision, probability = run_editorial_rules(sections, metadata, text_content)
                editorial_features = compute_editorial_features(sections, metadata, text_content)

                # Process text data through your active LLM scoring client
                qwen_scores = run_qwen_scoring(
                    sections=sections,
                    features=editorial_features,
                    mode="real",
                    prompt_version=prompt_version,
                    full_text=text_content,
                    layer1_violations=[v.description for v in hard_flags],
                )

                # Persistence Layer Execution
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

                # Append success results dictionary format
                results.append({
                    "paper_id": paper_id,
                    "true_label": ground_truth_label,
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

            except Exception as e:
                print(f"   -> PIPELINE FAILURE on Paper {paper_id}: {str(e)}")
                results.append({
                    "paper_id": paper_id,
                    "true_label": ground_truth_label,
                    "success": False,
                    "error": str(e),
                })

        print(f"==========================================================")
        print(f"PARTITION [{split.upper()}] COMPLETED PROCESSING.")
        print(f"==========================================================\n")
        return results


if __name__ == "__main__":
    # Test your orchestrator pipeline components on a small batch of validation samples
    pipeline = ManifestDrivenEditorialPipeline()
    
    # Process 3 files from your validation split to confirm everything works properly
    validation_test_results = pipeline.process_manifest_batch(
        split="val", 
        limit=3, 
        save_to_db=False, 
        prompt_version="v2"
    )
    
    print("Sample Batch Execution Output Preview:")
    print(json.dumps(validation_test_results, indent=2, default=str))