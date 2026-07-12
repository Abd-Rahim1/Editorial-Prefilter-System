"""
dataset.py — Offline Dataset Loader & Stratified Splitting
Loads tabular training and evaluation splits from `data/prepared/dataset/`.
Applies exact Tier C2 feature filtering, deterministic ordering, target mapping (`ground_truth`),
and stratified train/test partitioning.
"""

from pathlib import Path
from typing import Tuple, List, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

from ..common.constants import PACKAGE_ROOT
from ..common.feature_contract import CANONICAL_C2_FEATURES, FEATURE_DEFAULT_VALUES
from ..common.exceptions import Layer3Error

_PROJECT_ROOT = PACKAGE_ROOT.parent.parent.resolve()
_DATA_PREPARED_DIR = _PROJECT_ROOT / "data" / "prepared" / "dataset"


def _prepare_c2_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Ensures exact C2 canonical features and extracts `ground_truth` series."""
    df = df.copy()

    # 1. Target column resolution
    target_col = None
    for col in ["ground_truth", "true_label", "label", "accepted", "decision"]:
        if col in df.columns:
            target_col = col
            break

    if not target_col:
        raise Layer3Error("[Offline Dataset Error] No valid target label column found in dataset.")

    df = df.dropna(subset=[target_col])
    y = df[target_col].astype(int)

    # 2. Ensure risk_multiplier formula if missing
    if "risk_multiplier" not in df.columns:
        if "overall_quality" in df.columns and "total_rules_failed" in df.columns:
            df["risk_multiplier"] = (1.0 - df["overall_quality"]) * df["total_rules_failed"]
        else:
            df["risk_multiplier"] = 0.0

    # 3. Extract exact canonical features in order
    X_dict = {}
    for feat in CANONICAL_C2_FEATURES:
        if feat in df.columns:
            X_dict[feat] = pd.to_numeric(df[feat], errors="coerce").fillna(FEATURE_DEFAULT_VALUES.get(feat, 0.0))
        else:
            X_dict[feat] = pd.Series([FEATURE_DEFAULT_VALUES.get(feat, 0.0)] * len(df), index=df.index)

    X = pd.DataFrame(X_dict, index=df.index, columns=CANONICAL_C2_FEATURES)
    return X, y


def load_dataset_splits(
    test_size: float = 0.2,
    random_seed: int = 42,
    custom_csv_path: Optional[Path] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Loads a full CSV dataset and splits it into stratified train and test sets."""
    csv_p = custom_csv_path or (_DATA_PREPARED_DIR / "dataset.csv")
    if not csv_p.exists():
        raise Layer3Error(f"[Offline Dataset Error] Dataset file not found at: {csv_p}")

    df = pd.read_csv(csv_p)
    X, y = _prepare_c2_dataframe(df)

    strat = y if (len(y.value_counts()) >= 2 and y.value_counts().min() >= 2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_seed, stratify=strat
    )

    return X_train, X_test, y_train, y_test


def load_precomputed_splits() -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Loads pre-split `train.csv` and `test.csv` if available, otherwise falls back to `load_dataset_splits()`."""
    train_p = _DATA_PREPARED_DIR / "train.csv"
    test_p = _DATA_PREPARED_DIR / "test.csv"

    if train_p.exists() and test_p.exists():
        df_train = pd.read_csv(train_p)
        df_test = pd.read_csv(test_p)
        X_train, y_train = _prepare_c2_dataframe(df_train)
        X_test, y_test = _prepare_c2_dataframe(df_test)
        return X_train, X_test, y_train, y_test

    return load_dataset_splits()
