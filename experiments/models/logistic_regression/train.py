"""
Logistic regression training script for Chapter 5 experiments.
"""

import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.linear_model import LogisticRegression
from experiments.config import PARAM_GRIDS, PARAM_GRIDS_FAST
from experiments.models.common.trainer import run_experiment_train


def train_logistic_regression(
    dataset_variant: str = "dataset",
    tier: str = "A",
    fast_mode: bool = False,
    calib_method: str = "auto",
    llm_model: Optional[str] = None,
    prompt_version: Optional[str] = None,
    experiment_id: Optional[str] = None,
) -> Tuple[str, Dict[str, Any], Path]:
    estimator = LogisticRegression(random_state=42)
    param_grid = PARAM_GRIDS_FAST["logistic_regression"] if fast_mode else PARAM_GRIDS["logistic_regression"]
    return run_experiment_train(
        estimator=estimator,
        param_grid=param_grid,
        classifier_name="Logistic_Regression",
        classifier_subdir="logistic_regression",
        use_scaler=True,
        dataset_variant=dataset_variant,
        tier=tier,
        fast_mode=fast_mode,
        calib_method=calib_method,
        llm_model=llm_model,
        prompt_version=prompt_version,
        experiment_id=experiment_id,
    )


if __name__ == "__main__":
    train_logistic_regression()
