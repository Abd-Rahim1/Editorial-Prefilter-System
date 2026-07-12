# ============================================================
# FILE: src/check_processed_data.py
# ============================================================

import os
import pandas as pd

OUTPUT_DIR = r"C:\Users\Document\OneDrive\Desktop\TFG\Project\data\processed"
SPLITS = ["train_dataset.csv", "val_dataset.csv", "test_dataset.csv"]

def inspect_datasets():
    print("=" * 60)
    print("🔍 DATASET INTEGRITY CHECKER FOR TFG PIPELINE")
    print("=" * 60)
    
    for filename in SPLITS:
        path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(path):
            print(f"❌ File not found: {filename}")
            continue
            
        # Read the file
        df = pd.read_csv(path)
        print(f"\n📊 Checking file: {filename}")
        print(f"   • Total Rows (Processed PDFs): {len(df)}")
        print(f"   • Total Feature Columns: {len(df.columns)}")
        
        # 1. Check Layer 1 Coverage (Hard Rules Indicators)
        l1_cols = [c for c in df.columns if c.startswith("has_section_")]
        if l1_cols:
            # Check how many rows filled these out
            l1_missing = df[l1_cols].isna().sum().sum()
            print(f"   • Layer 1 (Hard Rules): OK ({len(l1_cols)} indicator columns found, {l1_missing} missing values)")
        else:
            print("   • Layer 1 (Hard Rules): ⚠️ WARNING! No 'has_section_' columns detected.")

        # 2. Check Layer 2 Coverage (Qwen LLM Metrics)
        qwen_metrics = [
            "recommendation", "integrity_risk_score", 
            "content_coherence_score", "reproducibility_signal_score"
        ]
        
        # Ensure columns actually exist in the dataframe
        existing_qwen_cols = [c for c in qwen_metrics if c in df.columns]
        
        if existing_qwen_cols:
            # Count how many rows actually contain valid numbers/scores instead of being blank (NaN)
            filled_rows = df[existing_qwen_cols[0]].notna().sum()
            fill_percentage = (filled_rows / len(df)) * 100
            
            print(f"   • Layer 2 (Qwen LLM):   Found {len(existing_qwen_cols)} core metrics.")
            print(f"     👉 Successful LLM extractions: {filled_rows}/{len(df)} rows ({fill_percentage:.1f}%)")
            
            # Print average score if rows exist to verify the data is realistic
            if filled_rows > 0:
                avg_risk = df["integrity_risk_score"].mean(skipna=True)
                print(f"     👉 Sample calculation (Mean Integrity Risk Score): {avg_risk:.2f}")
        else:
            print("   • Layer 2 (Qwen LLM):   ❌ ERROR! Qwen columns are missing from the file header entirely.")
            
        # 3. Quick Peek at the first couple of rows
        print("\n   • Sample view (First 2 entries):")
        peek_cols = ["filename", "true_label", "word_count"] + ([existing_qwen_cols[0]] if existing_qwen_cols else [])
        print(df[peek_cols].head(2).to_string(index=False))
        print("-" * 60)

if __name__ == "__main__":
    inspect_datasets()