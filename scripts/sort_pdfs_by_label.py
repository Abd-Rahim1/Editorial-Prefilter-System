"""
Deep-Structured Dataset Asset Organizer
Copies PeerRead documents and reviews into nested, label-driven conference subfolders.
"""

import os
import json
import shutil
from pathlib import Path

# Source configuration (where your raw PeerRead download sits)
DATA_DIR = r"C:\Users\Document\OneDrive\Desktop\TFG\Dataset\PeerRead\data"

# Target output folder inside your project
TARGET_BASE_DIR = r"C:\Users\Document\OneDrive\Desktop\TFG\Project\data\peerread"

def parse_peerread_label(review_data):
    """Deep parses PeerRead metadata to find acceptance decisions."""
    if "accepted" in review_data:
        val = review_data["accepted"]
        if val is True or str(val).lower() in ["true", "yes", "accept", "accepted"]: return 1
        if val is False or str(val).lower() in ["false", "no", "reject", "rejected"]: return 0
    if "decision" in review_data:
        decision = str(review_data["decision"]).lower()
        if "accept" in decision: return 1
        if "reject" in decision: return 0

    reviews = review_data.get("reviews", [])
    if isinstance(reviews, (list, dict)):
        iterable = reviews if isinstance(reviews, list) else reviews.values()
        for rev in iterable:
            if isinstance(rev, dict):
                if "accepted" in rev:
                    val = str(rev["accepted"]).lower()
                    if "accept" in val or val == "yes" or val == "true": return 1
                    if "reject" in val or val == "no" or val == "false": return 0
                if "RECOMMENDATION" in rev:
                    try:
                        score = int(rev["RECOMMENDATION"])
                        if score >= 4: return 1
                        if score <= 2: return 0
                    except ValueError:
                        pass
    return None

def sort_dataset_into_deep_structure():
    base_path = Path(DATA_DIR)
    target_base = Path(TARGET_BASE_DIR)
    
    conferences = [d.name for d in base_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    splits = ["train", "dev", "test"]
    
    copied_accepted = 0
    copied_rejected = 0
    
    print("==========================================================")
    print("STARTING DEEP-STRUCTURED COPY PROCESS")
    print("==========================================================")
    print(f"Source: {base_path.resolve()}")
    print(f"Target: {target_base.resolve()}\n")
    
    for conf in sorted(conferences):
        conf_path = base_path / conf
        conf_copied = 0
        
        for split in splits:
            split_path = conf_path / split
            reviews_path = split_path / "reviews"
            pdfs_path = split_path / "pdfs"
            parsed_path = split_path / "parsed_pdfs"
            
            if not reviews_path.exists():
                continue
                
            for json_file in reviews_path.glob("*.json"):
                paper_id = json_file.stem
                
                # Identify asset type (PDF or Arxiv Parsed Text)
                asset_found = False
                source_asset = pdfs_path / f"{paper_id}.pdf"
                asset_folder_name = "pdfs"
                dest_asset_name = f"{conf}_{paper_id}.pdf"
                
                if source_asset.exists():
                    asset_found = True
                elif parsed_path.exists():
                    possible_txts = list(parsed_path.glob(f"{paper_id}.*"))
                    if possible_txts:
                        source_asset = possible_txts[0]
                        asset_folder_name = "parsed_pdfs"
                        dest_asset_name = f"{conf}_{paper_id}{source_asset.suffix}"
                        asset_found = True
                
                if not asset_found:
                    continue
                    
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        review_data = json.load(f)
                except Exception:
                    continue
                
                label = parse_peerread_label(review_data)
                if label is None:
                    continue
                
                # Determine top-level classification path (accepted vs rejected)
                label_dir_name = "accepted" if label == 1 else "rejected"
                
                # Dynamically construct the nested directory structure
                target_review_dir = target_base / label_dir_name / conf / "reviews"
                target_asset_dir = target_base / label_dir_name / conf / asset_folder_name
                
                # Ensure the specific nested destination directories exist
                target_review_dir.mkdir(parents=True, exist_ok=True)
                target_asset_dir.mkdir(parents=True, exist_ok=True)
                
                # Define destination filenames with unique conference prefixes
                dest_json_name = f"{conf}_{paper_id}.json"
                
                # Copy files into their distinct target subdirectories
                shutil.copy2(source_asset, target_asset_dir / dest_asset_name)
                shutil.copy2(json_file, target_review_dir / dest_json_name)
                
                if label == 1:
                    copied_accepted += 1
                else:
                    copied_rejected += 1
                conf_copied += 1

        if conf_copied > 0:
            print(f" Structured {conf_copied} papers from {conf}")

    print("\n==========================================================")
    print("STRUCUTRED EXPORT SUMMARY")
    print("==========================================================")
    print(f"Total Accepted Papers Structured: {copied_accepted}")
    print(f"Total Rejected Papers Structured: {copied_rejected}")
    print(f"Total Files Placed inside Target: {(copied_accepted + copied_rejected) * 2}")
    print(f"Output Base Root: {target_base.resolve()}")
    print("==========================================================")

if __name__ == "__main__":
    sort_dataset_into_deep_structure()