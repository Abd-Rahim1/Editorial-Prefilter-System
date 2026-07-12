"""
Global Dataset Counter and Verification Utility
Deep-parses PeerRead JSON schemas across all conference subfolders.
"""

import os
import json
from pathlib import Path

# Global absolute path to your dataset folder
DEFAULT_DATA_DIR = r"C:\Users\Document\OneDrive\Desktop\TFG\Dataset\PeerRead\data"

def parse_peerread_label(review_data):
    """
    Deep parses PeerRead metadata across different schemas.
    Returns 1 for Accept, 0 for Reject, and None if completely unlabeled.
    """
    # 1. Check root level attributes (ICLR / Arxiv schema)
    if "accepted" in review_data:
        val = review_data["accepted"]
        if val is True or str(val).lower() in ["true", "yes", "accept", "accepted"]: 
            return 1
        if val is False or str(val).lower() in ["false", "no", "reject", "rejected"]: 
            return 0
        
    if "decision" in review_data:
        decision = str(review_data["decision"]).lower()
        if "accept" in decision: return 1
        if "reject" in decision: return 0

    # 2. Check nested reviews array/dict (ACL / CoNLL schema)
    reviews = review_data.get("reviews", [])
    if isinstance(reviews, list) and len(reviews) > 0:
        for rev in reviews:
            if not isinstance(rev, dict):
                continue
            
            # Check for explicit accepted string inside the review object
            if "accepted" in rev:
                val = str(rev["accepted"]).lower()
                if "accept" in val or val == "yes" or val == "true": return 1
                if "reject" in val or val == "no" or val == "false": return 0
            
            # Fallback: Check recommendation scores if formal decision strings are missing
            if "RECOMMENDATION" in rev:
                try:
                    score = int(rev["RECOMMENDATION"])
                    # On a typical 1-5 or 1-10 scale, 3+ or 4+ usually marks an acceptance baseline
                    if score >= 4: return 1
                    if score <= 2: return 0
                except ValueError:
                    pass

    return None

def count_global_dataset(data_dir: str = DEFAULT_DATA_DIR):
    base_path = Path(data_dir)
    
    if not base_path.exists():
        print(f"Error: Dataset directory not found at: {base_path.resolve()}")
        return

    conferences = [d.name for d in base_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    splits = ["train", "dev", "test"]
    
    grand_accepted = 0
    grand_rejected = 0
    grand_missing = 0
    grand_unlabeled = 0
    
    print("==========================================================================================")
    print("GLOBAL PEERREAD DATASET DISCOVERY AND LABEL VERIFICATION")
    print("==========================================================================================")
    print(f"Dataset Location: {base_path.resolve()}")
    print(f"Detected {len(conferences)} Conference Subfolders")
    print("------------------------------------------------------------------------------------------")
    
    header_fmt = "{:<25} | {:<8} | {:<8} | {:<12} | {:<10} | {:<10}"
    row_fmt =    "{:<25} | {:<8} | {:<8} | {:<12} | {:<10} | {:<10}"
    
    print(header_fmt.format("Conference / Dataset", "Accept", "Reject", "Missing PDF", "Unlabeled", "Total"))
    print("------------------------------------------------------------------------------------------")

    for conf in sorted(conferences):
        conf_accepted = 0
        conf_rejected = 0
        conf_missing = 0
        conf_unlabeled = 0
        
        conf_path = base_path / conf
        
        for split in splits:
            split_path = conf_path / split
            reviews_path = split_path / "reviews"
            parsed_path = split_path / "parsed_pdfs"
            pdfs_path = split_path / "pdfs"
            
            if not reviews_path.exists():
                continue
                
            for json_file in reviews_path.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        review_data = json.load(f)
                except Exception:
                    conf_unlabeled += 1
                    continue
                
                paper_id = json_file.stem
                
                # Check if text content assets exist
                has_txt = list(parsed_path.glob(f"{paper_id}.*")) != [] if parsed_path.exists() else False
                has_pdf = (pdfs_path / f"{paper_id}.pdf").exists() if pdfs_path.exists() else False
                
                if not has_txt and not has_pdf:
                    conf_missing += 1
                    continue
                    
                label = parse_peerread_label(review_data)
                if label == 1:
                    conf_accepted += 1
                elif label == 0:
                    conf_rejected += 1
                else:
                    conf_unlabeled += 1
                    
        conf_total = conf_accepted + conf_rejected + conf_missing + conf_unlabeled
        
        if conf_total > 0:
            print(row_fmt.format(
                conf, 
                conf_accepted, 
                conf_rejected, 
                conf_missing, 
                conf_unlabeled, 
                conf_total
            ))
            
            grand_accepted += conf_accepted
            grand_rejected += conf_rejected
            grand_missing += conf_missing
            grand_unlabeled += conf_unlabeled

    print("==========================================================================================")
    print("AGGREGATED METRICS SUMMARY REPORT")
    print("==========================================================================================")
    print(f"  Total Accepted Papers:  {grand_accepted}")
    print(f"  Total Rejected Papers:  {grand_rejected}")
    print(f"  Total Missing Papers:   {grand_missing} (No extractable text assets available)")
    print(f"  Total Unlabeled Papers: {grand_unlabeled}")
    print("------------------------------------------------------------------------------------------")
    
    usable_total = grand_accepted + grand_rejected
    print(f"  GRAND TOTAL USABLE PAPERS FOR TRAINING (ALL CONFERENCES): {usable_total}")
    print("==========================================================================================")

if __name__ == "__main__":
    count_global_dataset()