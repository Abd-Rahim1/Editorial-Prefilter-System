"""
Script 02: Sort PeerRead Dataset by Label (PDF-only conferences)
Phase 1 - Raw Labeling

Source:
  C:/Users/Document/OneDrive/Desktop/TFG/Dataset/PeerRead/data
  Only processes conferences that have a physical pdfs/ folder:
    - acl_2017
    - conll_2016
    - iclr_2017

Output structure (data/peerread_filtered/):
  data/peerread_filtered/
  ├── accepted/
  │   ├── acl_2017/
  │   │   ├── pdfs/     ← physical PDF files
  │   │   └── reviews/  ← matching review JSONs
  │   ├── conll_2016/
  │   │   ├── pdfs/
  │   │   └── reviews/
  │   └── iclr_2017/
  │       ├── pdfs/
  │       └── reviews/
  └── rejected/
      ├── acl_2017/  ...
      ├── conll_2016/ ...
      └── iclr_2017/ ...

Logic per review JSON:
  1. Read "accepted" boolean field.
  2. Find matching physical PDF in sibling pdfs/ directory (same paper_id).
  3. Copy PDF  → data/peerread_filtered/{accepted|rejected}/{conference}/pdfs/{paper_id}.pdf
  4. Copy JSON → data/peerread_filtered/{accepted|rejected}/{conference}/reviews/{paper_id}.json

Run from project root:
    python packages/dataset/scripts/02_sort_dataset_by_label.py
"""

import os
import json
import shutil
import pathlib

PROJECT_ROOT  = pathlib.Path(__file__).resolve().parents[3]
PEERREAD_ROOT = pathlib.Path(r"C:\Users\Document\OneDrive\Desktop\TFG\Dataset\PeerRead\data")
OUTPUT_ROOT   = PROJECT_ROOT / "data" / "peerread_filtered"   # destination root

SPLITS = ["train", "dev", "test"]

# Only conferences that contain physical PDFs (skip arxiv-only datasets)
PDF_CONFERENCES = {"acl_2017", "conll_2016", "iclr_2017"}

for verdict in ("accepted", "rejected"):
    for conf in PDF_CONFERENCES:
        os.makedirs(OUTPUT_ROOT / verdict / conf / "pdfs",    exist_ok=True)
        os.makedirs(OUTPUT_ROOT / verdict / conf / "reviews", exist_ok=True)

copied_accepted  = 0
copied_rejected  = 0
skipped_no_pdf   = 0   # review found but no matching physical PDF
skipped_already  = 0   # destination already exists (resume-safe)
errors           = 0

for conf_dir in sorted(PEERREAD_ROOT.iterdir()):
    if not conf_dir.is_dir():
        continue

    conference_name = conf_dir.name

    # Skip non-PDF conferences (arxiv etc.)
    if conference_name not in PDF_CONFERENCES:
        print(f"[02] SKIP (no physical PDFs): {conference_name}")
        continue

    print(f"\n[02] Processing: {conference_name}")

    for split in SPLITS:
        reviews_dir = conf_dir / split / "reviews"
        pdfs_dir    = conf_dir / split / "pdfs"

        if not reviews_dir.exists():
            continue
        if not pdfs_dir.exists():
            print(f"     [WARN] No pdfs/ dir in {conference_name}/{split} — skipping split")
            continue

        review_files = sorted(reviews_dir.glob("*.json"))
        print(f"     split={split:<6}  reviews found: {len(review_files)}")

        for review_file in review_files:
            paper_id = review_file.stem          # e.g. "304", "acl_2017_104"

            try:
                with open(review_file, "r", encoding="utf-8") as f:
                    review_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"     [ERROR] Cannot parse {review_file.name}: {e}")
                errors += 1
                continue

            is_accepted = bool(review_data.get("accepted", False))
            verdict     = "accepted" if is_accepted else "rejected"

            pdf_src = pdfs_dir / f"{paper_id}.pdf"
            if not pdf_src.exists():
                skipped_no_pdf += 1
                print(f"     [SKIP] No PDF: {pdfs_dir.name}/{paper_id}.pdf")
                continue

            dest_pdf    = OUTPUT_ROOT / verdict / conference_name / "pdfs"    / pdf_src.name
            dest_review = OUTPUT_ROOT / verdict / conference_name / "reviews" / review_file.name

            pdf_copied = False
            if not dest_pdf.exists():
                shutil.copy2(pdf_src, dest_pdf)
                pdf_copied = True
            else:
                skipped_already += 1

            if not dest_review.exists():
                shutil.copy2(review_file, dest_review)

            label_str = "ACCEPT" if is_accepted else "REJECT"
            status    = "→ copied" if pdf_copied else "→ already exists"
            print(f"     [{label_str}] {paper_id}.pdf  {status}")

            if is_accepted:
                copied_accepted += 1
            else:
                copied_rejected += 1

total = copied_accepted + copied_rejected
print()
print("=" * 65)
print(f"[02] DONE")
print(f"     Accepted papers copied : {copied_accepted}")
print(f"     Rejected papers copied : {copied_rejected}")
print(f"     Total labeled          : {total}")
print(f"     Skipped (no PDF)       : {skipped_no_pdf}")
print(f"     Skipped (already done) : {skipped_already}")
print(f"     Errors                 : {errors}")
print(f"     Output root            : {OUTPUT_ROOT}")
if total > 0:
    print(f"     Accept rate            : {100*copied_accepted/total:.1f}%")
    print(f"     Reject rate            : {100*copied_rejected/total:.1f}%")

print()
print("[02] Output structure:")
for verdict in ("accepted", "rejected"):
    for conf in sorted(PDF_CONFERENCES):
        pdf_count    = len(list((OUTPUT_ROOT / verdict / conf / "pdfs").glob("*.pdf")))
        review_count = len(list((OUTPUT_ROOT / verdict / conf / "reviews").glob("*.json")))
        print(f"     {verdict}/{conf:12s}  pdfs={pdf_count:4d}  reviews={review_count:4d}")
