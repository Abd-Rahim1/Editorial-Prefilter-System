"""
generate_parity_report.py
Generates the required training_serving_parity.csv report.
"""
import pandas as pd
import json
from pathlib import Path
from packages.calibration.common.constants import PACKAGE_ROOT
from packages.calibration.common.feature_contract import CANONICAL_C2_FEATURES
from packages.calibration.online.feature_builder import build_raw_features
from packages.calibration.online.feature_preprocessor import preprocess_features

def main():
    dataset_path = PACKAGE_ROOT.parent.parent / "data" / "prepared" / "dataset" / "dataset.csv"
    if not dataset_path.exists():
        print("Historical dataset.csv not found.")
        return
        
    df = pd.read_csv(dataset_path)
    
    reports_dir = PACKAGE_ROOT / "tests" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Load schema
    schema_path = PACKAGE_ROOT / "models" / "feature_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    rows_data = []
    
    for idx, row in df.head(50).iterrows():
        ms_id = f"MS-HISTORICAL-{idx}"
        
        l1 = {
            "total_rules_failed": row.get("total_rules_failed", 0.0),
            "critical_rules_failed": row.get("critical_rules_failed", 0.0),
            "conference": row.get("conference", 0.0)
        }
        l2 = {
            "overall_quality": row.get("overall_quality", 0.0),
            "argumentative_quality": row.get("argumentative_quality", 0.0),
            "experimental_strength": row.get("experimental_strength", 0.0),
            "methodological_strength": row.get("methodological_strength", 0.0),
            "scope_alignment": row.get("scope_alignment", 0.0),
            "structural_completeness": row.get("structural_completeness", 0.0)
        }
        
        raw_built = build_raw_features(layer1_output=l1, layer2_output=l2)
        X_online, _, _ = preprocess_features(raw_built, schema, strict_missing_check=False)
        
        for feature in CANONICAL_C2_FEATURES:
            prepared_value = float(row.get(feature, 0.0))
            online_value = float(X_online.iloc[0][feature])
            abs_diff = abs(prepared_value - online_value)
            
            rows_data.append({
                "manuscript_id": ms_id,
                "feature_name": feature,
                "prepared_value": prepared_value,
                "online_value": online_value,
                "absolute_difference": abs_diff,
                "match": abs_diff < 1e-9
            })
            
    out_df = pd.DataFrame(rows_data)
    out_df.to_csv(reports_dir / "training_serving_parity.csv", index=False)
    print("training_serving_parity.csv generated successfully.")

if __name__ == "__main__":
    main()
