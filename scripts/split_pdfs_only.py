"""
PDF-Only Dataset 3-Way Stratified Splitter
Filters out Arxiv parsed folders to strictly build a train/val/test map for raw PDF files.
"""

import os
import json
import random
from pathlib import Path

# Main paths
PEERREAD_ROOT = r"C:\Users\Document\OneDrive\Desktop\TFG\Project\data\peerread"
MANIFEST_OUT = r"C:\Users\Document\OneDrive\Desktop\TFG\Project\data\peerread_pdfs_only_manifest.json"

def build_pdf_only_split(train_ratio=0.70, val_ratio=0.15):
    base_path = Path(PEERREAD_ROOT)
    
    if not base_path.exists():
        print(f"Error: Organized root path not found at {base_path.resolve()}")
        return

    accepted_pairs = []
    rejected_pairs = []

    print("Filtering subfolders to scan RAW PDFs only...")
    for label_dir in ["accepted", "rejected"]:
        label_path = base_path / label_dir
        if not label_path.exists():
            continue
            
        for conf_dir in label_path.iterdir():
            if not conf_dir.is_dir():
                continue
                
            reviews_dir = conf_dir / "reviews"
            pdfs_dir = conf_dir / "pdfs"
            
            # CRITICAL FILTER: Skip Arxiv folders that only contain 'parsed_pdfs'
            if not pdfs_dir.exists() or not reviews_dir.exists():
                continue

            for json_file in reviews_dir.glob("*.json"):
                paper_id_with_prefix = json_file.stem
                
                # Check for the matching physical .pdf binary file
                matching_pdfs = list(pdfs_dir.glob(f"{paper_id_with_prefix}.pdf"))
                if not matching_pdfs:
                    continue
                    
                pair_info = {
                    "conference": conf_dir.name,
                    "review_path": str(json_file.relative_to(base_path)),
                    "asset_path": str(matching_pdfs[0].relative_to(base_path))
                }
                
                if label_dir == "accepted":
                    accepted_pairs.append(pair_info)
                else:
                    rejected_pairs.append(pair_info)

    print(f"-> Found {len(accepted_pairs)} Labeled PDF Pairs in 'accepted/' subfolders.")
    print(f"-> Found {len(rejected_pairs)} Labeled PDF Pairs in 'rejected/' subfolders.")

    # Apply standard fixed seed for experiment reproducibility
    random.seed(42)
    random.shuffle(accepted_pairs)
    random.shuffle(rejected_pairs)

    # Compute stratification boundary metrics for 3-way split (Accepted)
    acc_total = len(accepted_pairs)
    idx_acc_train = int(acc_total * train_ratio)
    idx_acc_val = idx_acc_train + int(acc_total * val_ratio)

    # Compute stratification boundary metrics for 3-way split (Rejected)
    rej_total = len(rejected_pairs)
    idx_rej_train = int(rej_total * train_ratio)
    idx_rej_val = idx_rej_train + int(rej_total * val_ratio)

    # Allocate pairs cleanly into partitions
    train_set = accepted_pairs[:idx_acc_train] + rejected_pairs[:idx_rej_train]
    val_set = accepted_pairs[idx_acc_train:idx_acc_val] + rejected_pairs[idx_rej_train:idx_rej_val]
    test_set = accepted_pairs[idx_acc_val:] + rejected_pairs[idx_rej_val:]

    # Interleave files inside the split partitions
    random.shuffle(train_set)
    random.shuffle(val_set)
    random.shuffle(test_set)

    manifest = {
        "summary": {
            "total_pdf_papers": len(train_set) + len(val_set) + len(test_set),
            "train_samples": len(train_set),
            "val_samples": len(val_set),
            "test_samples": len(test_set),
            "stratification_ratio": "70/15/15",
            "train_distribution": {
                "accepted": len([x for x in train_set if "accepted" in x["review_path"]]),
                "rejected": len([x for x in train_set if "rejected" in x["review_path"]])
            },
            "val_distribution": {
                "accepted": len([x for x in val_set if "accepted" in x["review_path"]]),
                "rejected": len([x for x in val_set if "rejected" in x["review_path"]])
            },
            "test_distribution": {
                "accepted": len([x for x in test_set if "accepted" in x["review_path"]]),
                "rejected": len([x for x in test_set if "rejected" in x["review_path"]])
            }
        },
        "train": train_set,
        "val": val_set,
        "test": test_set
    }

    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    print("\n==========================================================")
    print("PDF-ONLY 3-WAY STRATIFIED SHUFFLE COMPLETED")
    print("==========================================================")
    print(f"  Training Set Size (70%):   {manifest['summary']['train_samples']} papers")
    print(f"    - Accepted PDFs: {manifest['summary']['train_distribution']['accepted']}")
    print(f"    - Rejected PDFs: {manifest['summary']['train_distribution']['rejected']}")
    print(f"  Validation Set Size (15%): {manifest['summary']['val_samples']} papers")
    print(f"    - Accepted PDFs: {manifest['summary']['val_distribution']['accepted']}")
    print(f"    - Rejected PDFs: {manifest['summary']['val_distribution']['rejected']}")
    print(f"  Testing Set Size (15%):    {manifest['summary']['test_samples']} papers")
    print(f"    - Accepted PDFs: {manifest['summary']['test_distribution']['accepted']}")
    print(f"    - Rejected PDFs: {manifest['summary']['test_distribution']['rejected']}")
    print("----------------------------------------------------------")
    print(f"PDF Manifest Blueprint Map Saved: {Path(MANIFEST_OUT).resolve()}")
    print("==========================================================")

if __name__ == "__main__":
    build_pdf_only_split()