"""
Script 07: Comprehensive EDA & Preprocessing Pipeline
Combines Phase 2 (Exploratory Data Analysis) and Phase 3 (Data Preprocessing).

This script performs:
1. Data Ingestion & Overview (Step 3)
2. Missing Values Analysis & Robust Imputation (Step 4-5)
3. Duplicate Records Cleaning (Step 6)
4. Dynamic Feature Dropping (Removing 'integrity_risk_score' to avoid zero variance)
5. Target Analysis Plotting (Target_Class_Distribution.png)
6. Distribution Analysis (Histograms + KDE plots for active numeric features)
7. Outlier Analysis (Outliers_WordCount.png + Outliers_pages/quality boxplots)
8. Categorical Label Encoding (Step 9)
9. Clean Correlation Heatmap Plotting (Correlation_Matrix.png - No blank lines!)
10. Feature vs Target Analysis (TargetVs_[feature_name].png)
11. Stratified Train-Test Split (80/20 Stratified) (Step 11-12)
12. Data Standardization & Export (Step 13)

Output destinations:
  - Cleaned, Split & Scaled Datasets -> data/prepared
  - All EDA Plots & Heatmaps         -> storage/eda/eda_prepared
"""

import os
import pathlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--prompt", type=str, choices=["v1", "v5", "freetext"], default="v5", help="Prompt version to preprocess.")
parser.add_argument(
    "--model",
    type=str,
    default="qwen3:4b",
    choices=["qwen3:4b", "qwen3.5:35b", "qwen3.6:latest"],
    help="Select active LLM model associated with the dataset."
)
args = parser.parse_args()
prompt_version = args.prompt
model_choice = args.model

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent

# Refactor Dynamic Path Routing according to active configurations
if prompt_version == "v1":
    # Zero-Shot Baseline
    input_csv_name = "dataset_v1.csv"
    sub_dir = "v1"
elif prompt_version == "freetext":
    # Plaintext Critique
    input_csv_name = "dataset_freetext.csv"
    sub_dir = "freetext"
else:  # prompt_version == "v5"
    if model_choice == "qwen3.5:35b":
        input_csv_name = "dataset_qwen_35b.csv"
        sub_dir = "qwen_35b"
    elif model_choice == "qwen3.6:latest":
        input_csv_name = "dataset_qwen_latest.csv"
        sub_dir = "qwen_latest"
    else:  # qwen3:4b (Standard Baseline)
        input_csv_name = "dataset.csv"
        sub_dir = "v5"

INPUT_CSV = PROJECT_ROOT / "data" / "processed" / input_csv_name

# Destination paths
PREPARED_DIR = PROJECT_ROOT / "data" / "prepared" / sub_dir
PLOT_DIR     = PROJECT_ROOT / "storage" / "eda" / sub_dir

os.makedirs(PREPARED_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)

# Set global seaborn styling for TFG academic plots
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({'figure.max_open_warning': 0})

def main():
    print("=== STARTING UNIFIED ML PREPROCESSING & EDA PIPELINE ===")
    
    if not INPUT_CSV.exists():
        print(f"[ERROR] Cannot find dataset at {INPUT_CSV}")
        print("Please verify the file exists before running.")
        return
        
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded dataset containing {df.shape[0]} manuscripts with {df.shape[1]} features.")

    print("\n[STEP 3] Dataset Exploration")
    print(f"Shape: {df.shape}")

    print("\n[STEP 4] Missing Values Analysis")
    missing_counts = df.isnull().sum()
    missing_percent = (missing_counts / len(df)) * 100
    missing_df = pd.DataFrame({'Missing Count': missing_counts, 'Percentage': missing_percent})
    print(missing_df[missing_df['Missing Count'] > 0])

    print("\n[STEP 5] Handling Missing Values")
    # Impute numeric columns with mean to prevent model training crashes
    numeric_cols_for_imputation = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols_for_imputation:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mean())
            print(f" -> Imputed missing values in {col} with column Mean.")
            
    # Impute categorical columns with mode
    cat_cols_for_imputation = df.select_dtypes(include=['object']).columns
    for col in cat_cols_for_imputation:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mode()[0])
            print(f" -> Imputed missing values in {col} with column Mode.")

    print("\n[STEP 6] Checking for Duplicate Records")
    if "filename" in df.columns:
        dupes = df.duplicated(subset=["filename"]).sum()
        print(f"Found {dupes} duplicate filename rows.")
        if dupes > 0:
            df.drop_duplicates(subset=["filename"], keep="first", inplace=True)
            print(" -> Duplicates dropped successfully.")
        df.sort_values("filename", inplace=True)
        df.reset_index(drop=True, inplace=True)
    else:
        dupes = df.duplicated().sum()
        print(f"Found {dupes} duplicate rows.")
        if dupes > 0:
            df.drop_duplicates(inplace=True)

    print("\n[PREPROCESSING] Dropping Zero-Variance and Uninformative Features")
    features_to_drop = []
    
    # Enforce strict feature schema alignment across prompt versions
    schema_file = PROJECT_ROOT / "data" / "prepared" / "master_feature_schema.json"
    import json
    if sub_dir == "v5":
        if "integrity_risk_score" in df.columns:
            features_to_drop.append("integrity_risk_score")
        for col in df.select_dtypes(include=[np.number]).columns:
            if col != "ground_truth" and (df[col].std() == 0 or pd.isna(df[col].std()) or df[col].nunique() <= 1):
                if col not in features_to_drop:
                    features_to_drop.append(col)
        df = df.drop(columns=features_to_drop, errors="ignore")
        os.makedirs(PROJECT_ROOT / "data" / "prepared", exist_ok=True)
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(list(df.columns), f, indent=2)
        print(f" -> Baseline feature schema saved ({len(df.columns)} cols) to {schema_file}")
    else:
        if schema_file.exists():
            with open(schema_file, "r", encoding="utf-8") as f:
                master_cols = json.load(f)
            for col in master_cols:
                if col not in df.columns:
                    df[col] = 0.0
            df = df[master_cols]
            print(f" -> Aligned features to exact baseline schema ({len(master_cols)} cols)")
        else:
            if "integrity_risk_score" in df.columns:
                features_to_drop.append("integrity_risk_score")
            for col in df.select_dtypes(include=[np.number]).columns:
                if col != "ground_truth" and (df[col].std() == 0 or pd.isna(df[col].std()) or df[col].nunique() <= 1):
                    if col not in features_to_drop:
                        features_to_drop.append(col)
            df = df.drop(columns=features_to_drop, errors="ignore")
    print(f"Current Dataset Shape after feature removal: {df.shape}")

    # Setup feature categorization for visualization (excluding dropped columns)
    target_col = "ground_truth"
    
    # Explicitly track engineered features in numeric_features so they are scaled and visualized
    meta_cols = ["risk_multiplier", "format_failure"]
    meta_cols = [c for c in meta_cols if c in df.columns]
        
    llm_cols = [
        "abstract_clarity", "structural_completeness", "methodological_strength",
        "experimental_strength", "argumentative_quality", "scope_alignment",
        "overall_quality"
    ]
    # Filter only columns that actually exist in the dataframe
    llm_cols = [c for c in llm_cols if c in df.columns]
    rule_counts = ["total_rules_failed", "critical_rules_failed"]
    rule_counts = [c for c in rule_counts if c in df.columns]
    
    numeric_features = meta_cols + llm_cols + rule_counts

    print("\n[EDA] Plotting Target Class Distribution...")
    plt.figure(figsize=(6, 4))
    ax = sns.countplot(data=df, x=target_col)
    plt.title("Class Distribution (Ground Truth)")
    plt.xlabel("0 = Rejected, 1 = Accepted")
    
    total = len(df)
    for p in ax.patches:
        percentage = f'{100 * p.get_height() / total:.1f}%'
        ax.annotate(percentage, (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "Target_Class_Distribution.png", dpi=300)
    plt.close()

    print("[EDA] Plotting Feature Distributions...")
    for col in numeric_features:
        if col in df.columns:
            plt.figure(figsize=(7, 4))
            sns.histplot(df[col], kde=True, bins=20)
            plt.title(f"Distribution of {col}")
            plt.tight_layout()
            plt.savefig(PLOT_DIR / f"Dist_{col}.png", dpi=300)
            plt.close()

    print("\n[STEP 7] Detecting Outliers & Saving Boxplots...")
    if "risk_multiplier" in df.columns:
        plt.figure(figsize=(6, 2.5))
        sns.boxplot(x=df["risk_multiplier"])
        plt.title("Outliers in Risk Multiplier")
        plt.tight_layout()
        plt.savefig(PLOT_DIR / "Outliers_RiskMultiplier.png", dpi=300)
        plt.close()

    features_to_check = ["overall_quality"]
    for col in [c for c in features_to_check if c in df.columns]:
        plt.figure(figsize=(6, 2.5))
        sns.boxplot(x=df[col])
        plt.title(f"Outliers in {col}")
        plt.tight_layout()
        plt.savefig(PLOT_DIR / f"Outlier_{col}.png", dpi=300)
        plt.close()

    print("\n[STEP 8] Estimating Outlier Counts (IQR Method)")
    if "risk_multiplier" in df.columns:
        Q1 = df["risk_multiplier"].quantile(0.25)
        Q3 = df["risk_multiplier"].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers_count = len(df[(df["risk_multiplier"] < lower) | (df["risk_multiplier"] > upper)])
        print(f" -> Found {outliers_count} papers outside standard risk multiplier boundaries.")

    print("\n[STEP 9] Encoding Categorical Variables & Cleaning Columns")
    # Drop document file handles so they don't corrupt the numerical feature arrays
    if "filename" in df.columns:
        df = df.drop("filename", axis=1)
        
    # Label encode conference origins
    if "conference" in df.columns:
        encoder = LabelEncoder()
        df["conference"] = encoder.fit_transform(df["conference"])
        print(" -> Label Encoded 'conference' variable.")

    print("\n[STEP 10] Plotting Feature Correlation Heatmap (No NaN Blocks!)")
    plt.figure(figsize=(12, 10))
    numeric_df = df[numeric_features + [target_col]].select_dtypes(include=[np.number])
    corr_matrix = numeric_df.corr()
    
    # Generate heatmap with standard annotations
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", cbar=True, square=True)
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "Correlation_Matrix.png", dpi=300)
    plt.close()

    print("[EDA] Plotting Feature vs Target Comparisons...")
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
            plt.savefig(PLOT_DIR / f"TargetVs_{col}.png", dpi=300)
            plt.close()

    print("[EDA] Plotting Key Feature Pairplot...")
    pairplot_cols = ["risk_multiplier", "methodological_strength", "overall_quality", "critical_rules_failed", target_col]
    pairplot_cols = [c for c in pairplot_cols if c in df.columns] 
    if len(pairplot_cols) > 1:
        sns.pairplot(df[pairplot_cols], hue=target_col, palette="husl", diag_kind="kde")
        plt.savefig(PLOT_DIR / "Pairplot_Key_Features.png", dpi=300)
        plt.close()

    print("\n[STEP 11] Feature Selection")
    X = df.drop(target_col, axis=1)
    y = df[target_col]
    print(f" -> Features (X) shape: {X.shape}")
    print(f" -> Target (y) shape: {y.shape}")

    print("\n[STEP 12] Train-Test Split")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f" -> X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f" -> X_test:  {X_test.shape}, y_test:  {y_test.shape}")

    print("\n[STEP 13] Scaling Features (Standardization)")
    # Exclude filename and categorical columns from standardization
    cols_to_exclude = [c for c in ["filename", "conference"] if c in X.columns] + list(X.select_dtypes(include=["object", "category"]).columns)
    cols_to_exclude = list(set(cols_to_exclude))
    cols_to_scale = [c for c in X.columns if c not in cols_to_exclude]

    scaler = StandardScaler()
    X_train_scaled_df = X_train.copy().reset_index(drop=True)
    X_test_scaled_df = X_test.copy().reset_index(drop=True)
    
    if cols_to_scale:
        X_train_scaled_df[cols_to_scale] = scaler.fit_transform(X_train[cols_to_scale])
        X_test_scaled_df[cols_to_scale] = scaler.transform(X_test[cols_to_scale])

    # Save processed matrices and complete dataset table
    df.to_csv(PREPARED_DIR / "dataset.csv", index=False)
    X_train_scaled_df.to_csv(PREPARED_DIR / "X_train_scaled.csv", index=False)
    X_test_scaled_df.to_csv(PREPARED_DIR / "X_test_scaled.csv", index=False)
    y_train.to_csv(PREPARED_DIR / "y_train.csv", index=False)
    y_test.to_csv(PREPARED_DIR / "y_test.csv", index=False)
    
    if sub_dir == "v5":
        mirror_dir = PROJECT_ROOT / "data" / "prepared" / "dataset"
        os.makedirs(mirror_dir, exist_ok=True)
        df.to_csv(mirror_dir / "dataset.csv", index=False)
        X_train_scaled_df.to_csv(mirror_dir / "X_train_scaled.csv", index=False)
        X_test_scaled_df.to_csv(mirror_dir / "X_test_scaled.csv", index=False)
        y_train.to_csv(mirror_dir / "y_train.csv", index=False)
        y_test.to_csv(mirror_dir / "y_test.csv", index=False)
    
    print(f"\nPIPELINE & EDA COMPLETE!")
    print(f" -> Prepared Datasets exported to:  {PREPARED_DIR}")
    print(f" -> Complete Suite of clean EDA plots to: {PLOT_DIR}")

if __name__ == "__main__":
    main()