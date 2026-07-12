# ============================================================
# FILE:
# src/build_layer3_dataset.py
# ============================================================

import os
import json
import traceback
import pandas as pd
from tqdm import tqdm

# ============================================================
# REAL PROJECT IMPORTS
# ============================================================

from src.ingestion.extractor import extract_text_and_metadata
from src.parsing.section_parser import segment_sections
from src.rules.hard_rules import run_editorial_rules
from src.llm.qwen_client import run_qwen_scoring

from src.features.editorial_features import compute_editorial_features
from src.ingestion.validate import validate_pdf


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = r"C:\Users\Document\OneDrive\Desktop\TFG\Project"

DATA_ROOT = os.path.join(PROJECT_ROOT, "data")

PEERREAD_ROOT = os.path.join(DATA_ROOT, "peerread")

MANIFEST_PATH = os.path.join(
    DATA_ROOT,
    "peerread_pdfs_only_manifest.json"
)

OUTPUT_DIR = os.path.join(DATA_ROOT, "processed")

os.makedirs(OUTPUT_DIR, exist_ok=True)

FAILED_LOG = os.path.join(
    OUTPUT_DIR,
    "failed_pdfs.txt"
)


# ============================================================
# OUTPUT FILES
# ============================================================

TRAIN_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "train_dataset.csv"
)

VAL_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "val_dataset.csv"
)

TEST_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "test_dataset.csv"
)


# ============================================================
# LOAD MANIFEST
# ============================================================

with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    manifest = json.load(f)


# ============================================================
# LABEL EXTRACTION
# ============================================================

def derive_label(asset_path: str):

    asset_path = asset_path.lower()

    if asset_path.startswith("accepted"):
        return 1

    if asset_path.startswith("rejected"):
        return 0

    return None


# ============================================================
# QWEN V5 FLATTENING
# ============================================================

def flatten_qwen_v5(qwen_output: dict):

    flat = {}

    scalar_keys = [
        "recommendation",
        "research_paper_likelihood",
        "integrity_risk_score",
        "pdf_extraction_quality",
        "structure_validity_score",
        "equation_quality_score",
        "citation_quality_score",
        "content_coherence_score",
        "reproducibility_signal_score",
        "final_integrity_decision",
    ]

    for key in scalar_keys:
        flat[key] = qwen_output.get(key)

    # ========================================================
    # LAYER1 VERIFICATION
    # ========================================================

    layer1 = qwen_output.get(
        "layer1_verification",
        {}
    )

    flat["methodology_missing_confirmed"] = int(
        layer1.get(
            "methodology_missing_confirmed",
            False
        )
    )

    flat["methodology_like_content_found_elsewhere"] = int(
        layer1.get(
            "methodology_like_content_found_elsewhere",
            False
        )
    )

    # ========================================================
    # RESEARCH PAPER CHECKS
    # ========================================================

    checks = qwen_output.get(
        "research_paper_checks",
        {}
    )

    for key, value in checks.items():
        flat[f"check_{key}"] = int(bool(value))

    # ========================================================
    # INTEGRITY FLAGS
    # ========================================================

    flags = qwen_output.get(
        "integrity_flags",
        []
    )

    high = 0
    medium = 0
    low = 0

    for flag in flags:

        severity = flag.get(
            "severity",
            ""
        ).lower()

        if severity == "high":
            high += 1

        elif severity == "medium":
            medium += 1

        elif severity == "low":
            low += 1

    flat["integrity_flags_high"] = high
    flat["integrity_flags_medium"] = medium
    flat["integrity_flags_low"] = low

    return flat


# ============================================================
# SAFE FEATURE EXTRACTION
# ============================================================

def safe_missing_sections_count(editorial_features):

    missing_sections = (
        editorial_features
        .get("quality_indicators", {})
        .get("missing_critical_sections", [])
    )

    if isinstance(missing_sections, list):
        return len(missing_sections)

    if isinstance(missing_sections, int):
        return missing_sections

    return 0


# ============================================================
# PROCESS SINGLE PDF
# ============================================================

def process_pdf(entry: dict):

    try:

        asset_path = entry["asset_path"]

        pdf_path = os.path.join(
            PEERREAD_ROOT,
            asset_path
        )

        print(f"\nProcessing: {pdf_path}")

        # ====================================================
        # VALIDATE PDF
        # ====================================================

        validation_result = validate_pdf(pdf_path)

        is_valid = False

        if isinstance(validation_result, dict):
            is_valid = validation_result.get(
                "valid",
                False
            )
        else:
            is_valid = bool(validation_result)

        if not is_valid:
            raise ValueError(
                f"Invalid PDF: {pdf_path}"
            )

        # ====================================================
        # LABEL
        # ====================================================

        true_label = derive_label(asset_path)

        # ====================================================
        # EXTRACTION
        # ====================================================

        extracted_raw = extract_text_and_metadata(
            pdf_path
        )

        extracted = {}

        if isinstance(extracted_raw, dict):
            extracted = extracted_raw

        elif isinstance(extracted_raw, tuple):

            for item in extracted_raw:

                if isinstance(item, dict):
                    extracted = item
                    break

        full_text = extracted.get(
            "full_text",
            ""
        )

        metadata = extracted.get(
            "metadata",
            {}
        )

        # ====================================================
        # EMPTY EXTRACTION CHECK
        # ====================================================

        if not full_text:
            raise ValueError(
                "No extracted text"
            )

        if len(full_text.strip()) < 300:
            raise ValueError(
                "Extracted text too short"
            )

        page_count = metadata.get(
            "page_count",
            0
        )

        word_count = len(full_text.split())

        # ====================================================
        # SECTION PARSING
        # ====================================================

        sections = segment_sections(full_text)

        # ====================================================
        # LAYER 1
        # ====================================================

        layer1_result = run_editorial_rules(
            sections=sections,
            metadata=metadata,
            text=full_text,
        )

        # ====================================================
        # FEATURE ENGINEERING
        # ====================================================

        editorial_features = compute_editorial_features(
            sections=sections,
            metadata=metadata,
            text=full_text,
        )

        # ====================================================
        # LAYER 2 - QWEN
        # ====================================================

        qwen_result = run_qwen_scoring(
            sections=sections,
            features=editorial_features,
            full_text=full_text[:12000],
            prompt_version="v5",
        )

        # ====================================================
        # FLATTEN QWEN OUTPUT
        # ====================================================

        qwen_flat = flatten_qwen_v5(qwen_result)

        # ====================================================
        # SAFE FEATURE EXTRACTION
        # ====================================================

        missing_sections_count = safe_missing_sections_count(
            editorial_features
        )

        reference_count = (
            editorial_features
            .get("quality_indicators", {})
            .get("reference_count", 0)
        )

        # ====================================================
        # BUILD ROW
        # ====================================================

        row = {

            # BASIC INFO
            "filename": os.path.basename(pdf_path),

            "conference": entry.get(
                "conference"
            ),

            "true_label": true_label,

            # DOCUMENT FEATURES
            "page_count": page_count,

            "word_count": word_count,

            "missing_critical_sections_count":
                missing_sections_count,

            "reference_count":
                reference_count,
        }

        # ====================================================
        # FLATTEN SECTION PRESENCE
        # ====================================================

        sections_present = editorial_features.get(
            "sections_present",
            {}
        )

        for sec_name, present in sections_present.items():

            row[f"has_section_{sec_name}"] = int(
                bool(present)
            )

        # ====================================================
        # MERGE QWEN FEATURES
        # ====================================================

        row.update(qwen_flat)

        return row

    except Exception as e:

        source_file = entry.get(
            "asset_path",
            "Unknown"
        )

        print(
            f"ERROR processing file "
            f"'{source_file}': {str(e)}"
        )

        with open(
            FAILED_LOG,
            "a",
            encoding="utf-8"
        ) as f:

            f.write("=" * 80 + "\n")

            f.write(str(entry) + "\n")

            f.write(str(e) + "\n")

            f.write(traceback.format_exc())

            f.write("\n\n")

        return None


# ============================================================
# PROCESS SPLIT
# ============================================================

def process_split(
    split_name,
    entries,
    output_csv
):

    rows = []

    print("\n" + "=" * 60)

    print(f"PROCESSING SPLIT: {split_name}")

    print("=" * 60)

    for entry in tqdm(entries):

        row = process_pdf(entry)

        if row:
            rows.append(row)

    df = pd.DataFrame(rows)

    df.to_csv(
        output_csv,
        index=False
    )

    print(f"\nSaved: {output_csv}")

    print(f"Rows: {len(df)}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print("BUILDING LAYER 3 DATASET")

    print("=" * 60)

    train_entries = manifest["train"]

    val_entries = manifest["val"]

    test_entries = manifest["test"]

    # ========================================================
    # TRAIN
    # ========================================================

    process_split(
        split_name="train",
        entries=train_entries,
        output_csv=TRAIN_OUTPUT,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    process_split(
        split_name="validation",
        entries=val_entries,
        output_csv=VAL_OUTPUT,
    )

    # ========================================================
    # TEST
    # ========================================================

    process_split(
        split_name="test",
        entries=test_entries,
        output_csv=TEST_OUTPUT,
    )

    print("\nDONE.")


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()