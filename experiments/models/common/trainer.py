"""
Unified Model Trainer for the Chapter 5 TFG Experimentation Framework.
Encapsulates data loading, feature selection, scaling, GridSearchCV, probability
calibration, metric evaluation, artifact persistence, and MLflow logging.
"""

import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler

from experiments.config import EXPERIMENT_PROTOCOLS, PROJECT_ROOT
from experiments.models.common.dataset_loader import load_dataset, get_train_test_split
from experiments.models.common.feature_selector import select_features
from experiments.models.common.calibration import calibrate
from experiments.models.common.metrics import compute_all_metrics
from experiments.models.common.artifact_manager import save_all_artifacts
from experiments.models.common.mlflow_logger import log_to_mlflow
from experiments.models.common.utils import build_run_output_dir


def run_experiment_train(
    estimator: Any,
    param_grid: Dict[str, Any],
    classifier_name: str,
    classifier_subdir: str,
    use_scaler: bool = False,
    dataset_variant: str = "dataset",
    tier: str = "A",
    fast_mode: bool = False,
    calib_method: str = "auto",
    llm_model: Optional[str] = None,
    prompt_version: Optional[str] = None,
    experiment_id: Optional[str] = None,
) -> Tuple[str, Dict[str, Any], Path]:
    print(f"==========================================================================")
    print(f"   TRAINING {classifier_name.upper().replace('_', ' ')}")
    print(f"   Dataset={dataset_variant} | Tier=Exp_{tier} | Calib={calib_method}")
    print(f"==========================================================================")

    # 1. Load Dataset
    df, path = load_dataset(dataset_variant)
    print(f"[+] Loaded dataset ({len(df)} rows) from: {path}")

    # 2. Split Data
    X_train_raw, X_test_raw, y_train, y_test = get_train_test_split(
        df,
        test_size=EXPERIMENT_PROTOCOLS["test_size"],
        random_state=EXPERIMENT_PROTOCOLS["random_seed"],
    )

    # 3. Select Features for Ablation Tier
    X_train_unscaled = select_features(X_train_raw, tier)
    X_test_unscaled = select_features(X_test_raw, tier)
    feature_names = list(X_train_unscaled.columns)
    print(f"[+] Selected {len(feature_names)} features for Tier {tier}")
    print(f"[+] Split: {len(X_train_unscaled)} train | {len(X_test_unscaled)} test")

    # 4. Feature Scaling (if required)
    scaler = None
    if use_scaler:
        scaler = StandardScaler()
        X_train_arr = scaler.fit_transform(X_train_unscaled)
        X_test_arr = scaler.transform(X_test_unscaled)
        X_train = pd.DataFrame(X_train_arr, columns=feature_names)
        X_test = pd.DataFrame(X_test_arr, columns=feature_names)
    else:
        X_train = X_train_unscaled.reset_index(drop=True)
        X_test = X_test_unscaled.reset_index(drop=True)

    y_train = y_train.reset_index(drop=True)
    y_test = y_test.reset_index(drop=True)

    # 5. GridSearchCV
    print(f"\n---> GridSearchCV (cv={EXPERIMENT_PROTOCOLS['cv_folds']}, fast={fast_mode})...")
    grid = GridSearchCV(
        estimator=estimator,
        param_grid=param_grid,
        cv=EXPERIMENT_PROTOCOLS["cv_folds"],
        scoring=EXPERIMENT_PROTOCOLS["scoring_metric"],
        n_jobs=-1,
    )

    t0 = time.time()
    grid.fit(X_train, y_train)
    train_time_ms = (time.time() - t0) * 1000.0

    best_estimator = grid.best_estimator_
    best_params = grid.best_params_
    print(f"     Best Params: {best_params} (CV ROC AUC: {grid.best_score_:.4f})")

    # 6. Probability Calibration
    calibrated_model, method_used, ece_scores = calibrate(
        best_estimator=best_estimator,
        X_train=X_train,
        y_train=y_train,
        X_val=X_test,
        y_val=y_test,
        method=calib_method,
        cv=EXPERIMENT_PROTOCOLS["cv_folds"],
    )

    # 7. Evaluate on Test Set
    t_inf_0 = time.time()
    y_pred = calibrated_model.predict(X_test)
    y_prob = calibrated_model.predict_proba(X_test)[:, 1]
    inference_time_ms = (time.time() - t_inf_0) * 1000.0

    metrics_dict = compute_all_metrics(
        y_true=y_test,
        y_pred=y_pred,
        y_prob=y_prob,
        train_time_ms=train_time_ms,
        inference_time_ms=inference_time_ms,
    )
    print(f"     Test ROC AUC: {metrics_dict['roc_auc']:.4f} | ECE: {metrics_dict['ece']:.4f}")

    # 8. Build Output Directory
    out_path = build_run_output_dir(
        project_root=PROJECT_ROOT,
        classifier_subdir=classifier_subdir,
        dataset_variant=dataset_variant,
        tier=tier,
        calib_method=method_used,
    )

    # 9. Save All Artifacts & Manifests
    saved_paths = save_all_artifacts(
        output_dir=out_path,
        model=best_estimator,
        calibrated_model=calibrated_model,
        X_test=X_test,
        y_test=y_test,
        y_pred=y_pred,
        y_prob=y_prob,
        feature_names=feature_names,
        model_name=classifier_name,
        metrics=metrics_dict,
        experiment_id=experiment_id or f"{dataset_variant}_Exp{tier}_{classifier_subdir}_{method_used}",
        dataset=dataset_variant,
        tier=tier,
        calib_method=method_used,
        prompt_version=prompt_version,
        llm_model=llm_model,
        random_seed=EXPERIMENT_PROTOCOLS["random_seed"],
        hyperparameters=best_params,
        scaler=scaler,
    )

    # 10. Log to MLflow
    tags = {
        "dataset": dataset_variant,
        "feature_set": f"Exp_{tier}",
        "classifier": classifier_name,
        "calibration_method": method_used,
        "experiment_type": "grid_search",
        "random_seed": str(EXPERIMENT_PROTOCOLS["random_seed"]),
        "llm_model_name": str(llm_model or "default"),
        "prompt_version": str(prompt_version or "default"),
    }
    
    run_name = f"{classifier_name}_Exp{tier}_{dataset_variant}_{method_used}"
    run_id = log_to_mlflow(
        run_name=run_name,
        params=best_params,
        metrics=metrics_dict,
        tags=tags,
        artifacts=saved_paths,
    )
    print(f"[+] MLflow Run ID: {run_id}")

    return run_id, metrics_dict, out_path
