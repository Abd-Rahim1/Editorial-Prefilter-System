import os
import sys
import time
import argparse
import json
import joblib
import mlflow
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss

# Setup paths to import shared config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, MODELS_BASE_DIR)

from config import load_and_split_data, HYPERPARAMETERS, generate_run_plots, PROJECT_ROOT

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exp', type=str, required=True, choices=['A', 'B', 'C', 'D'])
    parser.add_argument('--mode', type=str, required=True, choices=['baseline', 'tuned'])
    parser.add_argument('--idx', type=int, default=0)
    args = parser.parse_args()
    
    # 1. Parameter resolution
    param_list = HYPERPARAMETERS["xgboost"][args.mode]
    params = param_list[args.idx] if (args.mode == "tuned" and args.idx < len(param_list)) else param_list[0]
    
    # 2. Output directory mapping
    approach_dir = "baseline" if args.mode == "baseline" else f"tuned_idx_{args.idx}"
    RUN_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "experiments", "models", "xgboost", approach_dir, f"exp_{args.exp}")
    
    MODELS_DIR = os.path.join(RUN_OUTPUT_DIR, "models")
    PLOTS_DIR = os.path.join(RUN_OUTPUT_DIR, "plots")
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)
    
    # 3. Load dynamically engineered feature sets
    print(f"[*] Loading data for XGBoost - Experiment {args.exp}...")
    X_train, X_test, y_train, y_test, scaler, feature_names = load_and_split_data(args.exp, scale=True)
    
    # 4. Initialize MLflow Experiment
    mlflow.set_experiment("TFG_Layer3_Models")
    run_name = f"XGBoost_{args.mode}_exp{args.exp}_idx{args.idx}"
    
    with mlflow.start_run(run_name=run_name):
        base_model = XGBClassifier(**params, random_state=42, use_label_encoder=False, eval_metric='logloss')
        calibrated_model = CalibratedClassifierCV(estimator=base_model, method="sigmoid", cv=5)
        
        # Train & Time
        start_train = time.time()
        calibrated_model.fit(X_train.values, y_train.values)
        train_time = time.time() - start_train
        
        # Predict & Time
        start_pred = time.time()
        y_pred = calibrated_model.predict(X_test.values)
        y_proba = calibrated_model.predict_proba(X_test.values)[:, 1]
        pred_time = time.time() - start_pred
        
        # Metrics Calculation
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_proba)
        brier_score = brier_score_loss(y_test.values, y_proba)
        
        print(f"📊 Calibrated Brier Score (Lower is better): {brier_score:.4f}")
        
        # Log to MLflow UI
        mlflow.log_param("model_name", "XGBoost")
        mlflow.log_param("random_state", 42)
        mlflow.log_param("train_test_ratio", "80/20")
        mlflow.log_param("feature_set", f"Exp_{args.exp}")
        mlflow.log_param("scaler_used", "StandardScaler")
        mlflow.log_param("calibration_method", "sigmoid_cv5")
        mlflow.log_params(params)
        
        mlflow.log_metric("Accuracy", acc)
        mlflow.log_metric("Precision", prec)
        mlflow.log_metric("Recall", rec)
        mlflow.log_metric("F1_Score", f1)
        mlflow.log_metric("ROC_AUC", roc_auc)
        mlflow.log_metric("Brier_Score", brier_score)
        mlflow.log_metric("Training_Time_s", train_time)
        mlflow.log_metric("Prediction_Time_s", pred_time)
        
        # 5. Export Local Artifacts (Pickles & Reports)
        model_path = os.path.join(MODELS_DIR, "model.pkl")
        scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
        report_path = os.path.join(MODELS_DIR, "classification_report.txt")
        
        joblib.dump(calibrated_model, model_path)
        joblib.dump(scaler, scaler_path)
            
        report_text = classification_report(y_test, y_pred, target_names=["Rejected (0)", "Accepted (1)"])
        with open(report_path, "w") as f:
            f.write(report_text)
            
        report_dict = classification_report(
            y_test,
            y_pred,
            target_names=["Rejected (0)", "Accepted (1)"],
            output_dict=True
        )
        
        metrics_path = os.path.join(MODELS_DIR, "metrics.json")
        metrics_payload = {
            "algorithm": "XGBoost",
            "experiment": args.exp,
            "configuration": {
                "mode": args.mode,
                "index": args.idx,
                "approach": approach_dir
            },
            "dataset": {
                "feature_set": f"Exp_{args.exp}",
                "n_features": len(feature_names),
                "features": list(feature_names)
            },
            "training": {
                "train_samples": int(len(X_train)),
                "test_samples": int(len(X_test)),
                "train_test_split": "80/20",
                "random_state": 42,
                "scaler": "StandardScaler" if scaler else "None",
                "calibration": "CalibratedClassifierCV(method='sigmoid', cv=5)"
            },
            "hyperparameters": params,
            "metrics": {
                "accuracy": float(acc),
                "precision": float(prec),
                "recall": float(rec),
                "f1_score": float(f1),
                "roc_auc": float(roc_auc),
                "brier_score": float(brier_score),
                "training_time_seconds": float(train_time),
                "prediction_time_seconds": float(pred_time)
            },
            "classification_report": report_dict
        }
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_payload, f, indent=4)
            
        # 6. Generate Mathematical Visualizations
        print(f"[*] Generating Evaluation Plots...")
        generate_run_plots(calibrated_model, X_test.values, y_test.values, y_pred, y_proba, feature_names, PLOTS_DIR, "XGBoost")
        
        # 7. Mirror Artifacts to MLflow
        mlflow.log_artifacts(MODELS_DIR, artifact_path="models")
        mlflow.log_artifacts(PLOTS_DIR, artifact_path="plots")
        
        print(f"Success! Run Complete. Artifacts saved to: {RUN_OUTPUT_DIR}")

if __name__ == "__main__":
    main()