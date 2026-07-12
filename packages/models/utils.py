"""
Utility functions and classes for model discovery, metric loading, ranking, and export.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


class ModelComparatorUtils:
    """Helper methods for discovering, loading, validating, ranking, and exporting ML models."""

    @staticmethod
    def discover_metrics_files(base_dir: Path) -> List[Path]:
        """
        Recursively discover all metrics.json files inside base_dir using Path.rglob().
        """
        if not base_dir.exists():
            print(f"[WARNING] Base directory {base_dir} does not exist.")
            return []
        return sorted(list(base_dir.rglob("metrics.json")))

    @staticmethod
    def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Safely load a JSON file with graceful error handling.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not read or parse {file_path}: {e}")
            return None

    @staticmethod
    def flatten_metrics_payload(payload: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """
        Normalize and flatten the nested metrics.json payload into a single record dictionary.
        """
        config = payload.get("configuration", {})
        dataset = payload.get("dataset", {})
        training = payload.get("training", {})
        hyper = payload.get("hyperparameters", {})
        metrics = payload.get("metrics", {})

        # Derive experiment folder relative path
        rel_path = str(file_path.parent)
        abs_path = str(file_path.parent.resolve())

        # Model file path if present or assumed
        model_path = payload.get("model_path", os.path.join(abs_path, "model.pkl"))

        record = {
            "algorithm": payload.get("algorithm", "Unknown"),
            "experiment": payload.get("experiment", "Unknown"),
            "mode": config.get("mode", "baseline"),
            "index": config.get("index", 0),
            "approach": config.get("approach", "baseline"),
            "feature_set": dataset.get("feature_set", payload.get("experiment", "Unknown")),
            "n_features": dataset.get("n_features", len(dataset.get("features", []))),
            "train_samples": training.get("train_samples", 0),
            "test_samples": training.get("test_samples", 0),
            "scaler": training.get("scaler", "None"),
            "calibration": training.get("calibration", "None"),
            "accuracy": float(metrics.get("accuracy", 0.0)),
            "precision": float(metrics.get("precision", 0.0)),
            "recall": float(metrics.get("recall", 0.0)),
            "f1_score": float(metrics.get("f1_score", 0.0)),
            "roc_auc": float(metrics.get("roc_auc", 0.0)),
            "brier_score": float(metrics.get("brier_score", 1.0)),
            "training_time_seconds": float(metrics.get("training_time_seconds", 0.0)),
            "prediction_time_seconds": float(metrics.get("prediction_time_seconds", 0.0)),
            "hyperparameters_str": json.dumps(hyper),
            "hyperparameters_dict": hyper,
            "metrics_dict": metrics,
            "classification_report": payload.get("classification_report", {}),
            "file_path": str(file_path),
            "model_path": model_path,
            "abs_path": abs_path,
            "rel_path": rel_path,
        }
        return record

    @classmethod
    def load_all_experiments(cls, base_dir: Path) -> pd.DataFrame:
        """
        Discover and load all experiment metrics into a sorted Pandas DataFrame.
        """
        print("[*] Loading experiments...")
        files = cls.discover_metrics_files(base_dir)
        print(f"[*] Found {len(files)} metrics.json files.")

        records = []
        for path in files:
            payload = cls.load_json_file(path)
            if payload is not None:
                records.append(cls.flatten_metrics_payload(payload, path))

        if not records:
            print("[WARNING] No valid experiment records loaded.")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        # Normalize strings
        for col in ["algorithm", "experiment", "mode", "approach"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # Sort alphabetically by algorithm, experiment, mode, index
        df.sort_values(by=["algorithm", "experiment", "mode", "index"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    @staticmethod
    def rank_models(df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute rankings for each model and sort by overall score.
        """
        if df.empty:
            return df

        df = df.copy()
        # Compute ranks (1 is best)
        df["rank_f1"] = df["f1_score"].rank(ascending=False, method="min")
        df["rank_roc_auc"] = df["roc_auc"].rank(ascending=False, method="min")
        df["rank_acc"] = df["accuracy"].rank(ascending=False, method="min")
        df["rank_brier"] = df["brier_score"].rank(ascending=True, method="min")
        df["rank_pred_time"] = df["prediction_time_seconds"].rank(ascending=True, method="min")

        # Composite score
        df["composite_rank_score"] = (
            df["rank_f1"] * 3.0 +
            df["rank_roc_auc"] * 2.5 +
            df["rank_acc"] * 1.5 +
            df["rank_brier"] * 2.0 +
            df["rank_pred_time"] * 1.0
        )
        df.sort_values(
            by=["f1_score", "roc_auc", "accuracy", "brier_score", "prediction_time_seconds"],
            ascending=[False, False, False, True, True],
            inplace=True
        )
        df["overall_rank"] = range(1, len(df) + 1)
        df.reset_index(drop=True, inplace=True)
        return df

    @staticmethod
    def select_best_model(df: pd.DataFrame, output_dir: Path) -> Dict[str, Any]:
        """
        Automatically select the best model using strict priority and save best_model.json.
        Priority:
        1. Highest F1-score
        2. Highest ROC-AUC
        3. Highest Accuracy
        4. Lowest Brier Score
        5. Lowest Prediction Time
        """
        print("[*] Selecting best model...")
        if df.empty:
            return {}

        sorted_df = df.sort_values(
            by=["f1_score", "roc_auc", "accuracy", "brier_score", "prediction_time_seconds"],
            ascending=[False, False, False, True, True]
        )
        best_row = sorted_df.iloc[0]

        reason = (
            f"Selected as top performing model achieving F1-score={best_row['f1_score']:.4f}, "
            f"ROC-AUC={best_row['roc_auc']:.4f}, Accuracy={best_row['accuracy']:.4f}, and "
            f"Brier Score={best_row['brier_score']:.4f}."
        )

        best_payload = {
            "algorithm": str(best_row["algorithm"]),
            "experiment": str(best_row["experiment"]),
            "configuration": {
                "mode": str(best_row["mode"]),
                "index": int(best_row["index"]),
                "approach": str(best_row["approach"]),
            },
            "dataset": {
                "feature_set": str(best_row["feature_set"]),
                "n_features": int(best_row["n_features"]),
            },
            "hyperparameters": best_row["hyperparameters_dict"],
            "metrics": {
                "accuracy": float(best_row["accuracy"]),
                "precision": float(best_row["precision"]),
                "recall": float(best_row["recall"]),
                "f1_score": float(best_row["f1_score"]),
                "roc_auc": float(best_row["roc_auc"]),
                "brier_score": float(best_row["brier_score"]),
                "training_time_seconds": float(best_row["training_time_seconds"]),
                "prediction_time_seconds": float(best_row["prediction_time_seconds"]),
            },
            "absolute_path": str(best_row["abs_path"]),
            "relative_path": str(best_row["rel_path"]),
            "reason_for_selection": reason,
            "timestamp": datetime.now().isoformat(),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / "best_model.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(best_payload, f, indent=4)

        return best_payload

    @staticmethod
    def export_tables(df: pd.DataFrame, output_dir: Path) -> None:
        """
        Export comparison tables to CSV and Excel formats.
        """
        print("[*] Saving outputs...")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. all_models.csv
        export_cols = [
            "overall_rank", "algorithm", "experiment", "mode", "approach",
            "accuracy", "precision", "recall", "f1_score", "roc_auc", "brier_score",
            "training_time_seconds", "prediction_time_seconds", "n_features"
        ]
        cols_present = [c for c in export_cols if c in df.columns]
        df[cols_present].to_csv(output_dir / "all_models.csv", index=False)

        # 2. comparison_table.csv & comparison_table.xlsx
        df[cols_present].to_csv(output_dir / "comparison_table.csv", index=False)
        try:
            df[cols_present].to_excel(output_dir / "comparison_table.xlsx", index=False)
        except Exception as e:
            print(f"[WARNING] Could not write Excel table: {e}")

        # 3. ranking.csv
        ranking_cols = ["overall_rank", "algorithm", "experiment", "approach", "f1_score", "roc_auc", "accuracy", "brier_score"]
        r_cols_present = [c for c in ranking_cols if c in df.columns]
        df[r_cols_present].to_csv(output_dir / "ranking.csv", index=False)

    @staticmethod
    def generate_summary_stats(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate executive summary statistics across all evaluated models.
        """
        if df.empty:
            return {}

        best_row = df.iloc[0]
        summary = {
            "total_models": len(df),
            "algorithms_evaluated": sorted(df["algorithm"].unique().tolist()),
            "experiments_evaluated": sorted(df["experiment"].unique().tolist()),
            "best_algorithm": str(best_row["algorithm"]),
            "best_experiment": str(best_row["experiment"]),
            "mean_f1": float(df["f1_score"].mean()),
            "mean_roc_auc": float(df["roc_auc"].mean()),
            "mean_accuracy": float(df["accuracy"].mean()),
            "mean_brier_score": float(df["brier_score"].mean()),
        }
        return summary
