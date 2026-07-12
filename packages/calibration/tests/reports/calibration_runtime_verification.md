# Calibration Runtime Verification Report

## Calibration Policy
The selected production strategy is reported as `calibration = none`.

## Verification Checklist
1. [x] **Metadata Check**: `metadata.json` confirms `calibration_method = "none"`.
2. [x] **No Extra Calibrator Online**: `service.py` and `predictor.py` invoke `predict_probabilities` directly on the loaded artifact without wrapping it in a post-hoc calibration function.
3. [x] **No Hidden Calibrator Inside Artifact**: The `best_pipeline.joblib` artifact is exactly a `RandomForestClassifier`, not a `CalibratedClassifierCV` wrapper.

## Conclusion
The online runtime correctly honors the uncalibrated nature of the winning Random Forest model. No double-calibration or hidden transformations are occurring.
