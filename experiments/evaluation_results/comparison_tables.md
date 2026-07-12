# Chapter 5: TFG_Evaluation Benchmarking Study — Comparison Tables

*Generated on: 2026-07-08 15:06:45 UTC | Total Experiments: 27*

## 1. Overall Top 10 Models Leaderboard

| Rank | Classifier | Dataset | Tier | Calib | ROC AUC | MCC | F1 Score | ECE | Train Time (s) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Random Forest** | `dataset` | C2 | auto | **0.6780** | 0.2227 | 0.7083 | 0.0780 | 0.00 |
| 2 | **Random Forest** | `dataset` | C2 | sigmoid | **0.6780** | 0.2227 | 0.7083 | 0.0780 | 0.00 |
| 3 | **Random Forest** | `v1` | C2 | none | **0.6763** | 0.1531 | 0.5766 | 0.1358 | 0.00 |
| 4 | **Random Forest** | `dataset` | C2 | none | **0.6733** | 0.2403 | 0.6822 | 0.0589 | 0.00 |
| 5 | **Xgboost** | `dataset` | C2 | none | **0.6710** | 0.2972 | 0.7031 | 0.0372 | 0.00 |
| 6 | **Random Forest** | `dataset` | C2 | isotonic | **0.6708** | 0.2609 | 0.6825 | 0.0822 | 0.00 |
| 7 | **Logistic Regression** | `dataset` | C3 | none | **0.6590** | 0.0643 | 0.6797 | 0.0124 | 0.00 |
| 8 | **Logistic Regression** | `dataset` | C2 | none | **0.6517** | 0.2159 | 0.6325 | 0.0672 | 0.00 |
| 9 | **Logistic Regression** | `dataset` | D | none | **0.6423** | 0.2693 | 0.6610 | 0.0845 | 0.00 |
| 10 | **Random Forest** | `dataset` | C3 | none | **0.6397** | 0.2304 | 0.6055 | 0.0469 | 0.00 |

---

## 2. Phase 1: ML Classifier & Feature Selection (`dataset.csv`, uncalibrated)

| Classifier | Feature Tier | ROC AUC | MCC | F1 Score | ECE | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest** | C2 | **0.6733** | 0.2403 | 0.6822 | 0.0589 | 0.2292 |
| **Xgboost** | C2 | **0.6710** | 0.2972 | 0.7031 | 0.0372 | 0.2266 |
| **Logistic Regression** | C3 | **0.6590** | 0.0643 | 0.6797 | 0.0124 | 0.2399 |
| **Logistic Regression** | C2 | **0.6517** | 0.2159 | 0.6325 | 0.0672 | 0.2350 |
| **Logistic Regression** | D | **0.6423** | 0.2693 | 0.6610 | 0.0845 | 0.2380 |
| **Random Forest** | C3 | **0.6397** | 0.2304 | 0.6055 | 0.0469 | 0.2355 |
| **Logistic Regression** | C | **0.6357** | 0.1764 | 0.6218 | 0.0689 | 0.2417 |
| **Random Forest** | D | **0.6313** | 0.2254 | 0.6613 | 0.0466 | 0.2344 |
| **Logistic Regression** | B | **0.6057** | -0.1318 | 0.5816 | 0.1917 | 0.2432 |
| **Random Forest** | B | **0.6030** | 0.2349 | 0.5981 | 0.0716 | 0.2381 |
| **Xgboost** | D | **0.5943** | 0.1514 | 0.6290 | 0.1110 | 0.2577 |
| **Xgboost** | C3 | **0.5850** | 0.1616 | 0.6617 | 0.1189 | 0.2481 |
| **Random Forest** | C | **0.5837** | 0.1688 | 0.6400 | 0.0312 | 0.2418 |
| **Logistic Regression** | C1 | **0.5635** | 0.1514 | 0.6290 | 0.0515 | 0.2469 |
| **Logistic Regression** | A | **0.5635** | 0.0219 | 0.6951 | 0.0170 | 0.2454 |
| **Xgboost** | B | **0.5223** | 0.0248 | 0.6119 | 0.1167 | 0.2579 |
| **Xgboost** | C | **0.4965** | 0.0034 | 0.5645 | 0.1485 | 0.2784 |
| **Random Forest** | A | **0.4687** | 0.0575 | 0.4255 | 0.0442 | 0.2514 |
| **Random Forest** | C1 | **0.4680** | 0.0490 | 0.3820 | 0.0524 | 0.2520 |
| **Xgboost** | C1 | **0.4520** | -0.0408 | 0.6946 | 0.0230 | 0.2507 |
| **Xgboost** | A | **0.4520** | -0.0408 | 0.6946 | 0.0230 | 0.2507 |

---

## 3. Phase 2: Calibration Selection (`Random Forest`, Tier `C2`)

| Calibration Method | ROC AUC | ECE | Brier Score | MCC | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`none`** | 0.6733 | **0.0589** | 0.2292 | 0.2403 | 0.6822 |
| **`auto`** | 0.6780 | **0.0780** | 0.2344 | 0.2227 | 0.7083 |
| **`sigmoid`** | 0.6780 | **0.0780** | 0.2344 | 0.2227 | 0.7083 |
| **`isotonic`** | 0.6708 | **0.0822** | 0.2272 | 0.2609 | 0.6825 |

---

## 4. Phase 3: Prompt Engineering Comparison (`Random Forest`, Tier `C2`, Calib `none`)

| Prompt Strategy | Dataset | LLM Model | ROC AUC | MCC | F1 Score | ECE |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **`v1`** | `v1` | `qwen3:4b` | **0.6763** | 0.1531 | 0.5766 | 0.1358 |
| **`v5`** | `dataset` | `qwen3:4b` | **0.6733** | 0.2403 | 0.6822 | 0.0589 |
| **`freetext`** | `freetext` | `qwen3:4b` | **0.6053** | 0.1884 | 0.6452 | 0.1049 |

---

## 5. Phase 4: LLM Parameter Scaling Comparison (`Random Forest`, Tier `C2`, Calib `none`)

| LLM Model Architecture | Dataset | Prompt | ROC AUC | MCC | F1 Score | ECE |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **`qwen3:4b`** | `dataset` | `v5` | **0.6733** | 0.2403 | 0.6822 | 0.0589 |
| **`qwen3.5:35b`** | `qwen_35b` | `v5` | **0.6360** | 0.1212 | 0.6519 | 0.0472 |