import sys
import json
import csv
from pathlib import Path

# Add project root to Python path for direct execution if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.pipeline.pipeline import process_manuscript


def normalize_decision(sys_result: dict) -> tuple[str, str]:
    """
    Normalize pipeline output into:
    - system_decision: ACCEPT / REJECT
    - reason: string
    Supports both old and refactored pipeline output formats.
    """
    # New/refactored shape
    hard_flags = sys_result.get("hard_flags", {})
    if isinstance(hard_flags, dict):
        decision = hard_flags.get("decision")
        reason = hard_flags.get("reason") or hard_flags.get("summary") or "No reason provided"

        if decision:
            decision = str(decision).strip().lower()
            if decision in {"accept", "review", "send_to_review", "send to review"}:
                return "ACCEPT", reason
            if decision in {"reject", "desk_reject", "desk reject"}:
                return "REJECT", reason

    # Old/simple shape fallback
    decision = sys_result.get("decision")
    reason = sys_result.get("reason", "No reason provided")

    if decision:
        decision = str(decision).strip().lower()
        if decision in {"accept", "review", "send_to_review", "send to review"}:
            return "ACCEPT", reason
        if decision in {"reject", "desk_reject", "desk reject"}:
            return "REJECT", reason

    # Final fallback: infer from text
    reason_text = str(reason).lower()
    if "desk reject" in reason_text or "reject" in reason_text:
        return "REJECT", reason
    return "ACCEPT", reason


def main():
    print("=" * 60)
    print("TESTING 10 PEERREAD PDFs (GROUND TRUTH COMPARISON)")
    print("=" * 60)

    pdf_dir = Path(r"C:\Users\Document\OneDrive\Desktop\TFG\Dataset\PeerRead\data\iclr_2017\train\pdfs")
    review_dir = Path(r"C:\Users\Document\OneDrive\Desktop\TFG\Dataset\PeerRead\data\iclr_2017\train\reviews")
    out_dir = Path("data/processed")

    if not pdf_dir.exists() or not review_dir.exists():
        print(
            "❌ Dataset directories not found! Ensure paths are correct.\n"
            f"PDFs: {pdf_dir}\n"
            f"Reviews: {review_dir}"
        )
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "test_10_results.csv"

    pdf_files = sorted(pdf_dir.glob("*.pdf"))[:10]
    if not pdf_files:
        print("❌ No PDFs found in the directory.")
        return

    results = []
    correct_count = 0
    mismatches = []

    print(f"\nProcessing {len(pdf_files)} papers...\n")

    for i, pdf_path in enumerate(pdf_files, start=1):
        paper_id = pdf_path.stem
        review_path = review_dir / f"{paper_id}.json"

        ground_truth = "UNKNOWN"
        if review_path.exists():
            with open(review_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                is_accepted = data.get("accepted", False)
                ground_truth = "ACCEPT" if is_accepted else "REJECT"

        print(f"[{i}/{len(pdf_files)}] Testing {pdf_path.name}... ", end="", flush=True)

        try:
            sys_result = process_manuscript(str(pdf_path))
        except Exception as e:
            print(f"❌ ERROR ({e})", flush=True)
            continue

        # If refactored pipeline exposes success, honor it
        if isinstance(sys_result, dict) and sys_result.get("success") is False:
            print("❌ ERROR", flush=True)
            continue

        sys_decision, reason = normalize_decision(sys_result)

        reason_clean = str(reason).replace("\n", " ").replace("\r", " ").strip()

        is_match = (sys_decision == ground_truth)

        if is_match:
            print("✅ MATCH", flush=True)
            correct_count += 1
        else:
            print("❌ MISMATCH", flush=True)
            mismatches.append(
                f"{paper_id}.pdf: System -> {sys_decision} | Actual -> {ground_truth}"
            )

        results.append({
            "paper_id": paper_id,
            "pdf_filename": pdf_path.name,
            "system_decision": sys_decision,
            "ground_truth": ground_truth,
            "match": is_match,
            "reason": reason_clean
        })

    with open(out_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "paper_id",
                "pdf_filename",
                "system_decision",
                "ground_truth",
                "match",
                "reason"
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    total_tested = len(results)
    accuracy = (correct_count / total_tested) * 100 if total_tested > 0 else 0

    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Papers Tested: {total_tested}")
    print(f"Correct Predictions: {correct_count}")
    print(f"Accuracy:            {accuracy:.2f}%\n")

    if mismatches:
        print("⚠️ MISMATCHES:")
        for m in mismatches:
            print(f" - {m}")
    else:
        print("🌟 Perfect Match!")

    print(f"\n📂 Results saved to {out_csv}")


if __name__ == "__main__":
    main()