"""
Script 04: Process Pipeline to JSON (Real Production Mode with Strict PDF Progress Counting)
Phase 2 - Pipeline Ingestion

Reads physical PDFs from:
  data/peerread_filtered/{accepted,rejected}/{conference}/pdfs/*.pdf

Runs each PDF through the real production pipeline using Prompt V5.
Progress counter traces exclusively strict *.pdf files with per-conference limits.
"""

import os
import sys
import json
import pathlib
import traceback
import argparse
import re

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--prompt", choices=["v1", "v5", "freetext"], default="v5", help="Prompt version to execute.")
parser.add_argument("--model", choices=["qwen3:4b", "qwen3.5:35b", "qwen3.6:latest"], default="qwen3:4b", help="Qwen model to use.")
args = parser.parse_args()
prompt_version = args.prompt
model_choice = args.model

PROJECT_ROOT  = pathlib.Path(__file__).resolve().parents[3]
PACKAGES_DIR  = PROJECT_ROOT / "packages"
FILTERED_ROOT = PROJECT_ROOT / "data" / "peerread_filtered"
OUTPUT_DIR    = PROJECT_ROOT / "data" / "processed"

if prompt_version == "v1":
    OUTPUT_JSONL = OUTPUT_DIR / "processed_data_v1.json"
elif prompt_version == "freetext":
    OUTPUT_JSONL = OUTPUT_DIR / "processed_data_freetext.json"
else:  # v5
    if model_choice == "qwen3.5:35b":
        OUTPUT_JSONL = OUTPUT_DIR / "processed_data_qwen_35b.json"
    elif model_choice == "qwen3.6:latest":
        OUTPUT_JSONL = OUTPUT_DIR / "processed_data_qwen_latest.json"
    else:
        OUTPUT_JSONL = OUTPUT_DIR / "processed_data.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Dynamically add project root and packages/ directory to sys.path
for p in [str(PROJECT_ROOT), str(PACKAGES_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Layer 1 Text Extraction
from parsing_engine.extractor import extract_text_and_metadata
from parsing_engine.section_parser import segment_sections

# Layer 1 Editorial Rules
from editorial_rules.hard_rules import run_editorial_rules
from editorial_rules.editorial_features import compute_editorial_features

# Layer 2 Real Qwen Inference (NO MOCKS)
from llm_scoring.qwen_client import run_qwen_scoring
from llm_scoring.prompts import get_prompt_builder


def to_float(val, default=0.5):
    """Safe float conversion helper for LLM output scores."""
    try:
        if val is None:
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def parse_freetext_scores(text: str) -> dict:
    extracted_scores = {}
    block_match = re.search(r"\[SCORES\](.*?)\[END SCORES\]", text, re.DOTALL | re.IGNORECASE)
    if not block_match:
        return extracted_scores
    block_content = block_match.group(1)
    pattern = re.compile(r"(\w+)\s*:\s*([0-9.]+)")
    for line in block_content.split("\n"):
        match = pattern.search(line)
        if match:
            key = match.group(1).strip().lower()
            val = float(match.group(2).strip())
            extracted_scores[key] = val
    return extracted_scores



processed_pdfs = set()
if OUTPUT_JSONL.exists():
    try:
        # Read the entire file content to parse filenames robustly
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
            content = f.read()
            # Capture all instances of "filename": "xxx.pdf" regardless of spacing or line breaks
            filenames_found = re.findall(r'"filename"\s*:\s*"([^"]+)"', content)
            for fname in filenames_found:
                processed_pdfs.add(fname)
                
        # Safe Append Alignment:
        # If the file has contents, ensure it ends with a clean newline so that
        # subsequent appends write cleanly to a new line instead of corrupting the last object.
        if OUTPUT_JSONL.stat().st_size > 0:
            with open(OUTPUT_JSONL, "rb+") as f:
                f.seek(-1, os.SEEK_END)
                last_char = f.read(1)
                if last_char != b'\n':
                    f.write(b'\n')
    except Exception as e:
        print(f"[04] WARNING: Could not read checkpoint file: {e}")

print(f"[04] Loaded checkpoint: {len(processed_pdfs)} PDFs already processed.")
print(f"[04] Output target    : {OUTPUT_JSONL}")


TARGET_VERDICTS = ["accepted", "rejected"]

# Define exact limits for each conference per verdict folder
CONFERENCE_LIMITS = {
    "acl_2017": 130,
    "conll_2016": 21,
    "iclr_2017": 149
}
TARGET_CONFERENCES = list(CONFERENCE_LIMITS.keys())


total_pdfs = 0
for verdict in TARGET_VERDICTS:
    verdict_dir = FILTERED_ROOT / verdict
    if not verdict_dir.exists():
        continue
    for conference_dir in sorted(verdict_dir.iterdir()):
        if not conference_dir.is_dir():
            continue
        if conference_dir.name not in TARGET_CONFERENCES:
            continue
        pdfs_dir = conference_dir / "pdfs"
        if pdfs_dir.exists():
            available_pdfs = len(list(pdfs_dir.glob("*.pdf")))
            limit = CONFERENCE_LIMITS.get(conference_dir.name, available_pdfs)
            total_pdfs += min(available_pdfs, limit)

print(f"[04] Total target allocation size: {total_pdfs} strict .pdf documents targeted.")
print("=" * 75)


processed   = 0
skipped     = 0
errors      = 0
current_idx = 0  # Running counter tracking active file position out of total_pdfs

# Open in append mode ('a') with unbuffered/immediate write via flush()
with open(OUTPUT_JSONL, "a", encoding="utf-8") as out_f:
    for verdict in TARGET_VERDICTS:
        verdict_dir = FILTERED_ROOT / verdict
        if not verdict_dir.exists():
            print(f"[04] WARNING: {verdict_dir} not found — run script 02 first.")
            continue

        ground_truth = 1 if verdict == "accepted" else 0

        for conference_dir in sorted(verdict_dir.iterdir()):
            if not conference_dir.is_dir():
                continue
            conference_name = conference_dir.name
            if conference_name not in TARGET_CONFERENCES:
                continue
            
            pdfs_dir = conference_dir / "pdfs"
            if not pdfs_dir.exists():
                continue

            limit = CONFERENCE_LIMITS.get(conference_name, 999999)
            
            # Local counter tracking documents processed inside THIS conference folder
            processed_for_this_conf_verdict = 0

            # Sorted loop for absolute predictability
            for pdf_path in sorted(pdfs_dir.glob("*.pdf")):
                
                # CRITICAL: If the target quota for this conference folder is met, 
                # break out of this loop immediately to PASS to the next conference folder!
                if processed_for_this_conf_verdict >= limit:
                    break

                filename = pdf_path.name
                current_idx += 1  # Increment counter relative to total_pdfs target ceiling

                # Idempotent resume check with strict progress indicators
                if filename in processed_pdfs:
                    print(f"[{current_idx} / {total_pdfs}] - [SKIPPING] Already processed in {conference_name}: {filename}")
                    skipped += 1
                    processed_for_this_conf_verdict += 1  # Counts towards quota to handle resume correctly
                    continue

                # Processing notice with strict progress indicators
                print(f"[{current_idx} / {total_pdfs}] - Processing: {verdict}/{conference_name}/pdfs/{filename}")

                # Wrap entire PDF processing in robust try/except block
                try:
                    extracted = extract_text_and_metadata(str(pdf_path))
                    full_text = extracted.get("full_text", "") or ""
                    metadata  = extracted.get("metadata", {}) or {}

                    num_pages        = int(metadata.get("num_pages", 0) or 0)
                    total_word_count = int(metadata.get("total_word_count", len(full_text.split())) or 0)

                    sections = segment_sections(full_text) if full_text else {}
                    features = compute_editorial_features(sections, metadata, full_text)

                    rule_checks_list = []
                    try:
                        hard_flags, _, _ = run_editorial_rules(sections, metadata, full_text)
                        rule_checks_list = [
                            {
                                "rule_name":   v.rule_name,
                                "severity":    v.severity,
                                "passed":      False,
                                "description": v.description,
                                "details":     getattr(v, "details", ""),
                            }
                            for v in hard_flags
                        ]
                    except Exception as rules_exc:
                        print(f"     [RULES WARN] Rule evaluation fallback ({rules_exc})")
                        try:
                            from editorial_rules.hard_rules import HardRulesEngine
                            default_rules = {"min_pages": 4, "max_pages": 30, "max_missing_sections": 2}
                            res = HardRulesEngine().run(sections, features, default_rules)
                            rule_checks_list = [
                                {
                                    "rule_name":   v.rule_name,
                                    "severity":    v.severity,
                                    "passed":      False,
                                    "description": v.description,
                                    "details":     getattr(v, "details", ""),
                                }
                                for v in res.violations
                            ]
                        except Exception:
                            rule_checks_list = []

                    format_failure = 0
                    try:
                        qwen_scores = run_qwen_scoring(
                            sections=sections,
                            features=features,
                            mode="real",
                            full_text=full_text,
                            layer1_violations=rule_checks_list,
                            prompt_version=prompt_version,
                            model=model_choice,
                        )
                        
                        if prompt_version == "freetext":
                            raw_text = qwen_scores.get("raw_output") or ""
                            parsed_scores = parse_freetext_scores(raw_text)
                            if parsed_scores:
                                qwen_scores.update(parsed_scores)
                                format_failure = 0
                            else:
                                format_failure = 1
                                # Fallback matrix of 0.50
                                for key in ["abstract_clarity", "structural_completeness", "methodological_strength", 
                                            "experimental_strength", "argumentative_quality", "scope_alignment", "overall_quality"]:
                                    qwen_scores[key] = 0.5
                                qwen_scores["integrity_risk_score"] = 0.0
                                qwen_scores["research_paper_likelihood"] = 0.5
                        else:
                            if qwen_scores.get("api_error") or qwen_scores.get("parse_error"):
                                format_failure = 1
                                err_msg = qwen_scores.get("error_message") or qwen_scores.get("parse_error_detail")
                                print(f"     [QWEN WARN] Live API/Parse fallback applied: {err_msg}")
                                qwen_scores = {
                                    "abstract_clarity":          0.5,
                                    "structural_completeness":   0.5,
                                    "methodological_strength":   0.5,
                                    "experimental_strength":     0.5,
                                    "argumentative_quality":     0.5,
                                    "scope_alignment":           0.5,
                                    "overall_quality":           0.5,
                                    "integrity_risk_score":      0.0,
                                    "research_paper_likelihood": 0.5,
                                }
                    except Exception as qwen_exc:
                        print(f"     [QWEN ERROR] Live API exception caught: {qwen_exc}")
                        format_failure = 1
                        qwen_scores = {
                            "abstract_clarity":          0.5,
                            "structural_completeness":   0.5,
                            "methodological_strength":   0.5,
                            "experimental_strength":     0.5,
                            "argumentative_quality":     0.5,
                            "scope_alignment":           0.5,
                            "overall_quality":           0.5,
                            "integrity_risk_score":      0.0,
                            "research_paper_likelihood": 0.5,
                        }

                    record = {
                        "filename":                  filename,
                        "conference":                conference_name,
                        "ground_truth":              ground_truth,
                        "words":                     total_word_count,
                        "pages":                     num_pages,
                        "format_failure":            format_failure,
                        "abstract_clarity":          to_float(qwen_scores.get("abstract_clarity", 0.5), 0.5),
                        "structural_completeness":   to_float(qwen_scores.get("structural_completeness", 0.5), 0.5),
                        "methodological_strength":   to_float(qwen_scores.get("methodological_strength", 0.5), 0.5),
                        "experimental_strength":     to_float(qwen_scores.get("experimental_strength", 0.5), 0.5),
                        "argumentative_quality":     to_float(qwen_scores.get("argumentative_quality", 0.5), 0.5),
                        "scope_alignment":           to_float(qwen_scores.get("scope_alignment", 0.5), 0.5),
                        "overall_quality":           to_float(qwen_scores.get("overall_quality", 0.5), 0.5),
                        "integrity_risk_score":      to_float(qwen_scores.get("integrity_risk_score", 0.0), 0.0),
                        "research_paper_likelihood": to_float(qwen_scores.get("research_paper_likelihood", qwen_scores.get("scope_alignment", 0.5)), 0.5),
                        "rule_checks":               rule_checks_list,
                    }

                    # Write record immediately and flush to disk
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_f.flush()

                    processed_pdfs.add(filename)
                    processed += 1
                    processed_for_this_conf_verdict += 1

                except Exception as e:
                    errors += 1
                    print(f"     [ERROR] Failed processing {filename}: {e}")
                    traceback.print_exc()

print()
print("=" * 75)
print(f"[04] PRODUCTION INGESTION COMPLETED")
print(f"     Processed this run : {processed}")
print(f"     Skipped (checkpoint): {skipped}")
print(f"     Errors             : {errors}")
print(f"     Total checkpointed : {len(processed_pdfs)} / (300 accepted + {total_pdfs} rejected target)")
print(f"     Output JSONL       : {OUTPUT_JSONL}")