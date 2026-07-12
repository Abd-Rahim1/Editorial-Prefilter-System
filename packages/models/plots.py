"""
Plot generation module using pure matplotlib for publication-quality comparison charts.
"""

import os
from pathlib import Path
from typing import List
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class ModelComparatorPlots:
    """Generates all 13 publication-quality comparison figures using pure matplotlib."""

    @staticmethod
    def _setup_figure(figsize=(10, 6)):
        fig, ax = plt.subplots(figsize=figsize, facecolor="white")
        ax.set_facecolor("white")
        ax.grid(True, linestyle="--", alpha=0.5, color="#CCCCCC")
        return fig, ax

    @classmethod
    def plot_metric_bar(cls, df: pd.DataFrame, metric_col: str, title: str, ylabel: str, output_path: Path, ascending: bool = False):
        if df.empty or metric_col not in df.columns:
            return
        sorted_df = df.sort_values(by=metric_col, ascending=ascending).copy()
        labels = [f"{row['algorithm']} ({row['experiment']}-{row['approach']})" for _, row in sorted_df.iterrows()]
        values = sorted_df[metric_col].values

        fig, ax = cls._setup_figure(figsize=(max(10, len(labels) * 0.5), 6))
        colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(values))) if not ascending else plt.cm.Reds(np.linspace(0.4, 0.9, len(values)))
        bars = ax.bar(range(len(labels)), values, color=colors, edgecolor="#111111", linewidth=0.8)

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
        ax.set_title(title, fontsize=14, weight="bold", pad=15)
        ax.set_ylabel(ylabel, fontsize=11, weight="bold")
        ax.set_xlabel("Model Configurations", fontsize=11, weight="bold")

        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.3f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

        fig.tight_layout()
        fig.savefig(output_path, dpi=300, facecolor="white")
        plt.close(fig)

    @classmethod
    def generate_all_plots(cls, df: pd.DataFrame, output_dir: Path) -> None:
        """
        Generate all required comparison charts.
        """
        print("[*] Generating charts...")
        output_dir.mkdir(parents=True, exist_ok=True)
        if df.empty:
            return

        # 1. accuracy.png
        cls.plot_metric_bar(df, "accuracy", "Model Accuracy Comparison", "Accuracy", output_dir / "accuracy.png", ascending=False)
        # 2. precision.png
        cls.plot_metric_bar(df, "precision", "Model Precision Comparison", "Precision", output_dir / "precision.png", ascending=False)
        # 3. recall.png
        cls.plot_metric_bar(df, "recall", "Model Recall Comparison", "Recall", output_dir / "recall.png", ascending=False)
        # 4. f1_score.png
        cls.plot_metric_bar(df, "f1_score", "Model F1-Score Comparison", "F1-Score", output_dir / "f1_score.png", ascending=False)
        # 5. roc_auc.png
        cls.plot_metric_bar(df, "roc_auc", "Model ROC-AUC Comparison", "ROC-AUC Score", output_dir / "roc_auc.png", ascending=False)
        # 6. brier_score.png (Lower is better)
        cls.plot_metric_bar(df, "brier_score", "Model Brier Score Comparison (Lower is Better)", "Brier Score", output_dir / "brier_score.png", ascending=True)
        # 7. training_time.png
        cls.plot_metric_bar(df, "training_time_seconds", "Training Time Comparison (Seconds)", "Time (s)", output_dir / "training_time.png", ascending=True)
        # 8. prediction_time.png
        cls.plot_metric_bar(df, "prediction_time_seconds", "Prediction Time Comparison (Seconds)", "Time (s)", output_dir / "prediction_time.png", ascending=True)
        # 9. feature_count.png
        cls.plot_metric_bar(df, "n_features", "Feature Count per Model Configuration", "Number of Features", output_dir / "feature_count.png", ascending=False)

        # 10. ranking.png
        cls._plot_ranking(df, output_dir / "ranking.png")
        # 11. heatmap_metrics.png
        cls._plot_heatmap(df, output_dir / "heatmap_metrics.png")
        # 12. algorithm_comparison.png
        cls._plot_algorithm_comparison(df, output_dir / "algorithm_comparison.png")
        # 13. experiment_comparison.png
        cls._plot_experiment_comparison(df, output_dir / "experiment_comparison.png")

    @classmethod
    def _plot_ranking(cls, df: pd.DataFrame, output_path: Path):
        sorted_df = df.sort_values(by="overall_rank", ascending=True).copy()
        labels = [f"#{row['overall_rank']} {row['algorithm']} ({row['experiment']})" for _, row in sorted_df.iterrows()]
        f1_vals = sorted_df["f1_score"].values

        fig, ax = cls._setup_figure(figsize=(10, max(5, len(labels) * 0.4)))
        y_pos = np.arange(len(labels))
        ax.barh(y_pos, f1_vals, color="#2b5c8f", edgecolor="#111111")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("F1-Score", fontsize=11, weight="bold")
        ax.set_title("Overall Model Ranking (by F1-Score Priority)", fontsize=14, weight="bold", pad=15)
        fig.tight_layout()
        fig.savefig(output_path, dpi=300, facecolor="white")
        plt.close(fig)

    @classmethod
    def _plot_heatmap(cls, df: pd.DataFrame, output_path: Path):
        metrics = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
        metrics_present = [m for m in metrics if m in df.columns]
        if not metrics_present:
            return

        data = df[metrics_present].values
        labels = [f"{row['algorithm']} ({row['experiment']}-{row['approach']})" for _, row in df.iterrows()]

        fig, ax = plt.subplots(figsize=(8, max(6, len(labels) * 0.4)), facecolor="white")
        cax = ax.imshow(data, cmap="YlGnBu", aspect="auto")
        fig.colorbar(cax, ax=ax, orientation="vertical", fraction=0.03, pad=0.04)

        ax.set_xticks(range(len(metrics_present)))
        ax.set_xticklabels([m.replace("_", " ").title() for m in metrics_present], rotation=30, ha="right", weight="bold")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_title("Metrics Heatmap Across Configurations", fontsize=14, weight="bold", pad=15)

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                ax.text(j, i, f"{data[i, j]:.3f}", ha="center", va="center", color="black", fontsize=8)

        fig.tight_layout()
        fig.savefig(output_path, dpi=300, facecolor="white")
        plt.close(fig)

    @classmethod
    def _plot_algorithm_comparison(cls, df: pd.DataFrame, output_path: Path):
        if "algorithm" not in df.columns:
            return
        grouped = df.groupby("algorithm")[["f1_score", "roc_auc", "accuracy"]].mean()
        algorithms = grouped.index.tolist()
        x = np.arange(len(algorithms))
        width = 0.25

        fig, ax = cls._setup_figure(figsize=(8, 5))
        ax.bar(x - width, grouped["f1_score"], width, label="Mean F1-Score", color="#1f77b4", edgecolor="black")
        ax.bar(x, grouped["roc_auc"], width, label="Mean ROC-AUC", color="#ff7f0e", edgecolor="black")
        ax.bar(x + width, grouped["accuracy"], width, label="Mean Accuracy", color="#2ca02c", edgecolor="black")

        ax.set_xticks(x)
        ax.set_xticklabels(algorithms, weight="bold", fontsize=10)
        ax.set_ylabel("Score", weight="bold", fontsize=11)
        ax.set_title("Average Performance by Algorithm", weight="bold", fontsize=14, pad=15)
        ax.legend(frameon=True, facecolor="white")
        fig.tight_layout()
        fig.savefig(output_path, dpi=300, facecolor="white")
        plt.close(fig)

    @classmethod
    def _plot_experiment_comparison(cls, df: pd.DataFrame, output_path: Path):
        if "experiment" not in df.columns:
            return
        grouped = df.groupby("experiment")[["f1_score", "roc_auc", "accuracy"]].mean()
        experiments = grouped.index.tolist()
        x = np.arange(len(experiments))
        width = 0.25

        fig, ax = cls._setup_figure(figsize=(8, 5))
        ax.bar(x - width, grouped["f1_score"], width, label="Mean F1-Score", color="#6a3d9a", edgecolor="black")
        ax.bar(x, grouped["roc_auc"], width, label="Mean ROC-AUC", color="#e31a1c", edgecolor="black")
        ax.bar(x + width, grouped["accuracy"], width, label="Mean Accuracy", color="#33a02c", edgecolor="black")

        ax.set_xticks(x)
        ax.set_xticklabels([f"Exp {e}" for e in experiments], weight="bold", fontsize=10)
        ax.set_ylabel("Score", weight="bold", fontsize=11)
        ax.set_title("Average Performance across Feature Sets (Experiments)", weight="bold", fontsize=14, pad=15)
        ax.legend(frameon=True, facecolor="white")
        fig.tight_layout()
        fig.savefig(output_path, dpi=300, facecolor="white")
        plt.close(fig)
