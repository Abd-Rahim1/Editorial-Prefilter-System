"""
XGBoost training script for Chapter 5 experiments.
"""

import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

from experiments.config import PARAM_GRIDS, PARAM_GRIDS_FAST
from experiments.models.common.trainer import run_experiment_train


def train_xgboost(
    dataset_variant: str = "dataset",
    tier: str = "A",
    fast_mode: bool = False,
    calib_method: str = "auto",
    llm_model: Optional[str] = None,
    prompt_version: Optional[str] = None,
    experiment_id: Optional[str] = None,
) -> Tuple[str, Dict[str, Any], Path]:
    if not HAS_XGB:
        raise ImportError("XGBoost package is not installed or could not be imported.")
    estimator = xgb.XGBClassifier(random_state=42, eval_metric="logloss")
    param_grid = PARAM_GRIDS_FAST["xgboost"] if fast_mode else PARAM_GRIDS["xgboost"]
    return run_experiment_train(
        estimator=estimator,
        param_grid=param_grid,
        classifier_name="XGBoost",
        classifier_subdir="xgboost",
        use_scaler=False,
        dataset_variant=dataset_variant,
        tier=tier,
        fast_mode=fast_mode,
        calib_method=calib_method,
        llm_model=llm_model,
        prompt_version=prompt_version,
        experiment_id=experiment_id,
    )


if __name__ == "__main__":
    train_xgboost()
