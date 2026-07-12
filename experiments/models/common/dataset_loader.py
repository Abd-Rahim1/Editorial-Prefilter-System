"""
Dataset Loader for the Chapter 5 TFG Experimentation Framework.
Supports dataset variants (dataset.csv, dataset_v1.csv, dataset_freetext.csv, dataset_qwen_35b.csv)
and prepared datasets in data/prepared/ (v5, v1, freetext, qwen_35b).
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def resolve_dataset_path(variant: str) -> Optional[Path]:
    """
    Resolves the file path for a requested dataset variant.
    Searches in data/prepared/<variant>/, data/processed/, data/, and outputs/.
    """
    variant_clean = variant.lower().replace(".csv", "").strip()
    
    # Build list of exact candidate filenames for this variant
    if variant_clean in ["dataset", "default", "baseline", "v5"]:
        candidate_names = ["dataset.csv", "data.csv", "train.csv"]
    else:
        candidate_names = [f"dataset_{variant_clean}.csv", f"{variant_clean}.csv"]

    # 1. Search in data/prepared/<variant>/
    prepared_dir = PROJECT_ROOT / "data" / "prepared" / variant_clean
    if prepared_dir.exists() and prepared_dir.is_dir():
        for fname in candidate_names + ["dataset.csv", "train.csv", "data.csv"]:
            p = prepared_dir / fname
            if p.exists():
                return p
            
    # 2. Search in data/processed/
    processed_dir = PROJECT_ROOT / "data" / "processed"
    for fname in candidate_names:
        p = processed_dir / fname
        if p.exists():
            return p
            
    # 3. Search in data/
    data_dir = PROJECT_ROOT / "data"
    for fname in candidate_names:
        p = data_dir / fname
        if p.exists():
            return p
            
    # 4. Search in outputs/
    outputs_dir = PROJECT_ROOT / "outputs"
    for fname in candidate_names + ["layer3_training_dataset.csv", "batch_results.csv"]:
        p = outputs_dir / fname
        if p.exists():
            return p
            
    # 5. Check if variant is an absolute or direct relative path
    direct_path = Path(variant)
    if direct_path.exists() and direct_path.is_file():
        return direct_path
        
    return None

def standardize_target_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures 'ground_truth' column exists as 0/1 integers.
    Maps from 'true_label', 'label', 'accepted', 'decision', or 'status' if needed.
    """
    df = df.copy()
    
    if "ground_truth" not in df.columns:
        for col in ["true_label", "label", "accepted", "decision", "status", "target"]:
            if col in df.columns:
                df["ground_truth"] = df[col]
                break
                
    if "ground_truth" not in df.columns:
        raise ValueError("Dataset must contain a target label column ('ground_truth', 'true_label', 'label', etc.).")
        
    # Drop rows where target is NaN
    df = df.dropna(subset=["ground_truth"])
    
    # Map strings/booleans to 0/1
    def _map_val(val):
        if isinstance(val, bool):
            return 1 if val else 0
        if isinstance(val, (int, float)):
            return int(val > 0)
        s = str(val).lower().strip()
        if s in ["true", "1", "1.0", "accept", "accepted", "yes", "pass", "passed"]:
            return 1
        return 0
        
    df["ground_truth"] = df["ground_truth"].apply(_map_val).astype(int)
    return df

def clean_and_impute(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans tabular data: converts boolean/string flags to numeric,
    fills missing numeric values with median or mean.
    """
    df = df.copy()
    
    # Convert booleans and boolean-like object columns
    for col in df.columns:
        if col == "ground_truth":
            continue
        if df[col].dtype == 'bool' or df[col].dtype == 'object':
            # Try mapping common true/false strings
            mapped = df[col].astype(str).str.lower().map({
                'true': 1.0, 'false': 0.0, 'yes': 1.0, 'no': 0.0,
                '1': 1.0, '0': 0.0, '1.0': 1.0, '0.0': 0.0,
                'pass': 1.0, 'passed': 1.0, 'fail': 0.0, 'failed': 0.0
            })
            if not mapped.isna().all():
                df[col] = mapped
            else:
                # Try numeric conversion
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass
                
    # Coerce numeric columns and impute NaNs
    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if col == "ground_truth":
            continue
        if df[col].isna().any():
            median_val = df[col].median()
            if pd.isna(median_val):
                median_val = 0.0
            df[col] = df[col].fillna(median_val)
            
    return df

def load_dataset(variant: str) -> Tuple[pd.DataFrame, Path]:
    """
    Loads, standardizes, and cleans the specified dataset variant.
    Returns the cleaned DataFrame and the resolved file path.
    """
    path = resolve_dataset_path(variant)
    if not path or not path.exists():
        raise FileNotFoundError(f"Could not resolve dataset variant '{variant}'. Searched standard project data directories.")
        
    df = pd.read_csv(path)
    df = standardize_target_column(df)
    df = clean_and_impute(df)
    
    return df, path

def get_train_test_split(
    df: pd.DataFrame, 
    test_size: float = 0.2, 
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Performs deterministic stratified train/test split.
    """
    X = df.drop(columns=["ground_truth"])
    y = df["ground_truth"]
    
    # Check if stratification is possible (at least 2 samples per class)
    class_counts = y.value_counts()
    stratify_param = y if (len(class_counts) >= 2 and class_counts.min() >= 2) else None
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify_param
    )
    
    return X_train, X_test, y_train, y_test
