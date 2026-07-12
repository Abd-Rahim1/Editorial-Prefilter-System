"""
Script 06: Exploratory Data Analysis (EDA)
Phase 2 - Data Understanding and Visualization

Generates and saves:
  - Distribution plots (Histograms + KDE)
  - Outlier Boxplots
  - Correlation Heatmap
  - Target Analysis (Class distribution)
  - Feature vs Target Analysis (Violin/Boxplots)
  - Pairwise Analysis (Pairplots)

Output destination: storage/eda_plots
"""

import os
import pathlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent

# FIXED: Now pointing directly to dataset.csv
INPUT_CSV    = PROJECT_ROOT / "data" / "processed" / "dataset.csv"
OUTPUT_DIR   = PROJECT_ROOT / "storage" / "eda_plots"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set global seaborn styling for academic plots
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({'figure.max_open_warning': 0}) # Suppress warning for many plots

def main():
    print("=== Phase 2: Exploratory Data Analysis ===")
    
    # 1. Check if file exists
    if not INPUT_CSV.exists():
        print(f"[ERROR] Cannot find dataset at {INPUT_CSV}")
        print("Make sure you ran the 05_convert_json_to_csv.py script first!")
        return
        
    print(f"Loading dataset from: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    
    # Define feature groups based on the schema
    target_col = "ground_truth"
    meta_cols = ["total_word_count", "num_pages"]
    llm_cols = [
        "abstract_clarity", "structural_completeness", "methodological_strength",
        "experimental_strength", "argumentative_quality", "scope_alignment",
        "overall_quality", "integrity_risk_score"
    ]
    
    # Filter only columns that actually exist in the dataframe
    llm_cols = [c for c in llm_cols if c in df.columns]
    rule_counts = ["total_rules_failed", "critical_rules_failed"]
    numeric_cols = meta_cols + llm_cols + rule_counts
    
    print("\n[1] Dataset Overview:")
    print(f" - Samples (Rows): {df.shape[0]}")
    print(f" - Features (Cols): {df.shape[1]}")
    print(f" - Missing Values: \n{df.isnull().sum()[df.isnull().sum() > 0]}")
    print(f" - Duplicates: {df.duplicated().sum()}")
    
    print("\n[2] Generating Target Analysis...")
    plt.figure(figsize=(6, 4))
    ax = sns.countplot(data=df, x=target_col)
    plt.title("Class Distribution (Ground Truth)")
    plt.xlabel("0 = Rejected, 1 = Accepted")
    
    # Add percentage labels
    total = len(df)
    for p in ax.patches:
        percentage = f'{100 * p.get_height() / total:.1f}%'
        ax.annotate(percentage, (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "Target_Class_Distribution.png", dpi=300)
    plt.close()

    print("[3] Generating Distribution Plots...")
    for col in numeric_cols:
        if col in df.columns:
            plt.figure(figsize=(7, 4))
            sns.histplot(df[col], kde=True, bins=20)
            plt.title(f"Distribution of {col}")
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / f"Dist_{col}.png", dpi=300)
            plt.close()

    print("[4] Generating Outlier Boxplots...")
    features_to_check = meta_cols + ["overall_quality"]
    for col in [c for c in features_to_check if c in df.columns]:
        plt.figure(figsize=(6, 2))
        sns.boxplot(x=df[col])
        plt.title(f"Outliers in {col}")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / f"Outlier_{col}.png", dpi=300)
        plt.close()

    print("[5] Generating Correlation Heatmap...")
    plt.figure(figsize=(12, 10))
    # Select only numeric data to avoid errors in latest pandas versions
    numeric_df = df[numeric_cols + [target_col]].select_dtypes(include=[np.number])
    corr_matrix = numeric_df.corr()
    
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", cbar=True, square=True)
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "Correlation_Heatmap.png", dpi=300)
    plt.close()

    print("[6] Generating Feature vs Target Plots...")
    for col in llm_cols + meta_cols:
        if col in df.columns:
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            
            # Boxplot
            sns.boxplot(data=df, x=target_col, y=col, ax=axes[0])
            axes[0].set_title(f"{col} by Class (Boxplot)")
            axes[0].set_xlabel("0 = Rejected, 1 = Accepted")
            
            # Violin Plot
            sns.violinplot(data=df, x=target_col, y=col, ax=axes[1], inner="quartile")
            axes[1].set_title(f"{col} by Class (Violin)")
            axes[1].set_xlabel("0 = Rejected, 1 = Accepted")
            
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / f"TargetVs_{col}.png", dpi=300)
            plt.close()

    print("[7] Generating Pairwise Relationships...")
    # Select key features to prevent the graph from becoming unreadable
    pairplot_cols = ["total_word_count", "methodological_strength", "overall_quality", "critical_rules_failed", target_col]
    pairplot_cols = [c for c in pairplot_cols if c in df.columns] 
    
    if len(pairplot_cols) > 1:
        sns.pairplot(df[pairplot_cols], hue=target_col, palette="husl", diag_kind="kde")
        plt.savefig(OUTPUT_DIR / "Pairplot_Key_Features.png", dpi=300)
        plt.close()

    print(f"\n✅ EDA Complete! All plots have been saved to: \n{OUTPUT_DIR}")

if __name__ == "__main__":
    main()