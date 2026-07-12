# Chapter 5 Experimentation Framework: Reproduction Guide

This document provides complete, step-by-step instructions for reproducing all experiments, ablation studies, and evaluation comparisons for **Chapter 5** of the Bachelor's Thesis (*Trabajo de Fin de Grado - TFG*): *"Design and Implementation of an Automatic Scientific Paper Pre-filtering System Based on Large Language Models for Editorial Decision Support"*.

---

## 1. Architectural Highlights & Isolation Guarantee

The Chapter 5 experimentation framework is designed to be **modular**, **reproducible**, and **strictly non-intrusive**.
- **100% Production Isolation**: All experimentation scripts and models reside inside the `experiments/` directory. No production files in `packages/editorial_rules/`, `packages/llm_scoring/`, `packages/pipeline/`, `apps/api/`, or `apps/web/` have been modified.
- **Database Safety**: Results are synchronized exclusively into `public.experiments` and `public.trained_models`. The production inference table (`public.model_runs`) is **never** touched by the experimentation engine.
- **MLflow Tracking**: All parameters, metrics (13 metrics including ECE), tags, and visual artifacts (ROC curves, calibration curves, confusion matrices) are logged to a centralized MLflow database (`mlflow.db`).

---

## 2. Environment Setup & Installation

Ensure you are in the project root directory and using your Python virtual environment.

### Using PowerShell (Windows)
```powershell
# Navigate to project root
cd C:\Users\Document\OneDrive\Desktop\TFG\Project

# Activate virtual environment (adjust path if your venv name differs)
.\venv\Scripts\Activate.ps1

# Install required machine learning and reporting dependencies
pip install scikit-learn pandas numpy matplotlib seaborn mlflow xgboost openpyxl tabulate
```

---

## 3. Running Individual Experiments

You can execute targeted experiments across specific classifiers, dataset variants, and feature ablation tiers.

### Feature Ablation Tiers
- **Tier A (`--exp A`)**: Structural & Editorial Rules (Layer 1 features: word counts, section counts, citation metrics, rule pass/fail flags).
- **Tier B (`--exp B`)**: Semantic & LLM Evaluation (Layer 2 features: novelty score, rigor score, methodology score, confidence, recommendation).
- **Tier C (`--exp C`)**: Hybrid Layer 1 + Layer 2 (Combined structural and semantic features).
- **Tier D (`--exp D`)**: Hybrid + Engineered Document Statistics (Layer 1 + Layer 2 + readability ratios, density metrics, and composite scores).

### Dataset Variants (`--dataset`)
- `dataset`: Default standard training dataset (`dataset_training.csv` or `data/processed/dataset.csv`).
- `v1`: Version 1 prompt dataset (`dataset_v1.csv`).
- `freetext`: Free-text explanation dataset (`dataset_freetext.csv`).
- `qwen_35b`: High-capacity 35B LLM evaluation dataset (`dataset_qwen_35b.csv`).

### Terminal Commands (PowerShell)

**1. Train Logistic Regression on Hybrid Features (Exp C) with GridSearchCV & Calibration:**
```powershell
python experiments/models/logistic_regression/train.py --dataset dataset --exp C
```
*(Add `--fast` for a rapid verification run using a reduced hyperparameter grid).*

**2. Train Random Forest on Layer 1 Features (Exp A):**
```powershell
python experiments/models/random_forest/train.py --dataset dataset --exp A
```

**3. Train XGBoost on Engineered Features (Exp D):**
```powershell
python experiments/models/xgboost/train.py --dataset dataset --exp D
```

**4. Run Classical Reference Baselines (Dummy, Default LR, Default RF, Default XGB):**
```powershell
python experiments/baselines/run_classical_baselines.py --dataset dataset --exp C
```

---

## 4. Running the Full 48-Experiment Suite

To automatically execute the complete matrix required for Chapter 5 (4 datasets × 4 feature sets × 3 classifiers = 48 experiments) with automated calibration, artifact generation, MLflow logging, and PostgreSQL synchronization:

```powershell
# Run the entire suite (takes approximately 15-45 minutes depending on hardware)
python experiments/run_all_tfg_experiments.py
```

### Advanced Suite Options:
```powershell
# Fast verification run of the entire suite
python experiments/run_all_tfg_experiments.py --fast

# Run only on specific datasets or feature tiers
python experiments/run_all_tfg_experiments.py --datasets dataset freetext --tiers C D --classifiers xgboost random_forest

# Simulate execution without running training or touching DB
python experiments/run_all_tfg_experiments.py --dry-run
```

---

## 5. Viewing Results in MLflow UI

All experimental runs, hyperparameter grids, calibration curves, and evaluation metrics are tracked in MLflow.

### Launching MLflow UI
```powershell
# Start MLflow server pointing to local SQLite database
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```
Open your web browser and navigate to: [http://localhost:5000](http://localhost:5000)

**What to explore in MLflow:**
1. Select the **`TFG_Chapter5_Experiments`** experiment.
2. Compare runs by clicking the checkbox next to multiple models and selecting **Compare**.
3. View **Parallel Coordinates Plots** to analyze hyperparameter sensitivity.
4. Click on any individual run -> **Artifacts** tab to view generated figures:
   - `roc_curve.png` (Receiver Operating Characteristic)
   - `pr_curve.png` (Precision-Recall Curve)
   - `calibration_curve.png` (Reliability Diagram showing Isotonic vs Sigmoid vs Uncalibrated)
   - `confusion_matrix.png` (True/False Positives and Negatives)
   - `feature_importance.csv` (Ranked feature contribution weights)

---

## 6. PostgreSQL Synchronization & Verification

By default, completed runs are automatically synchronized into PostgreSQL by the master script. To run synchronization manually or check status:

### Manual Synchronization
```powershell
# Synchronize all finished MLflow runs into PostgreSQL
python experiments/sync_mlflow_to_postgres.py

# Simulate synchronization (dry-run)
python experiments/sync_mlflow_to_postgres.py --dry-run
```

### Verifying in PostgreSQL
Connect to your database using `psql` or pgAdmin and run:
```sql
-- View all Chapter 5 experiment records
SELECT id, experiment_name, model_version, created_at 
FROM experiments 
ORDER BY id DESC LIMIT 10;

-- View synchronized trained models and their metrics
SELECT id, model_version, training_dataset, auroc, ece, is_active, trained_at 
FROM trained_models 
ORDER BY auroc DESC LIMIT 10;
```
*Note: In accordance with Rule 11 of the system architecture, all newly synchronized models have `is_active = False`. An editorial administrator must manually promote a model via the Admin Dashboard or SQL to make it active in production.*

---

## 7. Exporting Comparison Tables for Chapter 5

To generate publication-ready tables summarizing classifier rankings, feature ablation results, prompt comparisons, and calibration impacts:

```powershell
python experiments/reports/export_results.py
```

### Generated Output Files
All tables are exported to `experiments/reports/outputs/`:
1. **`Chapter5_Comparison_Tables.md`**: A clean Markdown document formatted with standard tables ready to be copied directly into Chapter 5 of your thesis text.
2. **`Chapter5_Experimental_Results.xlsx`**: A multi-sheet Excel workbook containing:
   - `All Experiments` (Master spreadsheet of all runs)
   - `Classifier Ranking` (Mean/Max ROC AUC, F1, Accuracy, ECE per algorithm)
   - `Feature Set Ablation` (Comparison of Tier A vs B vs C vs D)
   - `Prompt Comparison` (Impact of prompt engineering versions)
   - `LLM & Dataset Comparison` (Performance across LLM evaluator variants)
   - `Calibration Impact` (ECE reduction via Isotonic Regression & Platt Scaling)
3. **`00_master_all_experiments.csv`** to **`05_calibration_impact.csv`**: Individual CSV files for easy ingestion into LaTeX or plotting software.

---

## 8. Summary of Evaluated Metrics

Every model evaluated by this framework computes the exact 13 metrics required for Chapter 5:
1. **Accuracy**: Overall classification correctness.
2. **Precision**: Positive predictive value (editorial acceptance accuracy).
3. **Recall (Sensitivity)**: True positive rate (capturing worthy manuscripts).
4. **F1-Score**: Harmonic mean of Precision and Recall.
5. **ROC AUC**: Area Under the Receiver Operating Characteristic Curve.
6. **PR AUC**: Area Under the Precision-Recall Curve (crucial for imbalanced editorial datasets).
7. **Balanced Accuracy**: Macro-average of sensitivity and specificity.
8. **Matthews Correlation Coefficient (MCC)**: Robust correlation measure for binary classification.
9. **Brier Score**: Mean squared difference between predicted probabilities and actual binary outcomes.
10. **Expected Calibration Error (ECE)**: Quantifies how closely predicted probability reflects empirical accuracy.
11. **Confusion Matrix**: Full breakdown of TP, FP, TN, FN counts.
12. **Training Duration**: Model fitting and grid search time (milliseconds/seconds).
13. **Inference Duration**: Prediction latency per batch/sample (milliseconds).
