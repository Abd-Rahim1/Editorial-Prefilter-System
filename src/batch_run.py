import argparse
import csv
from pathlib import Path

from src.pipeline.pipeline import process_manuscript


def main():
    parser = argparse.ArgumentParser(description="Batch Runner for Editorial Pre-filtering System")
    parser.add_argument("folder_path", type=str, help="Path to the folder containing PDFs")
    parser.add_argument("prompt_version", type=str, choices=["v1", "v2", "v3", "v4"], help="Qwen prompt version (v1, v2, v3, v4)")
    parser.add_argument("limit", type=int, nargs="?", default=None, help="Optional limit on number of PDFs to process")

    args = parser.parse_args()

    folder_path = Path(args.folder_path)
    if not folder_path.is_dir():
        print(f"Error: {folder_path} is not a valid directory.")
        return

    pdf_files = list(folder_path.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {folder_path}")
        return

    if args.limit is not None:
        pdf_files = pdf_files[:args.limit]

    print("=" * 60)
    print("BATCH RUNNER - EDITORIAL PRE-FILTERING SYSTEM")
    print("=" * 60)
    print(f"Folder: {folder_path}")
    print(f"Prompt version: {args.prompt_version}")
    print(f"Total PDFs to process: {len(pdf_files)}")
    print("-" * 60)

    results = []
    successful = 0
    failed = 0

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name} ... ", end="", flush=True)
        try:
            res = process_manuscript(
                manuscript_pdf=str(pdf_file),
                save_to_db=True,
                prompt_version=args.prompt_version
            )
            
            success = res.get("success", False)
            qwen_scores = res.get("qwen_scores", {})
            layer1_verification = qwen_scores.get("layer1_verification", {}) if isinstance(qwen_scores, dict) else {}

            row = {
                "filename": pdf_file.name,
                "success": success,
                "decision": res.get("decision", ""),
                "probability": res.get("probability", ""),
                "prompt_version": args.prompt_version,
                "qwen_recommendation": qwen_scores.get("recommendation", "") if isinstance(qwen_scores, dict) else "",
                "methodology_missing_confirmed": layer1_verification.get("methodology_missing_confirmed", ""),
                "methodology_like_content_found_elsewhere": layer1_verification.get("methodology_like_content_found_elsewhere", ""),
                "overall_quality": qwen_scores.get("overall_quality", "") if isinstance(qwen_scores, dict) else "",
                "suspicious_score": qwen_scores.get("suspicious_score", "") if isinstance(qwen_scores, dict) else "",
                "credibility_score": qwen_scores.get("credibility_score", "") if isinstance(qwen_scores, dict) else "",
                "model_run_id": res.get("model_run_id", ""),
                "manuscript_id": res.get("manuscript_id", ""),
                "error": res.get("error", "")
            }
            results.append(row)

            if success:
                successful += 1
                print("SUCCESS")
            else:
                failed += 1
                print(f"FAILED ({res.get('error', 'Unknown Error')})")

        except Exception as e:
            failed += 1
            print("ERROR")
            results.append({
                "filename": pdf_file.name,
                "success": False,
                "prompt_version": args.prompt_version,
                "error": str(e)
            })

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    output_csv = output_dir / "batch_results.csv"

    fieldnames = [
        "filename", "success", "decision", "probability", "prompt_version",
        "qwen_recommendation", "methodology_missing_confirmed",
        "methodology_like_content_found_elsewhere", "overall_quality",
        "suspicious_score", "credibility_score", "model_run_id",
        "manuscript_id", "error"
    ]

    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print("=" * 60)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total PDFs processed: {len(pdf_files)}")
    print(f"Successful PDFs:      {successful}")
    print(f"Failed PDFs:          {failed}")
    print(f"Output CSV path:      {output_csv.absolute()}")


if __name__ == "__main__":
    main()
