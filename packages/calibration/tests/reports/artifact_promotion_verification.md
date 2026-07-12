# Artifact Promotion Verification Report

## Verification Checklist
- [x] **File Presence**: `best_pipeline.joblib`, `feature_schema.json`, `metadata.json`, `checksums.json` are present in `packages/calibration/models/`.
- [x] **SHA-256 Match**: The production model SHA-256 (`583c3c0c70cf5b6d4a238727940e34ee13e68ab17248f5862a02d34b8d389eb9`) perfectly matches the evaluation winner.
- [x] **File Size**: Byte sizes match identically.
- [x] **Model Class**: `RandomForestClassifier` match confirmed.
- [x] **Model Parameters**: Hyperparameters match perfectly (`max_depth=3`, `n_estimators=150`, `min_samples_leaf=4`).
- [x] **Feature Schema**: Exact canonical C2 10-feature schema match confirmed.
- [x] **Metadata**: `metadata.json` successfully preserved study metrics.
- [x] **Calibration Method**: `none` confirmed.
- [x] **Classes**: `[0, 1]` mapping preserved.

## Conclusion
The artifact promotion process (`offline/promote_model.py`) was successful and flawless. The production artifact is mathematically and procedurally identical to the validated winner. No unintended serialization alterations occurred.
