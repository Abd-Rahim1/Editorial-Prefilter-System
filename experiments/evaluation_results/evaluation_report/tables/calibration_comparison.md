### Table 6: Phase 2: Probability Calibration Strategy Comparison (Random Forest, Tier C2)

| calibration | roc_auc | ece    | brier_score | mcc    | f1     | accuracy |
| ----------- | ------- | ------ | ----------- | ------ | ------ | -------- |
| auto        | 0.678   | 0.078  | 0.2344      | 0.2227 | 0.7083 | 0.6182   |
| sigmoid     | 0.678   | 0.078  | 0.2344      | 0.2227 | 0.7083 | 0.6182   |
| none        | 0.6733  | 0.0589 | 0.2292      | 0.2403 | 0.6822 | 0.6273   |
| isotonic    | 0.6708  | 0.0822 | 0.2272      | 0.2609 | 0.6825 | 0.6364   |

---
