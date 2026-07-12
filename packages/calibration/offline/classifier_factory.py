"""
classifier_factory.py — Offline Classifier instantiation Factory
Instantiates underlying estimator models (`RandomForestClassifier`, `LogisticRegression`, `XGBClassifier`)
with validated default hyperparameters or custom hyperparameter grids.
"""

from typing import Dict, Any, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


def create_classifier(classifier_name: str, random_seed: int = 42, custom_params: Optional[Dict[str, Any]] = None) -> Any:
    """Instantiates a supervised classifier by name.

    Args:
        classifier_name: 'Random_Forest', 'Logistic_Regression', or 'XGBoost'.
        random_seed: Seed for reproducibility.
        custom_params: Optional hyperparameter overrides.

    Returns:
        Sklearn-compatible estimator instance.
    """
    clean_name = classifier_name.strip().lower().replace(" ", "_")
    params = custom_params.copy() if custom_params else {}

    if "random_forest" in clean_name or "rf" == clean_name:
        defaults = {
            "n_estimators": 150,
            "max_depth": 3,
            "min_samples_leaf": 4,
            "class_weight": None,
            "random_state": random_seed
        }
        defaults.update(params)
        return RandomForestClassifier(**defaults)

    elif "logistic" in clean_name or "lr" == clean_name:
        defaults = {
            "C": 1.0,
            "max_iter": 1000,
            "class_weight": None,
            "random_state": random_seed
        }
        defaults.update(params)
        return LogisticRegression(**defaults)

    elif "xgboost" in clean_name or "xgb" == clean_name:
        if not XGB_AVAILABLE:
            raise ImportError("XGBoost is not installed in the active environment.")
        defaults = {
            "n_estimators": 100,
            "max_depth": 3,
            "learning_rate": 0.1,
            "random_state": random_seed,
            "eval_metric": "logloss"
        }
        defaults.update(params)
        return XGBClassifier(**defaults)

    else:
        raise ValueError(f"Unsupported classifier name: '{classifier_name}'. Supported: Random_Forest, Logistic_Regression, XGBoost.")
