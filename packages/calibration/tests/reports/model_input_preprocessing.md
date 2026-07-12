# Exact Model-Facing Preprocessing Report (`Phase 4B`)

**Date:** July 9, 2026  
**Target Model Artifact:** `best_pipeline.joblib` (`TrainedModel id=1`, `Experiment id=388`)  
**Model Class:** `sklearn.ensemble._forest.RandomForestClassifier`  
**Status:** **Exact Preprocessing Path Verified & Proven**

---

## Executive Summary & Option Identification

Following deep inspection of the offline evaluation runners (`experiments/models/random_forest/train.py`, `experiments/models/common/trainer.py`), preprocessing pipelines (`packages/dataset/eda/07_eda_and_preprocessing.py`), database metadata (`TrainedModel id=1`), and internal decision tree split thresholds (`best_pipeline.joblib.estimators_[0...149]`), we definitively confirm the exact model-facing representation:

### Winner Training Representation: **Option A / Option C (Unscaled Numeric Features + Integer-Encoded Categorical `conference`)**

The winning **Experiment 388** (`Random Forest C2`) was trained on **Option C** (which maps to **Option A** for numeric values):
1. **`conference`** was categorical-encoded via `sklearn.preprocessing.LabelEncoder()` into integer codes `[0, 1, 2]`.
2. **All `9` numeric columns** (`argumentative_quality`, `critical_rules_failed`, `experimental_strength`, `methodological_strength`, `overall_quality`, `risk_multiplier`, `scope_alignment`, `structural_completeness`, `total_rules_failed`) were passed to `RandomForestClassifier.fit()` as **100% RAW, UNSCALED values**.

---

## Detailed Investigation & Answers to Required Points

### 1. Exact Variable Passed to Winner `model.fit()`
- In `experiments/models/random_forest/train.py`, `train_random_forest()` invokes the universal experiment runner with:
  ```python
  run_experiment_train(
      estimator=RandomForestClassifier(random_state=42),
      param_grid=PARAM_GRIDS["random_forest"],
      classifier_name="Random_Forest",
      use_scaler=False,  # <-- CRITICAL: Explicitly False for Random Forest
      dataset_variant="dataset",
      tier="C2"
  )
  ```
- Inside `experiments/models/common/trainer.py` (lines 64–72), when `use_scaler=False`, `StandardScaler()` is skipped entirely:
  ```python
  if use_scaler:
      ...
  else:
      X_train = X_train_unscaled.reset_index(drop=True)
      X_test = X_test_unscaled.reset_index(drop=True)
  ```
- `X_train` (`X_train_unscaled`) passed to `grid.fit(X_train, y_train)` is a pandas DataFrame containing the exactly `10` canonical features loaded from `data/prepared/dataset/dataset.csv` (`data/prepared/v5/dataset.csv`).

---

### 2. Whether Scaling Was Applied
- **No scaling (`StandardScaler`, `RobustScaler`, or `MinMaxScaler`) was applied to any feature passed to `RandomForestClassifier.fit()`.**
- Why `X_test_scaled.csv` exists: `packages/dataset/eda/07_eda_and_preprocessing.py` (Step 13) exports side-by-side scaled datasets (`X_train_scaled.csv` and `X_test_scaled.csv`) for linear classifiers (e.g., Logistic Regression) and EDA visualizations. However, `RandomForestClassifier` (Experiment 388) explicitly bypassed those scaled CSVs and trained directly on `dataset.csv` (`use_scaler=False`).

---

### 3. Which Columns Were Scaled
- **`0` Columns (None).**
- All feature columns retained their raw empirical ranges during training and grid search.

---

### 4. Which Columns Were Not Scaled
- **All `10` Columns (`100%`).**
- Internal decision tree threshold inspection across the `150` estimators in `best_pipeline.joblib` confirms that the model learned split boundaries directly within these natural unscaled ranges:

| Feature Name | Empirical Minimum | Empirical Maximum | Model Split Threshold Range inside `best_pipeline.joblib` |
|---|---|---|---|
| `argumentative_quality` | `0.20` | `0.95` | `[0.3250, 0.9350]` |
| `conference` | `0.00` | `2.00` | `[0.5000, 1.5000]` |
| `critical_rules_failed` | `0.00` | `3.00` | `[0.5000, 1.5000]` |
| `experimental_strength` | `0.00` | `0.95` | `[0.0500, 0.9350]` |
| `methodological_strength` | `0.15` | `0.98` | `[0.3500, 0.9350]` |
| `overall_quality` | `0.15` | `0.97` | `[0.2750, 0.9400]` |
| `risk_multiplier` | `0.09` | `6.40` | `[0.1750, 5.6000]` |
| `scope_alignment` | `0.30` | `1.00` | `[0.5250, 0.9750]` |
| `structural_completeness`| `0.20` | `1.00` | `[0.2250, 0.9250]` |
| `total_rules_failed` | `3.00` | `10.00`| `[3.5000, 7.5000]` |

---

### 5. Exact `conference` Encoding
- In `packages/dataset/eda/07_eda_and_preprocessing.py` (`lines 262–266`), the categorical string column `conference` from `data/processed/dataset.csv` was encoded using `sklearn.preprocessing.LabelEncoder().fit_transform(df["conference"])`.
- The exact deterministic mapping dictionary is:
  ```json
  {
    "acl_2017": 0,
    "conll_2016": 1,
    "iclr_2017": 2
  }
  ```
- (`234` manuscripts mapped to `0`, `39` mapped to `1`, `276` mapped to `2`).
- Decision tree splits on `conference` occur exclusively at `threshold = 0.5` (separating `0` from `1/2`) and `threshold = 1.5` (separating `0/1` from `2`).

---

### 6. Whether Scaling Parameters Were Persisted
- **No scaling parameters or scaler artifacts were persisted.**
- In `trained_models` table (`id=1`), the column `scaler_path` is explicitly set to `NULL` (`None`).
- The persisted artifact `best_pipeline.joblib` (`2.66 MB`, SHA-256: `955e09f8714ba36ce0deae5decebbcf7c61bf8bc0d74fc100803ee5283ffaa7a`) is a standalone `<class 'sklearn.ensemble._forest.RandomForestClassifier'>` instance without any enclosed `Pipeline`, `StandardScaler`, `ColumnTransformer`, or preprocessing stage.

---

### 7. How Online Inference Reproduces the Transformation
Online serving (`Layer3Service.predict()`) accurately matches the winning training representation without requiring a scaler:
1. **Raw Feature Construction (`feature_builder.build_raw_features`)**: Merges Layer 1 rule outputs and Layer 2 Qwen LLM scores, resolving key aliases (`is_conference` -> `conference`, `credibility_score` -> `overall_quality`).
2. **Exact Risk Multiplier Calculation**: Dynamically computes `risk_multiplier = (1.0 - overall_quality) * total_rules_failed` using exact raw unscaled values.
3. **Schema Alignment & Validation (`feature_preprocessor.preprocess_features`)**: Orders the feature dictionary to strictly match `feature_schema.json` (`CANONICAL_C2_FEATURES`), casts inputs to `float`, and returns an unscaled 1-row DataFrame `X`.
4. **Model Inference (`Predictor.predict_probabilities`)**: Directly invokes `best_pipeline.joblib.predict_proba(X)`, passing unscaled numeric values (`0.15–6.40`) and numeric `conference` codes (`0.0, 1.0, 2.0`).

---

### 8. Training-Serving Parity Verification Result
- **Parity Status**: **100% EXACT PARITY (`PASS`)**
- As verified by `test_numerical_parity_across_dataset_rows` in `packages/calibration/tests/integration/test_training_serving_parity.py`:
  - For all `50` validation matrix rows tested across offline and online pipelines:
    $$\max_{i} \left| P(\text{Accept})_{\text{online}, i} - P(\text{Accept})_{\text{offline}, i} \right| < 10^{-7}$$
  - Full dataset verification across `549` manuscripts in `training_serving_parity.csv` confirms zero numerical drift or schema mismatch between offline evaluation (`Experiment 388`) and online production serving.

---

## Conclusion & Layer 3 Freeze Readiness
The exact model-facing preprocessing path has been rigorously traced, documented, and proven from source code (`train.py`, `trainer.py`, `07_eda_and_preprocessing.py`), database metadata (`TrainedModel id=1`), tree node split thresholds, and end-to-end parity tests. **Layer 3 is verified and ready for architectural freeze.**
