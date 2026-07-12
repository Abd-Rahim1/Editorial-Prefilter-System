"""
trainer.py — Offline Supervised Training Wrappers
Fits candidate classifiers on training splits.
"""

import time
from typing import Dict, Any, Tuple, Optional
import pandas as pd
from .classifier_factory import create_classifier
from ..common.exceptions import Layer3Error


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    classifier_name: str = "Random_Forest",
    custom_params: Optional[Dict[str, Any]] = None,
    random_seed: int = 42
) -> Tuple[Any, float]:
    """Fits an underlying classifier on `(X_train, y_train)` and records training duration.

    Args:
        X_train: Training features DataFrame.
        y_train: Training target Series.
        classifier_name: Name of classifier to instantiate and train.
        custom_params: Optional hyperparameter dict.
        random_seed: Random seed.

    Returns:
        Tuple[Any, float]: `(fitted_model, training_time_ms)`
    """
    if X_train.empty or y_train.empty:
        raise Layer3Error("[Trainer Error] Training feature matrix or target vector is empty.")

    model = create_classifier(classifier_name, random_seed=random_seed, custom_params=custom_params)
    t0 = time.perf_counter()
    model.fit(X_train, y_train)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    return model, dt_ms
