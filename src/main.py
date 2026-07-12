"""
Editorial Pre-filtering System - Main Entry Point
"""

import json
import argparse
from pathlib import Path

from src.pipeline.pipeline import process_manuscript, EditorialPipeline

def print_qwen_scores(qwen_scores: dict) -> None:
    print("\n" + "=" * 50)
    print("LAYER 2 - QWEN SCORES")
    print("=" * 50)
    
    ignore_keys = {"_meta", "prompt_text", "input_payload", "raw_output"}
    
    preferred_order = [
        "mode",
        "abstract_clarity",
        "structural_completeness",
        "methodological_strength",
        "experimental_strength",
        "argumentative_quality",
        "scope_alignment",
        "overall_quality",
        "suspicious_score",
        "credibility_score",
        "evidence_strength",
        "coherence_score",
        "reproducibility_score",
        "theoretical_rigor_score",
        "layer1_verification",
        "detected_issues",
        "detected_integrity_issues",
        "claim_validation",
        "evidence_spans",
        "recommendation",
    ]
    
    for key in preferred_order:
        if key in qwen_scores and key not in ignore_keys:
            val = qwen_scores[key]
            if isinstance(val, (dict, list)):
                print(f"\n{key}:")
                print(json.dumps(val, indent=2, ensure_ascii=False))
            else:
                print(f"{key}: {val}")
                
    extra_keys = [k for k in qwen_scores.keys() if k not in preferred_order and k not in ignore_keys]
    for key in extra_keys:
        val = qwen_scores[key]
        if isinstance(val, (dict, list)):
            print(f"\n{key}:")
            print(json.dumps(val, indent=2, ensure_ascii=False))
        else:
            print(f"{key}: {val}")

def compute_final_decision(result: dict) -> str:
    if result.get("recommendation") == "low_concern":
        return "ACCEPTABLE"
    elif result.get("recommendation") == "manual_review":
        return "REVIEW_NEEDED"
    else:
        return "HIGH_RISK"


def main():
    parser = argparse.ArgumentParser(description="Editorial Pre-filtering System")
    parser.add_argument("pdf_path", nargs="?", help="Path to a PDF file or a PeerRead dataset folder to process")
    parser.add_argument("prompt_version", nargs="?", default="v2", help="Qwen prompt version (v1, v2, v3, v4, v5)")
    parser.add_argument("--batch", action="store_true", help="Run on a batch of PeerRead papers")
    parser.add_argument("--split", type=str, default="dev", help="Dataset split to use for batch (train/dev/test)")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of papers to process in batch mode")

    args = parser.parse_args()

    if args.prompt_version not in ["v1", "v2", "v3", "v4", "v5"]:
        raise ValueError(f"Invalid prompt version: {args.prompt_version}. Must be one of ['v1', 'v2', 'v3', 'v4']")

    print("=" * 60)
    print("EDITORIAL PRE-FILTERING SYSTEM")
    print("=" * 60)
    print(f"Using prompt version: {args.prompt_version}")

    pipeline = EditorialPipeline()

    if args.pdf_path:
        target_path = Path(args.pdf_path)
        if not target_path.exists():
            print(f"\nError: Path not found - {args.pdf_path}")
            return

        if target_path.is_file() and target_path.suffix.lower() == ".pdf":
            print(f"\nProcessing single PDF: {target_path.name}")
            result = process_manuscript(str(target_path), save_to_db=True, prompt_version=args.prompt_version)

            if result.get("success"):
                print("\n" + "=" * 50)
                print("EDITORIAL PRE-FILTERING RESULT")
                print("=" * 50)

                metadata = result.get("metadata", {})
                print(f"\nFile: {metadata.get('filename', target_path.name)}")
                print(f"Pages: {metadata.get('num_pages', 'Unknown')}")
                print(f"Words: {metadata.get('total_word_count', 0)}")

                print("\nSections detected:")
                sections = result.get("sections", {})
                sections_found = [
                    k for k, v in sections.items()
                    if isinstance(v, str) and k != "title" and len(v.strip()) > 50
                ]
                if sections_found:
                    for section in sections_found:
                        print(f"- {section}")
                else:
                    print("- None")

                decision = "DESK REJECT" if result.get("decision") == "reject" else "SEND TO REVIEW"
                print(f"\nDecision:\n→ {decision}")

                print(f"\nReason:\n→ {result.get('reason', 'No reason provided')}")

                qwen_scores = result.get("qwen_scores")
                if qwen_scores:
                    print_qwen_scores(qwen_scores)
                    if "recommendation" in qwen_scores:
                        final_dec = compute_final_decision(qwen_scores)
                        print(f"\nFinal Layer 2 Decision: {final_dec}")

                manuscript_id = result.get("manuscript_id")
                if manuscript_id is not None:
                    print(f"\nSaved manuscript_id: {manuscript_id}")

                db_warning = metadata.get("db_warning")
                if db_warning:
                    print(f"\nDatabase warning: {db_warning}")

            else:
                print(f"\nError processing PDF: {result.get('error', 'Unknown error')}")

        elif target_path.is_dir():
            print(f"\nProcessing directory as dataset: {target_path}")
            print(f"Processing up to {args.limit} papers from {args.split} split...")
            results = pipeline.process_peerread_batch(split=args.split, limit=args.limit, prompt_version=args.prompt_version, data_dir=str(target_path))

            output_path = Path("./data/processed/batch_results.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            reject_by_rules = sum(1 for r in results if r.get("hard_rules_reject"))
            print("\nBatch Summary:")
            print(f"  Papers processed: {len(results)}")
            print(f"  Flagged for desk reject: {reject_by_rules}/{len(results)}")
            print(f"\n✓ Results saved to {output_path}")

    elif args.batch:
        peerread_path = Path("./data/peerread/")
        if not peerread_path.exists():
            print("\nPeerRead dataset not found at ./data/peerread/")
            print("Please ensure your dataset is located at: project/data/peerread/")
            return

        print(f"\nProcessing up to {args.limit} papers from {args.split} split...")
        results = pipeline.process_peerread_batch(split=args.split, limit=args.limit, prompt_version=args.prompt_version)

        output_path = Path("./data/processed/batch_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        reject_by_rules = sum(1 for r in results if r.get("hard_rules_reject"))
        print("\nBatch Summary:")
        print(f"  Papers processed: {len(results)}")
        print(f"  Flagged for desk reject: {reject_by_rules}/{len(results)}")
        print(f"\n✓ Results saved to {output_path}")

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python -m src.main path/to/paper.pdf      (Process a single PDF)")
        print("  python -m src.main path/to/dataset_folder (Process a PeerRead folder)")
        print("  python -m src.main --batch --limit 50     (Process default PeerRead batch)")


if __name__ == "__main__":
    main()