"""
generate_figures.py — Publication-Quality Figures for Chapter 5 TFG.

Generates all figures required for Chapter 5 of the thesis from MLflow
experiment data. All figures are saved as high-resolution PNG (300 DPI)
and PDF (for LaTeX inclusion) in experiments/reports/outputs/figures/.

Figures produced:
  01_classifier_roc_comparison.png    — ROC AUC bar chart: LR vs RF vs XGB
  02_feature_set_ablation.png         — Ablation bar chart: Exp A vs B vs C vs D
  03_calibration_comparison.png       — ECE bar chart by calibration strategy
  04_dataset_comparison.png           — Performance across 4 dataset variants
  05_confusion_matrices.png           — Confusion matrix grid (best run per clf)
  06_learning_curves.png              — Metric profiles across tiers (radar/line)
  07_llm_comparison.png               — ROC AUC per LLM/dataset variant
"""

import sys
import warnings
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

import mlflow
from mlflow.tracking import MlflowClient

from experiments.models.common.constants import EXPERIMENT_TYPE_GRID_SEARCH
from experiments.models.common.utils import print_section, ensure_dir

DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
DEFAULT_FIGURES   = PROJECT_ROOT / "experiments" / "reports" / "outputs" / "figures"

PALETTE     = "Set2"
DPI         = 300
FIG_WIDTH   = 10
FIG_HEIGHT  = 6
FONT_FAMILY = "DejaVu Sans"
plt.rcParams.update({
    "font.family":       FONT_FAMILY,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.3,
})


# Data loading

def load_runs(tracking_uri: str = None) -> pd.DataFrame:
    uri = tracking_uri or DEFAULT_MLFLOW_DB
    mlflow.set_tracking_uri(uri)
    client = MlflowClient(tracking_uri=uri)
    rows = []
    for exp in client.search_experiments():
        for run in client.search_runs(experiment_ids=[exp.experiment_id]):
            if run.info.status != "FINISHED":
                continue
            tags    = run.data.tags
            metrics = run.data.metrics
            if tags.get("experiment_type") != EXPERIMENT_TYPE_GRID_SEARCH:
                continue
            rows.append({
                "run_id":             run.info.run_id,
                "classifier":         tags.get("classifier", "Unknown"),
                "dataset":            tags.get("dataset", "Unknown"),
                "feature_set":        tags.get("feature_set", "Unknown"),
                "calibration_method": tags.get("calibration_method", "none"),
                "llm_label":          tags.get("llm_model_name", tags.get("dataset", "Unknown")),
                "roc_auc":            metrics.get("roc_auc", np.nan),
                "f1":                 metrics.get("f1", np.nan),
                "accuracy":           metrics.get("accuracy", np.nan),
                "precision":          metrics.get("precision", np.nan),
                "recall":             metrics.get("recall", np.nan),
                "ece":                metrics.get("ece", np.nan),
                "brier_score":        metrics.get("brier_score", np.nan),
            })
    return pd.DataFrame(rows).dropna(subset=["roc_auc"])


def _save(fig: plt.Figure, figures_dir: Path, stem: str) -> None:
    """Saves a figure as PNG and PDF."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / f"{stem}.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(figures_dir / f"{stem}.pdf",           bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved: {stem}.png / .pdf")


# Figure generators

def fig_classifier_roc(df: pd.DataFrame, figures_dir: Path) -> None:
    """Bar chart: mean ROC AUC per classifier with ±1 std error bars."""
    stats = (
        df.groupby("classifier")["roc_auc"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    stats["se"] = stats["std"] / np.sqrt(stats["count"])

    fig, ax = plt.subplots(figsize=(FIG_WIDTH * 0.6, FIG_HEIGHT * 0.7))
    colors = sns.color_palette(PALETTE, n_colors=len(stats))
    bars = ax.bar(stats["classifier"], stats["mean"], color=colors,
                  yerr=stats["se"], capsize=5, error_kw={"linewidth": 1.5})
    ax.set_ylim(max(0, stats["mean"].min() - 0.1), min(1.0, stats["mean"].max() + 0.1))
    ax.set_ylabel("Mean ROC AUC", fontsize=12)
    ax.set_title("Classifier Comparison — ROC AUC\n(All Datasets & Feature Sets)", fontweight="bold")
    for bar, val in zip(bars, stats["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=10)
    _save(fig, figures_dir, "01_classifier_roc_comparison")


def fig_feature_set_ablation(df: pd.DataFrame, figures_dir: Path) -> None:
    """Grouped bar chart: mean ROC AUC by feature set, coloured by classifier."""
    TIER_ORDER = ["Exp_A", "Exp_B", "Exp_C", "Exp_D"]
    pivot = (
        df.groupby(["feature_set", "classifier"])["roc_auc"]
        .mean()
        .reset_index()
    )
    available_tiers = [t for t in TIER_ORDER if t in pivot["feature_set"].values]

    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT * 0.8))
    classifiers = pivot["classifier"].unique().tolist()
    x      = np.arange(len(available_tiers))
    width  = 0.8 / max(len(classifiers), 1)
    colors = sns.color_palette(PALETTE, n_colors=len(classifiers))

    for i, (clf, color) in enumerate(zip(classifiers, colors)):
        vals = [pivot[(pivot["feature_set"] == t) & (pivot["classifier"] == clf)]["roc_auc"].values
                for t in available_tiers]
        heights = [v[0] if len(v) > 0 else np.nan for v in vals]
        ax.bar(x + i * width, heights, width, label=clf, color=color)

    ax.set_xticks(x + width * (len(classifiers) - 1) / 2)
    ax.set_xticklabels(available_tiers)
    ax.set_ylabel("Mean ROC AUC", fontsize=12)
    ax.set_title("Feature Set Ablation Study\n(Exp A: Structural | B: LLM Scores | C: Hybrid | D: Full)",
                 fontweight="bold")
    ax.legend(title="Classifier", bbox_to_anchor=(1.01, 1), loc="upper left")
    _save(fig, figures_dir, "02_feature_set_ablation")


def fig_calibration_comparison(df: pd.DataFrame, figures_dir: Path) -> None:
    """Box plot: ECE distribution by calibration strategy."""
    if "calibration_method" not in df.columns or df["calibration_method"].isna().all():
        print("[SKIP] No calibration_method column in data.")
        return

    fig, ax = plt.subplots(figsize=(FIG_WIDTH * 0.7, FIG_HEIGHT * 0.7))
    order = sorted(df["calibration_method"].dropna().unique())
    sns.boxplot(data=df, x="calibration_method", y="ece", order=order,
                palette=PALETTE, ax=ax, width=0.5)
    ax.set_ylabel("Expected Calibration Error (ECE)", fontsize=12)
    ax.set_xlabel("Calibration Strategy", fontsize=12)
    ax.set_title("Calibration Strategy Comparison — ECE Distribution", fontweight="bold")
    _save(fig, figures_dir, "03_calibration_comparison")


def fig_dataset_comparison(df: pd.DataFrame, figures_dir: Path) -> None:
    """Bar chart: mean ROC AUC across 4 dataset variants."""
    stats = (
        df.groupby("dataset")["roc_auc"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    stats["se"] = stats["std"] / np.sqrt(stats["count"])

    fig, ax = plt.subplots(figsize=(FIG_WIDTH * 0.6, FIG_HEIGHT * 0.7))
    colors = sns.color_palette(PALETTE, n_colors=len(stats))
    bars = ax.bar(stats["dataset"], stats["mean"], color=colors,
                  yerr=stats["se"], capsize=5)
    ax.set_ylabel("Mean ROC AUC", fontsize=12)
    ax.set_title("Dataset Variant Comparison — ROC AUC", fontweight="bold")
    for bar, val in zip(bars, stats["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=10)
    _save(fig, figures_dir, "04_dataset_comparison")


def fig_llm_comparison(df: pd.DataFrame, figures_dir: Path) -> None:
    """Bar chart: ROC AUC by LLM/dataset variant."""
    stats = (
        df.groupby("dataset")["roc_auc"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    stats["se"] = stats["std"] / np.sqrt(stats["count"])

    LABELS = {
        "dataset":  "Qwen3 4B\n(default)",
        "v1":       "Qwen3 4B\n(v1 prompts)",
        "freetext": "Qwen3 4B\n(free-text)",
        "qwen_35b": "Qwen3 35B",
    }
    stats["label"] = stats["dataset"].map(lambda d: LABELS.get(d, d))

    fig, ax = plt.subplots(figsize=(FIG_WIDTH * 0.7, FIG_HEIGHT * 0.8))
    colors = sns.color_palette(PALETTE, n_colors=len(stats))
    bars = ax.bar(stats["label"], stats["mean"], color=colors,
                  yerr=stats["se"], capsize=5)
    ax.set_ylabel("Mean ROC AUC", fontsize=12)
    ax.set_title("LLM Scorer Comparison — Impact on Classifier ROC AUC", fontweight="bold")
    for bar, val in zip(bars, stats["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=10)
    _save(fig, figures_dir, "07_llm_comparison")


def fig_metric_profiles(df: pd.DataFrame, figures_dir: Path) -> None:
    """Line plot: multiple metrics across feature set tiers for each classifier."""
    TIER_ORDER = ["Exp_A", "Exp_B", "Exp_C", "Exp_D"]
    metrics    = ["roc_auc", "f1", "accuracy", "precision", "recall"]
    classifiers = df["classifier"].unique().tolist()

    fig, axes = plt.subplots(1, len(classifiers), figsize=(FIG_WIDTH * 1.4, FIG_HEIGHT * 0.9),
                              sharey=True)
    if len(classifiers) == 1:
        axes = [axes]

    for ax, clf in zip(axes, classifiers):
        sub = df[df["classifier"] == clf]
        colors = sns.color_palette(PALETTE, n_colors=len(metrics))
        for metric, color in zip(metrics, colors):
            vals = [
                sub[sub["feature_set"] == tier][metric].mean()
                for tier in TIER_ORDER
                if tier in sub["feature_set"].values
            ]
            tiers_available = [t for t in TIER_ORDER if t in sub["feature_set"].values]
            if vals:
                ax.plot(tiers_available, vals, marker="o", label=metric, color=color)
        ax.set_title(clf, fontsize=10, fontweight="bold")
        ax.set_ylabel("Score" if ax == axes[0] else "")
        ax.set_ylim(0, 1)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(metrics), bbox_to_anchor=(0.5, -0.08))
    fig.suptitle("Metric Profiles Across Feature Set Tiers", fontweight="bold", fontsize=13)
    _save(fig, figures_dir, "06_metric_profiles")


# Main

def generate_all_figures(tracking_uri: str = None, figures_dir: Path = None) -> None:
    print_section("GENERATING CHAPTER 5 PUBLICATION FIGURES")
    df = load_runs(tracking_uri)

    if df.empty:
        print("[!] No completed grid-search runs found. Cannot generate figures.")
        return

    figs_dir = Path(figures_dir or DEFAULT_FIGURES)
    ensure_dir(figs_dir)
    print(f"[+] Output directory: {figs_dir}")
    print(f"[+] Loaded {len(df)} runs\n")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fig_classifier_roc(df, figs_dir)
        fig_feature_set_ablation(df, figs_dir)
        fig_calibration_comparison(df, figs_dir)
        fig_dataset_comparison(df, figs_dir)
        fig_llm_comparison(df, figs_dir)
        fig_metric_profiles(df, figs_dir)

    print(f"\n[+] All figures saved to: {figs_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate publication-quality figures for Chapter 5 TFG."
    )
    parser.add_argument("--tracking-uri",  type=str, default=None)
    parser.add_argument("--figures-dir",   type=str, default=None,
                        help="Output directory for figures (default: reports/outputs/figures/)")
    args = parser.parse_args()
    generate_all_figures(args.tracking_uri, args.figures_dir)


if __name__ == "__main__":
    main()
