"""
run_tfg_evaluation_study.py — Autonomous 4-Phase Evaluation & Benchmarking Pipeline (TFG_Evaluation)
Executes a two-stage (4-Phase) scientific methodology across exactly 27 independent runs:
  Phase 1: ML Classifier & Feature Selection (21 runs across LR, RF, XGB × Exp_A..D, C1..C3 uncalibrated)
  Phase 2: Calibration Selection (3 new runs across sigmoid, isotonic, auto on winning model + tier)
           -> Exports best_model_config.json and evaluation_models/best_pipeline/
  Phase 3: Prompt Engineering Comparison (2 new runs across v1 and freetext on frozen pipeline)
  Phase 4: LLM Scaling Comparison (1 new run across qwen_35b on frozen pipeline)

Enforces strict isolation and complete tracking:
  - Models saved strictly in: experiments/evaluation_models/<classifier>/<dataset>/<feature_set>/<calibration>/
  - MLflow runs logged exclusively to experiment: TFG_Evaluation with full parameters, metrics, and artifacts
  - PostgreSQL records written to public.experiments (isolating study_name='TFG_Evaluation') and verified after every insert
  - Zero modifications to existing experiments, production code, or databases.
"""

import os
import sys
import time
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for p in [str(PROJECT_ROOT), str(PROJECT_ROOT / "packages")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import core training scripts and helpers
from experiments.models.logistic_regression.train import train_logistic_regression
from experiments.models.random_forest.train import train_random_forest
try:
    from experiments.models.xgboost.train import train_xgboost, HAS_XGB
except ImportError:
    HAS_XGB = False

import experiments.models.common.trainer as trainer
import experiments.models.common.utils as utils
import experiments.models.common.mlflow_logger as mlflow_logger
import experiments.models.common.feature_selector as feature_selector
from database.connection import get_connection

DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"



CURRENT_REQUESTED_CALIB = "none"

def format_feature_set_name(tier: str) -> str:
    """Formats feature set name consistently: Exp_A..Exp_D for A..D, and C1..C3 for C1..C3."""
    t = tier.strip()
    if t.upper() in ["A", "B", "C", "D"]:
        return f"Exp_{t.upper()}"
    elif t.upper() in ["C1", "C2", "C3"]:
        return t.upper()
    return t if t.startswith("Exp") else f"Exp_{t}"

def custom_build_run_output_dir(
    project_root: Path,
    classifier_subdir: str,
    dataset_variant: str,
    tier: str,
    calib_method: str,
    base_subdir: str = "runs",
) -> Path:
    """
    Redirects output directory strictly to:
    experiments/evaluation_models/<classifier>/<dataset>/<feature_set>/<calib>/
    Ensures 'auto' calibration creates its own directory when requested.
    """
    actual_calib = CURRENT_REQUESTED_CALIB if CURRENT_REQUESTED_CALIB in ["none", "sigmoid", "isotonic", "auto"] else calib_method
    feature_set_clean = format_feature_set_name(tier)
    out = project_root / "experiments" / "evaluation_models" / classifier_subdir / dataset_variant / feature_set_clean / actual_calib
    out.mkdir(parents=True, exist_ok=True)
    return out

utils.build_run_output_dir = custom_build_run_output_dir
trainer.build_run_output_dir = custom_build_run_output_dir


original_log_to_mlflow = mlflow_logger.log_to_mlflow

def custom_log_to_mlflow(
    run_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    tags: Dict[str, Any],
    artifacts: Dict[str, Path],
    experiment_name: str = "TFG_Evaluation",
    tracking_uri: Optional[str] = None,
) -> str:
    """
    Enforces logging strictly to MLflow experiment 'TFG_Evaluation' with all required parameters, metrics, tags, and artifacts.
    """
    new_tags = dict(tags)
    new_tags["study_name"] = "TFG_Evaluation"
    new_tags["dataset"] = tags.get("dataset", "dataset")
    new_tags["prompt_version"] = tags.get("prompt_version", "v5")
    new_tags["llm_model"] = tags.get("llm_model_name", "qwen3:4b")
    new_tags["classifier"] = tags.get("classifier", "Unknown")
    new_tags["feature_set"] = format_feature_set_name(tags.get("feature_set", "Exp_C"))
    new_tags["calibration"] = CURRENT_REQUESTED_CALIB if CURRENT_REQUESTED_CALIB in ["none", "sigmoid", "isotonic", "auto"] else tags.get("calibration_method", "none")
    new_tags["random_seed"] = str(tags.get("random_seed", "42"))
    new_tags["git_commit"] = utils.get_git_commit_hash()
    
    # Enforce logging all requested parameters explicitly
    new_params = dict(params)
    new_params["classifier"] = new_tags["classifier"]
    new_params["feature_set"] = new_tags["feature_set"]
    new_params["calibration"] = new_tags["calibration"]
    new_params["dataset"] = new_tags["dataset"]
    new_params["prompt_version"] = new_tags["prompt_version"]
    new_params["llm_model"] = new_tags["llm_model"]
    if "hyperparameters" not in new_params:
        new_params["hyperparameters"] = json.dumps(params)
        
    # Enforce logging all requested metrics (both exact case and lowercase aliases)
    new_metrics = dict(metrics)
    metric_aliases = {
        "Accuracy": metrics.get("accuracy", 0.0),
        "Precision": metrics.get("precision", 0.0),
        "Recall": metrics.get("recall", 0.0),
        "F1": metrics.get("f1", 0.0),
        "ROC AUC": metrics.get("roc_auc", 0.0),
        "PR AUC": metrics.get("pr_auc", 0.0),
        "MCC": metrics.get("mcc", 0.0),
        "Balanced Accuracy": metrics.get("balanced_accuracy", metrics.get("accuracy", 0.0)),
        "Brier Score": metrics.get("brier_score", 0.0),
        "ECE": metrics.get("ece", 0.0),
        "Training Time": metrics.get("train_time_ms", 0.0) / 1000.0,
        "Inference Time": metrics.get("inference_time_ms", 0.0),
    }
    new_metrics.update(metric_aliases)
    
    return original_log_to_mlflow(
        run_name=run_name,
        params=new_params,
        metrics=new_metrics,
        tags=new_tags,
        artifacts=artifacts,
        experiment_name="TFG_Evaluation",
        tracking_uri=DEFAULT_MLFLOW_DB
    )

mlflow_logger.log_to_mlflow = custom_log_to_mlflow
trainer.log_to_mlflow = custom_log_to_mlflow



original_select_features = feature_selector.select_features

def custom_select_features(df: pd.DataFrame, tier: str) -> pd.DataFrame:
    """
    Implements feature tiers A, B, C, D alongside C1, C2, C3 ablations without editing original module.
    """
    tier_upper = tier.upper().strip()
    if tier_upper in ["A", "B", "C", "D"]:
        return original_select_features(df, tier_upper)
        
    all_num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in feature_selector.IGNORE_COLS]
    
    if tier_upper == "C1":
        # C1: Only structural features (remove semantic Qwen features and full-text derived features)
        l1_canon = [c for c in feature_selector.LAYER1_CANDIDATES if c in all_num_cols]
        l1_rules = sorted([c for c in all_num_cols if c.startswith("rule_") and c not in l1_canon])
        selected = l1_canon + l1_rules + [c for c in ["format_failure", "total_rules_failed", "critical_rules_failed"] if c in all_num_cols]
        selected = sorted(list(set(selected)))
    elif tier_upper == "C2":
        # C2: Remove section segmentation (use concatenated document instead of section-aware features)
        selected = [
            c for c in all_num_cols 
            if not any(sec in c.lower() for sec in ["abstract", "section", "methodology", "introduction", "conclusion", "experiments"])
        ]
        selected = sorted(list(set(selected)))
    elif tier_upper == "C3":
        # C3: Remove hard editorial rule features (remove rule_*, format_failure, total_rules_failed, critical_rules_failed, risk_multiplier)
        remove_set = {"format_failure", "total_rules_failed", "critical_rules_failed", "risk_multiplier"}
        selected = [c for c in all_num_cols if not c.startswith("rule_") and c not in remove_set]
        selected = sorted(list(set(selected)))
    else:
        # Fallback to original
        return original_select_features(df, tier)
        
    if not selected:
        selected = sorted(all_num_cols)
    return df[selected].copy()

feature_selector.select_features = custom_select_features
trainer.select_features = custom_select_features



def clean_previous_evaluation_records():
    print("\n[DB] Checking for previous TFG_Evaluation records in PostgreSQL...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM public.experiments 
                WHERE experiment_name LIKE 'TFG_Evaluation%' 
                   OR notes LIKE '%study_name=TFG_Evaluation%' 
                   OR metrics->>'study_name' = 'TFG_Evaluation';
            """)
            deleted_count = cur.rowcount
            conn.commit()
            print(f"[DB] Cleaned {deleted_count} previous TFG_Evaluation records from public.experiments.")
    except Exception as e:
        print(f"[!] Error cleaning DB: {e}")
    finally:
        conn.close()

def clean_mlflow_evaluation_experiment():
    print("[MLflow] Checking for previous TFG_Evaluation runs in MLflow...")
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        mlflow.set_tracking_uri(DEFAULT_MLFLOW_DB)
        client = MlflowClient()
        exp = client.get_experiment_by_name("TFG_Evaluation")
        if exp:
            runs = client.search_runs(experiment_ids=[exp.experiment_id])
            for r in runs:
                client.delete_run(r.info.run_id)
            print(f"[MLflow] Cleaned {len(runs)} previous runs from experiment TFG_Evaluation.")
    except Exception as e:
        print(f"[!] MLflow clean warning: {e}")



def sync_evaluation_run_to_postgres(
    run_id: str,
    run_name: str,
    classifier_name: str,
    dataset_variant: str,
    tier: str,
    calib_method: str,
    prompt_version: str,
    llm_model: str,
    metrics_dict: Dict[str, Any],
):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            metrics_payload = dict(metrics_dict)
            metrics_payload["study_name"] = "TFG_Evaluation"
            metrics_payload["llm_model"] = llm_model
            metrics_payload["feature_set"] = format_feature_set_name(tier)
            metrics_payload["calibration"] = calib_method
            
            notes_str = f"study_name=TFG_Evaluation | Dataset: {dataset_variant} | Tier: {format_feature_set_name(tier)} | Calib: {calib_method} | Prompt: {prompt_version} | LLM: {llm_model}"
            
            cur.execute("""
                INSERT INTO public.experiments (
                    experiment_name, model_version, dataset_name, classifier,
                    calibration_method, prompt_version, random_seed, training_time,
                    experiment_status, mlflow_run_id, accuracy, "precision", recall,
                    f1, auroc, ece, metrics, notes, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                );
            """, (
                f"TFG_Evaluation - {run_name}",
                run_id,
                dataset_variant,
                classifier_name,
                calib_method,
                prompt_version,
                42,
                metrics_dict.get("train_time_ms", 0.0) / 1000.0,
                "FINISHED",
                run_id,
                metrics_dict.get("accuracy", 0.0),
                metrics_dict.get("precision", 0.0),
                metrics_dict.get("recall", 0.0),
                metrics_dict.get("f1", 0.0),
                metrics_dict.get("roc_auc", 0.0),
                metrics_dict.get("ece", 0.0),
                json.dumps(metrics_payload),
                notes_str
            ))
            conn.commit()
            
            # Verify row exists immediately after insertion
            cur.execute("SELECT count(*) FROM public.experiments WHERE mlflow_run_id = %s;", (run_id,))
            cnt = cur.fetchone()[0]
            if cnt == 0:
                raise RuntimeError(f"PostgreSQL verification failed right after insert for run_id={run_id}!")
            print(f"      [DB Verified] Run {run_id} exists in public.experiments.")
    except Exception as e:
        print(f"[!] PostgreSQL sync error for {run_id}: {e}")
        raise e
    finally:
        conn.close()



DATASET_METADATA = {
    "dataset": {"prompt_version": "v5", "llm_model": "qwen3:4b"},
    "v1": {"prompt_version": "v1", "llm_model": "qwen3:4b"},
    "freetext": {"prompt_version": "freetext", "llm_model": "qwen3:4b"},
    "qwen_35b": {"prompt_version": "v5", "llm_model": "qwen3.5:35b"},
}

def execute_single_run(
    clf_key: str,
    ds_name: str,
    tier: str,
    calib: str,
    fast_mode: bool = False,
    run_idx_info: str = "",
) -> Tuple[str, Dict[str, Any], Path]:
    global CURRENT_REQUESTED_CALIB
    CURRENT_REQUESTED_CALIB = calib
    
    meta = DATASET_METADATA.get(ds_name, {"prompt_version": "v5", "llm_model": "qwen3:4b"})
    prompt_ver = meta["prompt_version"]
    llm_mod = meta["llm_model"]
    run_name = f"{clf_key}_{format_feature_set_name(tier)}_{ds_name}_{calib}"
    
    print(f"\n------------------------------------------------------------------------")
    print(f"{run_idx_info} Running: {run_name}")
    print(f"       Dataset: {ds_name} ({llm_mod}, Prompt {prompt_ver}) | Tier: {format_feature_set_name(tier)} | Calib: {calib}")
    print(f"------------------------------------------------------------------------")
    
    if clf_key == "logistic_regression":
        run_id, metrics, out_path = train_logistic_regression(
            dataset_variant=ds_name, tier=tier, fast_mode=fast_mode,
            calib_method=calib, llm_model=llm_mod, prompt_version=prompt_ver,
            experiment_id=run_name
        )
    elif clf_key == "random_forest":
        run_id, metrics, out_path = train_random_forest(
            dataset_variant=ds_name, tier=tier, fast_mode=fast_mode,
            calib_method=calib, llm_model=llm_mod, prompt_version=prompt_ver,
            experiment_id=run_name
        )
    elif clf_key == "xgboost":
        run_id, metrics, out_path = train_xgboost(
            dataset_variant=ds_name, tier=tier, fast_mode=fast_mode,
            calib_method=calib, llm_model=llm_mod, prompt_version=prompt_ver,
            experiment_id=run_name
        )
    else:
        raise ValueError(f"Unknown classifier {clf_key}")
        
    sync_evaluation_run_to_postgres(
        run_id=run_id, run_name=run_name,
        classifier_name=clf_key.replace("_", " ").title(),
        dataset_variant=ds_name, tier=tier, calib_method=calib,
        prompt_version=prompt_ver, llm_model=llm_mod, metrics_dict=metrics
    )
    return run_id, metrics, out_path



def run_study(fast_mode: bool = False):
    t_total_0 = time.time()
    print("\n=== TFG_Evaluation — AUTONOMOUS 4-PHASE EVALUATION STUDY ===")
    
    clean_previous_evaluation_records()
    clean_mlflow_evaluation_experiment()
    
    print("\n=== PHASE 1: ML CLASSIFIER & FEATURE SELECTION (21 experiments) ===")
    print("    Dataset: dataset.csv | Calib: none | Tiers: A, B, C, D, C1, C2, C3")
    
    classifiers = ["logistic_regression", "random_forest"] + (["xgboost"] if HAS_XGB else [])
    phase1_tiers = ["A", "B", "C", "D", "C1", "C2", "C3"]
    phase1_results = []
    
    total_p1 = len(classifiers) * len(phase1_tiers)
    idx_p1 = 0
    for clf in classifiers:
        for tier in phase1_tiers:
            idx_p1 += 1
            run_id, metrics, out_path = execute_single_run(
                clf_key=clf, ds_name="dataset", tier=tier, calib="none",
                fast_mode=fast_mode, run_idx_info=f"[Phase 1: {idx_p1}/{total_p1}]"
            )
            phase1_results.append({
                "classifier": clf,
                "tier": tier,
                "run_id": run_id,
                "roc_auc": metrics.get("roc_auc", 0.0),
                "mcc": metrics.get("mcc", 0.0),
                "f1": metrics.get("f1", 0.0),
                "ece": metrics.get("ece", 0.0),
                "out_path": out_path,
            })
            
    # Sort Phase 1 by: 1. ROC AUC (desc), 2. MCC (desc), 3. F1 (desc)
    phase1_sorted = sorted(phase1_results, key=lambda x: (x["roc_auc"], x["mcc"], x["f1"]), reverse=True)
    best_p1 = phase1_sorted[0]
    
    print("\n--- PHASE 1 TOP 5 MODEL RANKINGS (by ROC AUC -> MCC -> F1) ---")
    for r in phase1_sorted[:5]:
        print(f"  {r['classifier']} (Tier {format_feature_set_name(r['tier'])}): ROC AUC={r['roc_auc']:.4f} | MCC={r['mcc']:.4f} | F1={r['f1']:.4f}")
        
    best_clf = best_p1["classifier"]
    best_tier = best_p1["tier"]
    best_out_path = best_p1["out_path"]
    
    # Extract best hyperparameters from Phase 1 winner metadata.json
    best_params = {}
    meta_path = best_out_path / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_json = json.load(f)
                best_params = meta_json.get("best_params", {})
        except Exception as e:
            print(f"[!] Could not load best_params from {meta_path}: {e}")
            
    print(f"\n[+] Phase 1 Winner Selected: {best_clf} (Tier {format_feature_set_name(best_tier)})")
    print(f"[+] Best Hyperparameters: {best_params}")
    
    
    print("\n=== PHASE 2: CALIBRATION SELECTION (3 new experiments on frozen model/tier) ===")
    print(f"    Model: {best_clf} | Tier: {format_feature_set_name(best_tier)} | Calibs: sigmoid, isotonic, auto")
    
    phase2_calibs = ["sigmoid", "isotonic", "auto"]
    phase2_results = [{
        "calib": "none",
        "roc_auc": best_p1["roc_auc"],
        "ece": best_p1["ece"],
        "out_path": best_out_path,
        "run_id": best_p1["run_id"]
    }]
    
    for i, calib in enumerate(phase2_calibs, 1):
        run_id, metrics, out_path = execute_single_run(
            clf_key=best_clf, ds_name="dataset", tier=best_tier, calib=calib,
            fast_mode=fast_mode, run_idx_info=f"[Phase 2: {i}/3]"
        )
        phase2_results.append({
            "calib": calib,
            "roc_auc": metrics.get("roc_auc", 0.0),
            "ece": metrics.get("ece", 0.0),
            "out_path": out_path,
            "run_id": run_id
        })
        
    # Select calibration minimizing ECE (Primary) while keeping ROC AUC strong (Secondary)
    base_auc = best_p1["roc_auc"]
    viable_calibs = [r for r in phase2_results if r["roc_auc"] >= base_auc - 0.015]
    if not viable_calibs:
        viable_calibs = phase2_results
    best_p2 = sorted(viable_calibs, key=lambda x: (x["ece"], -x["roc_auc"]))[0]
    best_calib = best_p2["calib"]
    best_calib_path = best_p2["out_path"]
    
    print("\n--- PHASE 2 CALIBRATION RANKINGS (by ECE minimization) ---")
    for r in sorted(phase2_results, key=lambda x: (x["ece"], -x["roc_auc"])):
        print(f"  Calib '{r['calib']}': ECE={r['ece']:.4f} | ROC AUC={r['roc_auc']:.4f}")
    print(f"\n[+] Phase 2 Winner Selected: {best_calib} (ECE: {best_p2['ece']:.4f})")
    
    # Save best_model_config.json
    results_dir = PROJECT_ROOT / "experiments" / "evaluation_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    config_path = results_dir / "best_model_config.json"
    
    config_data = {
        "best_classifier": best_clf,
        "best_hyperparameters": best_params,
        "best_feature_set": format_feature_set_name(best_tier),
        "best_calibration": best_calib,
        "best_run_id": best_p2["run_id"],
        "baseline_roc_auc": best_p2["roc_auc"],
        "baseline_ece": best_p2["ece"],
        "selected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
    print(f"[+] Saved frozen configuration to: {config_path}")
    
    # Copy complete pipeline into evaluation_models/best_pipeline/
    best_pipe_dir = PROJECT_ROOT / "experiments" / "evaluation_models" / "best_pipeline"
    if best_pipe_dir.exists():
        shutil.rmtree(best_pipe_dir)
    best_pipe_dir.mkdir(parents=True, exist_ok=True)
    
    for item in best_calib_path.iterdir():
        if item.is_file():
            shutil.copy2(item, best_pipe_dir / item.name)
    print(f"[+] Copied complete winning pipeline to: {best_pipe_dir}")
    
    
    print("\n=== PHASE 3: PROMPT ENGINEERING COMPARISON (2 new experiments) ===")
    print(f"    Frozen Model: {best_clf} | Tier: {format_feature_set_name(best_tier)} | Calib: {best_calib}")
    print("    Comparing: dataset (v5, reused) vs v1 vs freetext")
    
    for i, ds in enumerate(["v1", "freetext"], 1):
        execute_single_run(
            clf_key=best_clf, ds_name=ds, tier=best_tier, calib=best_calib,
            fast_mode=fast_mode, run_idx_info=f"[Phase 3: {i}/2]"
        )
        
        
    print("\n=== PHASE 4: LLM SCALING COMPARISON (1 new experiment) ===")
    print(f"    Frozen Model: {best_clf} | Tier: {format_feature_set_name(best_tier)} | Calib: {best_calib}")
    print("    Comparing: dataset (Qwen3 4B, reused) vs qwen_35b (Qwen3.5 35B)")
    
    execute_single_run(
        clf_key=best_clf, ds_name="qwen_35b", tier=best_tier, calib=best_calib,
        fast_mode=fast_mode, run_idx_info="[Phase 4: 1/1]"
    )
    
    print(f"\n=== TFG_Evaluation 4-PHASE STUDY COMPLETED IN {t_dur/60:.2f} MINUTES ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run in fast mode.")
    args = parser.parse_args()
    run_study(fast_mode=args.fast)
