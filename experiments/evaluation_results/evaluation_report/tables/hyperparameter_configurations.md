### Table 9: Hyperparameter Configurations of Winning Classifiers Across Evaluation Phases

| Classifier                    | Best Hyperparameters                                                       | CV Score (ROC AUC) | Test ROC AUC |
| ----------------------------- | -------------------------------------------------------------------------- | ------------------ | ------------ |
| Random Forest (Tier C2)       | class_weight='balanced', max_depth=3, min_samples_leaf=6, n_estimators=100 | 0.5764             | 0.6733       |
| XGBoost (Tier C2)             | lr=0.05, max_depth=3, min_child_weight=6, n_estimators=150                 | 0.5814             | 0.6710       |
| Logistic Regression (Tier C3) | C=1.0, class_weight='balanced', penalty='l2', solver='lbfgs'               | 0.6210             | 0.6590       |
| Random Forest (Tier v1)       | class_weight='balanced', max_depth=3, min_samples_leaf=6, n_estimators=150 | 0.6928             | 0.6763       |
| Random Forest (Tier qwen_35b) | class_weight=None, max_depth=5, min_samples_leaf=2, n_estimators=100       | 0.5995             | 0.6360       |

---
