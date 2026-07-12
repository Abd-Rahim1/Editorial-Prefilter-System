import pandas as pd
import json
from pathlib import Path
from src.database.connection import get_connection, get_cursor

def main():
    print("=" * 60)
    print("PREPARING LAYER 3 TRAINING DATASET")
    print("=" * 60)
    
    # 1. Load Ground Truth Labels from PeerRead directory
    label_dict = {}
    peerread_dir = Path(r"C:\Users\Document\OneDrive\Desktop\TFG\Dataset\PeerRead\data")
    
    files_found = 0
    examples_printed = 0
    
    if not peerread_dir.exists():
        print("Warning: PeerRead data directory not found.")
    else:
        for review_file in peerread_dir.rglob("reviews/*.json"):
            if review_file.name.endswith(".meta.json"):
                continue
            
            try:
                with open(review_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                files_found += 1
                paper_id = review_file.stem
                label = None
                decision_val = None
                
                # Check root fields
                if "accepted" in data:
                    decision_val = data["accepted"]
                    if isinstance(decision_val, bool):
                        label = 1 if decision_val else 0
                    elif isinstance(decision_val, str):
                        label = 1 if decision_val.lower() in ["true", "accept", "accepted"] else 0
                elif "decision" in data:
                    decision_val = data["decision"]
                    if isinstance(decision_val, str):
                        label = 1 if "accept" in decision_val.lower() else 0
                
                # Check reviews list
                if label is None and "reviews" in data and isinstance(data["reviews"], list):
                    # Try to find a decision or recommendation in the first review or average them
                    recs = []
                    for r in data["reviews"]:
                        if "RECOMMENDATION" in r:
                            val = r["RECOMMENDATION"]
                            try:
                                recs.append(float(val))
                            except ValueError:
                                if isinstance(val, str) and "accept" in val.lower():
                                    label = 1
                                    decision_val = val
                                    break
                                elif isinstance(val, str) and "reject" in val.lower():
                                    label = 0
                                    decision_val = val
                                    break
                    
                    if label is None and recs:
                        avg_rec = sum(recs) / len(recs)
                        decision_val = f"avg_recommendation={avg_rec:.2f}"
                        label = 1 if avg_rec >= 3.5 else 0  # Assuming 1-5 scale, 3.5+ is accept
                        
                if label is not None:
                    label_dict[paper_id] = label
                    
                    if examples_printed < 2:
                        print(f"DEBUG: Found label file: {review_file}")
                        print(f"DEBUG: JSON keys: {list(data.keys())}")
                        print(f"DEBUG: Paper ID: {paper_id}")
                        print(f"DEBUG: Decision field used: {decision_val}")
                        print(f"DEBUG: Parsed label: {label}")
                        print("-" * 40)
                        examples_printed += 1
                        
            except Exception as e:
                pass
                
    print(f"Total label files parsed: {files_found}")
    print(f"Total labels mapped: {len(label_dict)}")
    
    # 2. Connect to database
    try:
        conn = get_connection()
        cur = get_cursor(conn)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return
        
    # Get all model runs joined with manuscripts
    query = """
        SELECT m.id as ms_id, m.filename, m.num_pages, m.total_word_count,
               r.id as run_id, r.prompt_version, r.parsed_output
        FROM manuscripts m
        JOIN model_runs r ON m.id = r.manuscript_id
        WHERE r.parsed_output IS NOT NULL
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    paper_runs = {}
    for r in rows:
        filename = r['filename']
        parsed = r['parsed_output']
        
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except:
                continue
        if not isinstance(parsed, dict) or not parsed:
            continue
            
        # Ensure it has Qwen scores (overall_quality or recommendation)
        if "recommendation" not in parsed and "overall_quality" not in parsed and "abstract_clarity" not in parsed:
            continue
            
        r['parsed_dict'] = parsed
        
        if filename not in paper_runs:
            paper_runs[filename] = []
        paper_runs[filename].append(r)
    
    final_manuscripts = []
    duplicates_removed = 0
    
    for filename, runs in paper_runs.items():
        if len(runs) > 1:
            duplicates_removed += (len(runs) - 1)
        # Sort to prefer prompt_version='v3', then latest run_id
        runs.sort(key=lambda x: (1 if x['prompt_version'] == 'v3' else 2, -x['run_id']))
        final_manuscripts.append(runs[0])
    
    dataset = []
    missing_labels = 0
    accepted_papers = 0
    rejected_papers = 0
    
    for ms in final_manuscripts:
        ms_id = ms['ms_id']
        filename = ms['filename']
        parsed = ms['parsed_dict']
        
        paper_id = filename.replace('.pdf', '')
        
        if paper_id in label_dict:
            true_label = label_dict[paper_id]
            if true_label == 1:
                accepted_papers += 1
            else:
                rejected_papers += 1
        else:
            true_label = None
            missing_labels += 1
            
        # Get Layer 1 editorial features
        cur.execute("SELECT feature_name, feature_value FROM editorial_features WHERE manuscript_id = %s", (ms_id,))
        feats = cur.fetchall()
        feat_dict = {f['feature_name']: f['feature_value'] for f in feats}
        
        # Get Layer 1 rule checks (hard decision)
        cur.execute("SELECT severity FROM rule_checks WHERE manuscript_id = %s", (ms_id,))
        rules = cur.fetchall()
        hard_reject = any(r['severity'] == 'high' for r in rules)
        hard_decision = "reject" if hard_reject else "accept"
        
        layer1_verification = parsed.get("layer1_verification", {}) if isinstance(parsed.get("layer1_verification"), dict) else {}
        
        row = {
            "manuscript_id": ms_id,
            "filename": filename,
            "paper_id": paper_id,
            "true_label": true_label,
            
            # Layer 1 Features
            "hard_rule_decision": hard_decision,
            "missing_critical_sections": feat_dict.get("missing_critical_sections", 0),
            "has_abstract": feat_dict.get("has_abstract", 0),
            "has_introduction": feat_dict.get("has_introduction", 0),
            "has_methodology": feat_dict.get("has_methodology", 0),
            "has_experiments": feat_dict.get("has_experiments", 0),
            "has_conclusions": feat_dict.get("has_conclusions", 0),
            "word_count": ms['total_word_count'],
            "page_count": ms['num_pages'],
            
            # Layer 2 Features
            "abstract_clarity": parsed.get("abstract_clarity", None),
            "structural_completeness": parsed.get("structural_completeness", None),
            "methodological_strength": parsed.get("methodological_strength", None),
            "experimental_strength": parsed.get("experimental_strength", None),
            "argumentative_quality": parsed.get("argumentative_quality", None),
            "scope_alignment": parsed.get("scope_alignment", None),
            "overall_quality": parsed.get("overall_quality", None),
            "suspicious_score": parsed.get("suspicious_score", None),
            "credibility_score": parsed.get("credibility_score", None),
            "evidence_strength": parsed.get("evidence_strength", None),
            "coherence_score": parsed.get("coherence_score", None),
            "reproducibility_score": parsed.get("reproducibility_score", None),
            "theoretical_rigor_score": parsed.get("theoretical_rigor_score", None),
            "methodology_missing_confirmed": layer1_verification.get("methodology_missing_confirmed", None),
            "methodology_like_content_found_elsewhere": layer1_verification.get("methodology_like_content_found_elsewhere", None),
            "qwen_recommendation": parsed.get("recommendation", None),
        }
        
        dataset.append(row)
        
    cur.close()
    conn.close()
    
    df = pd.DataFrame(dataset)
    
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    output_csv = output_dir / "layer3_training_dataset.csv"
    
    df.to_csv(output_csv, index=False, encoding='utf-8')
    
    print(f"Total unique papers:      {len(df)}")
    print(f"Accepted papers:          {accepted_papers}")
    print(f"Rejected papers:          {rejected_papers}")
    print(f"Duplicates removed:       {duplicates_removed}")
    print(f"Missing labels:           {missing_labels}")
    print(f"Output CSV path:          {output_csv.absolute()}")
    print("=" * 60)

    if accepted_papers > 0 and rejected_papers == 0:
        print("\nWARNING: Only one class found. Layer 3 classifier cannot be trained yet.")
    elif rejected_papers > 0 and accepted_papers == 0:
        print("\nWARNING: Only one class found. Layer 3 classifier cannot be trained yet.")

if __name__ == "__main__":
    main()
