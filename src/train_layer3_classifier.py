import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import pickle
from pathlib import Path

def main():
    print("=" * 60)
    print("TRAINING LAYER 3 CALIBRATED CLASSIFIER")
    print("=" * 60)

    dataset_path = Path("outputs/layer3_training_dataset.csv")
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return

    # Load dataset
    df = pd.read_csv(dataset_path)

    # 1. Drop rows with missing target
    initial_len = len(df)
    df = df.dropna(subset=['true_label'])
    print(f"Loaded {len(df)} rows (dropped {initial_len - len(df)} missing labels).")

    if len(df) == 0:
        print("Error: No data available with valid labels.")
        return

    features = [
        'missing_critical_sections',
        'has_abstract',
        'has_introduction',
        'has_methodology',
        'has_experiments',
        'has_conclusions',
        'word_count',
        'page_count',
        'suspicious_score',
        'credibility_score',
        'evidence_strength',
        'coherence_score',
        'reproducibility_score',
        'theoretical_rigor_score',
        'methodology_missing_confirmed',
        'methodology_like_content_found_elsewhere'
    ]

    # Verify features exist
    missing_features = [f for f in features if f not in df.columns]
    if missing_features:
        print(f"Warning: Missing features in dataset: {missing_features}")
        # Keep only available features
        features = [f for f in features if f in df.columns]

    X = df[features].copy()
    y = df['true_label'].astype(int)

    # 2. Convert boolean columns to 0/1
    for col in X.select_dtypes(include=['bool', 'object']).columns:
        # Convert true/false strings or booleans to 1/0
        X[col] = X[col].astype(str).str.lower().map({'true': 1, 'false': 0, '1': 1, '0': 0, '1.0': 1, '0.0': 0})

    # Convert all columns to numeric, coercing errors to NaN
    X = X.apply(pd.to_numeric, errors='coerce')

    # 3. Fill missing numeric values with median
    X = X.fillna(X.median())

    # Check class distribution
    class_counts = y.value_counts()
    print(f"Class distribution:\n{class_counts.to_string()}")
    
    if len(class_counts) < 2:
        print("Error: Need at least 2 classes to train classifier. Ensure you have both accepted and rejected papers.")
        return

    # 5. Train/test split with stratify=true_label
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError as e:
        print(f"Train/test split failed (possibly too few samples of one class): {e}")
        return

    print(f"Training set: {len(X_train)} samples")
    print(f"Testing set: {len(X_test)} samples")

    # 4. Train Logistic Regression
    clf = LogisticRegression(random_state=42, max_iter=1000)
    clf.fit(X_train, y_train)

    # Predictions
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1] if hasattr(clf, "predict_proba") else None

    # 6. Evaluate and print metrics
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    try:
        auc = roc_auc_score(y_test, y_prob) if y_prob is not None else "N/A"
    except ValueError:
        auc = "N/A (Only one class in y_test)"

    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    if isinstance(auc, float):
        print(f"ROC-AUC:   {auc:.4f}")
    else:
        print(f"ROC-AUC:   {auc}")
    print("\nConfusion Matrix:")
    print(cm)
    
    # 7. Save model
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    model_path = models_dir / "layer3_logistic_regression.pkl"
    
    with open(model_path, 'wb') as f:
        pickle.dump(clf, f)
        
    print("\n" + "=" * 60)
    print(f"Model saved to: {model_path.absolute()}")
    print("=" * 60)

if __name__ == "__main__":
    main()
