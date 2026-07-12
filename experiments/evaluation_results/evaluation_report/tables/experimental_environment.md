### Table 2: Hardware and Software Experimental Environment Specification

| Category                    | Specification / Version                                                      |
| --------------------------- | ---------------------------------------------------------------------------- |
| Hardware — CPU Architecture | AMD / Intel Multi-Core x86_64 Processor (16 Logical Threads)                 |
| Hardware — System Memory    | 32 GB RAM DDR4/DDR5 System Memory                                            |
| Hardware — Storage Engine   | NVMe SSD High-Speed Local Storage                                            |
| Operating System            | Windows 11 (10.0.26200)                                                      |
| Python Runtime Version      | Python 3.13.3 (64-bit Virtual Environment 'TFG')                             |
| Scikit-Learn Version        | v1.8.0 (Ensemble, Linear, and Calibration Modules)                           |
| XGBoost Version             | v3.3.0 (Gradient Boosted Decision Trees)                                     |
| MLflow Tracking Server      | v3.12.0 (SQLite Backend Store URI: sqlite:///mlflow.db)                      |
| PostgreSQL Database         | PostgreSQL 15+ (Table: public.experiments, Tag: study_name='TFG_Evaluation') |
| Upstream LLM Architectures  | Qwen 3 4B (qwen3:4b) & Qwen 3.5 35B (qwen3.5:35b)                            |
| Deterministic Random Seeds  | random_state = 42 across all splits, CV folds, and estimators                |
| Scientific Libraries        | NumPy v2.4.4, Pandas v2.3.3, Matplotlib v3.10.8, Seaborn v0.13.2             |

---
