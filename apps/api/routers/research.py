import os
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from config import get_db, AuditLog
from auth import TokenData, require_role

# Defensive execution wrappers in case MLflow is isolated or offline
try:
    import mlflow
    import mlflow.sklearn
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

router = APIRouter(prefix="/api/research", tags=["Research & Machine Learning Matrix"])

class TrainingPayload(BaseModel):
    model_type: str  # Accepted strings: "logistic_regression" or "xgboost"
    test_size: float = 0.25
    random_state: int = 42

@router.post("/train")
def train_research_model(
    payload: TrainingPayload,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"]))
):
    """
    Reads active platform feature weights, processes calibration matrices,
    and logs model footprints securely inside MLflow tracking layers.
    """
    # 1. Pipeline Feature Extraction Step
    query_string = """
        SELECT 
            m.total_word_count, m.num_pages,
            f.integrity_risk_score, f.structure_validity_score, f.content_coherence_score, f.citation_quality_score,
            m.status
        FROM manuscripts m
        JOIN model_runs r ON m.id = r.manuscript_id
        CROSS JOIN LATERAL jsonb_to_record(r.parsed_output) as f(
            integrity_risk_score float, structure_validity_score float, 
            content_coherence_score float, citation_quality_score float
        );
    """
    
    raw_data = db.execute(query_string).fetchall()
    if len(raw_data) < 4:
        raise HTTPException(status_code=400, detail="Insufficient dataset size. Process at least 4 manuscripts to run ML modules.")
        
    # Convert parameters structurally into memory matrices
    df = pd.DataFrame(raw_data, columns=["word_count", "page_count", "integrity", "structure", "coherence", "citation", "status"])
    df["target"] = df["status"].apply(lambda val: 1 if val == "Accepted" else 0)
    
    X = df[["word_count", "page_count", "integrity", "structure", "coherence", "citation"]].fillna(0.5)
    y = df["target"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=payload.test_size, random_state=payload.random_state)
    
    # 2. Select and Train Model Architecture
    chosen_type = payload.model_type.lower()
    if chosen_type == "logistic_regression":
        model = LogisticRegression(max_iter=1000)
        params = {"model_class": "LogisticRegression", "C": 1.0}
    elif chosen_type == "xgboost":
        if not HAS_XGB:
            raise HTTPException(status_code=501, detail="XGBoost wheel binaries are not linked natively in this python context environment.")
        model = XGBClassifier(use_label_encoder=False, eval_metric="logloss")
        params = {"model_class": "XGBClassifier", "n_estimators": 100, "max_depth": 6}
    else:
        raise HTTPException(status_code=400, detail="Unknown selection pattern classification matrix requested.")
        
    model.fit(X_train, y_train)
    accuracy = float(model.score(X_test, y_test))
    
    # 3. Handle MLflow Tracking Interconnections Defensively
    mlflow_status = "Skipped (mlflow package not detected)"
    if HAS_MLFLOW:
        try:
            # Enforce local micro-tracking isolation registers
            mlflow.set_tracking_uri("file:./mlruns")
            mlflow.set_experiment("TFG_Editorial_Calibration_Layer")
            
            with mlflow.start_run():
                mlflow.log_params(params)
                mlflow.log_param("test_split_ratio", payload.test_size)
                mlflow.log_metric("accuracy_score", accuracy)
                mlflow.sklearn.log_model(model, "calibrated_tfg_classifier")
                mlflow_status = "Successfully committed into local MLflow repository registers."
        except Exception as log_error:
            mlflow_status = f"Tracking connected, but metadata step failed: {str(log_error)}"

    # 4. Save audit log record entry
    audit = AuditLog(
        action=f"TRAIN_{chosen_type.upper()}",
        details=f"Model calibrated by {current_user.username}. Validation Accuracy achieved: {accuracy * 100:.2f}%."
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True,
        "selected_architecture": chosen_type,
        "metrics": {
            "validation_accuracy": accuracy,
            "training_samples_count": len(X_train),
            "testing_samples_count": len(X_test)
        },
        "mlflow_status": mlflow_status
    }