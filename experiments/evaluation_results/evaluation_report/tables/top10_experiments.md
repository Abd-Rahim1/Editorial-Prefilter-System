### Table 10: Top 10 Best Performing Experiments in TFG_Evaluation Ranked by ROC AUC

| rank | experiment_id                          | classifier          | feature_tier | calibration | prompt_version | roc_auc | mcc    | f1     | ece    |
| ---- | -------------------------------------- | ------------------- | ------------ | ----------- | -------------- | ------- | ------ | ------ | ------ |
| 1    | random_forest_ExpC2_dataset_auto       | Random Forest       | C2           | auto        | v5             | 0.678   | 0.2227 | 0.7083 | 0.078  |
| 2    | random_forest_ExpC2_dataset_sigmoid    | Random Forest       | C2           | sigmoid     | v5             | 0.678   | 0.2227 | 0.7083 | 0.078  |
| 3    | random_forest_ExpC2_v1_none            | Random Forest       | C2           | none        | v1             | 0.6763  | 0.1531 | 0.5766 | 0.1358 |
| 4    | random_forest_ExpC2_dataset_none       | Random Forest       | C2           | none        | v5             | 0.6733  | 0.2403 | 0.6822 | 0.0589 |
| 5    | xgboost_ExpC2_dataset_none             | Xgboost             | C2           | none        | v5             | 0.671   | 0.2972 | 0.7031 | 0.0372 |
| 6    | random_forest_ExpC2_dataset_isotonic   | Random Forest       | C2           | isotonic    | v5             | 0.6708  | 0.2609 | 0.6825 | 0.0822 |
| 7    | logistic_regression_ExpC3_dataset_none | Logistic Regression | C3           | none        | v5             | 0.659   | 0.0643 | 0.6797 | 0.0124 |
| 8    | logistic_regression_ExpC2_dataset_none | Logistic Regression | C2           | none        | v5             | 0.6517  | 0.2159 | 0.6325 | 0.0672 |
| 9    | logistic_regression_ExpD_dataset_none  | Logistic Regression | D            | none        | v5             | 0.6423  | 0.2693 | 0.661  | 0.0845 |
| 10   | random_forest_ExpC3_dataset_none       | Random Forest       | C3           | none        | v5             | 0.6397  | 0.2304 | 0.6055 | 0.0469 |

---
