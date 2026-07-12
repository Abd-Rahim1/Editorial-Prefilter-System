# Winner Artifact Verification Report

## Authoritative Source
The authoritative source for the winning evaluation model is:
`experiments/evaluation_models/best_pipeline/`

## Exact Parameters
- **Classifier Class**: `RandomForestClassifier`
- **n_estimators**: 150
- **max_depth**: 3
- **min_samples_leaf**: 4
- **min_samples_split**: 2
- **class_weight**: None
- **max_features**: `sqrt`
- **random_state**: 42

## Exact Feature Schema
- **Feature Tier**: C2
- **Feature Count**: 10
- **Feature Order**: 
  1. `argumentative_quality`
  2. `conference`
  3. `critical_rules_failed`
  4. `experimental_strength`
  5. `methodological_strength`
  6. `overall_quality`
  7. `risk_multiplier`
  8. `scope_alignment`
  9. `structural_completeness`
  10. `total_rules_failed`

## Exact Class Mapping
- **Classes**: `[0, 1]`
- **Positive Class (Accept)**: `1`
- **Predict Proba Index**: `1`

## Artifact Hashes
- **Winner model.pkl SHA-256**: `583c3c0c70cf5b6d4a238727940e34ee13e68ab17248f5862a02d34b8d389eb9`
- **Production best_pipeline.joblib SHA-256**: `583c3c0c70cf5b6d4a238727940e34ee13e68ab17248f5862a02d34b8d389eb9`

## Production Artifact Match Result
- **Status**: **MATCH**
- The production artifact `packages/calibration/models/best_pipeline.joblib` is byte-for-byte identical to the original serialized evaluation winner.
