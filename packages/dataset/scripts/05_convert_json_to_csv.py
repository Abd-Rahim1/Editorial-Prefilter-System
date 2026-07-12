"""
Script 05: Convert Raw JSON to Schema-Aligned CSV
Phase 2 - CSV Conversion with Strict Schema Mapping

Reads:  data/processed/pipeline_output_raw.json (JSONL)
Applies STRICT Schema Mapping.
Flattens nested rule_checks array into binary columns:
  rule_{rule_name}_passed = 1 if passed else 0

Saves to: data/processed/dataset.csv  <-- (RENAMED HERE)

Run from project root:
    python packages/dataset/scripts/05_convert_json_to_csv.py
"""

import os
import json
import re
import pathlib
import pandas as pd
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--prompt", choices=["v1", "v5", "freetext"], default="v5", help="Prompt version to convert.")
parser.add_argument("--model", choices=["qwen3:4b", "qwen3.5:35b", "qwen3.6:latest"], default="qwen3:4b", help="Qwen model to use.")
args = parser.parse_args()
prompt_version = args.prompt
model_choice = args.model

PROJECT_ROOT   = pathlib.Path(__file__).resolve().parents[3]
OUTPUT_DIR     = PROJECT_ROOT / "data" / "processed"
FALLBACK_JSONL = PROJECT_ROOT / "data" / "pipeline_master_output.jsonl"

if prompt_version == "v1":
    PRIMARY_JSONL = OUTPUT_DIR / "processed_data_v1.json"
    OUTPUT_CSV    = OUTPUT_DIR / "dataset_v1.csv"
elif prompt_version == "freetext":
    PRIMARY_JSONL = OUTPUT_DIR / "processed_data_freetext.json"
    OUTPUT_CSV    = OUTPUT_DIR / "dataset_freetext.csv"
else:  # v5
    if model_choice == "qwen3.5:35b":
        PRIMARY_JSONL = OUTPUT_DIR / "processed_data_qwen_35b.json"
        OUTPUT_CSV    = OUTPUT_DIR / "dataset_qwen_35b.csv"
    elif model_choice == "qwen3.6:latest":
        PRIMARY_JSONL = OUTPUT_DIR / "processed_data_qwen_latest.json"
        OUTPUT_CSV    = OUTPUT_DIR / "dataset_qwen_latest.csv"
    else:
        PRIMARY_JSONL = OUTPUT_DIR / "processed_data.json"
        OUTPUT_CSV    = OUTPUT_DIR / "dataset.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_robust_jsonl(filepath):
    """Safely loads standard JSON Arrays or JSONL (Newline Delimited JSON)."""
    data = []
    if not filepath.exists():
        return data
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        
    if not content:
        return data
        
    # Split by closing/opening brackets if multiple JSON objects are concatenated
    json_strings = re.split(r'\}\s*\{', content)
    
    for i, j_str in enumerate(json_strings):
        if i > 0: j_str = '{' + j_str
        if i < len(json_strings) - 1: j_str = j_str + '}'
            
        try:
            data.append(json.loads(j_str))
        except json.JSONDecodeError as e:
            print(f"[WARNING] Skipping a malformed JSON block: {e}")
            
    return data

def main():
    target_json = PRIMARY_JSONL if PRIMARY_JSONL.exists() else FALLBACK_JSONL
    if not target_json.exists():
        print(f"[ERROR] No input JSON found at {target_json}")
        return
        
    print(f"[05] Loading raw JSON from: {target_json}")
    raw_data = load_robust_jsonl(target_json)
    print(f"[05] Loaded {len(raw_data)} manuscript records.")
    
    if len(raw_data) == 0:
        return

    rows = []
    for item in raw_data:
        row = {
            "filename": item.get("filename", "unknown"),
            "conference": item.get("conference", "unknown"),
            "ground_truth": item.get("ground_truth", 0),
            "format_failure": item.get("format_failure", 0),
            
            # Qualitative (Strict Schema Mapping)
            "abstract_clarity": item.get("abstract_clarity", item.get("content_coherence_score", 0.5)),
            "structural_completeness": item.get("structural_completeness", item.get("structure_validity_score", 0.5)),
            "methodological_strength": item.get("methodological_strength", item.get("citation_quality_score", 0.5)),
            "experimental_strength": item.get("experimental_strength", item.get("reproducibility_signal_score", 0.5)),
            "argumentative_quality": item.get("argumentative_quality", 0.5),
            "scope_alignment": item.get("scope_alignment", item.get("research_paper_likelihood", 0.5)),
            "overall_quality": item.get("overall_quality", 0.5),
        }

        # Dynamic Rule Flattening
        rule_checks = item.get("rule_checks", [])
        
        row["total_rules_failed"] = len([r for r in rule_checks if not r.get("passed", True)])
        row["critical_rules_failed"] = len([r for r in rule_checks if not r.get("passed", True) and r.get("severity") == "critical"])
        
        for rc in rule_checks:
            rname = rc.get("rule_name", "").strip().lower().replace(" ", "_").replace("-", "_")
            if not rname: continue
            
            passed_val = rc.get("passed", False)
            row[f"rule_{rname}_passed"] = 1 if passed_val else 0

        # Feature Engineering: Interaction Column
        row["risk_multiplier"] = row["total_rules_failed"] * (1.0 - row["overall_quality"])

        rows.append(row)

    df = pd.DataFrame(rows)
    
    priority_cols = [
        "filename", "conference", "ground_truth", "format_failure",
        "total_rules_failed", "critical_rules_failed", "risk_multiplier"
    ]
    rule_cols = sorted([c for c in df.columns if c.startswith("rule_")])
    llm_cols = [
        "abstract_clarity", "structural_completeness", "methodological_strength", 
        "experimental_strength", "argumentative_quality", "scope_alignment", "overall_quality"
    ]
    
    final_order = priority_cols + llm_cols + rule_cols
    df = df[[c for c in final_order if c in df.columns]]

    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"[05] Shape: {df.shape}")
    print(f"[05] Successfully saved flattened data to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()