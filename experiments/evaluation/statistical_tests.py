"""
statistical_tests.py — Statistical Significance Tests for Chapter 5 TFG.

Provides non-parametric statistical tests to validate that performance
differences between classifiers/feature sets are statistically significant:

  - Wilcoxon signed-rank test  : pairwise comparison of two classifiers
  - Friedman test              : multi-classifier comparison across datasets
  - Nemenyi post-hoc test      : pairwise ranking differences after Friedman
  - Confidence intervals       : bootstrap 95% CI for ROC AUC and F1

All tests operate on the per-run ROC AUC scores retrieved from MLflow.
Results are printed and saved to experiments/reports/outputs/.

Dependencies:
  scipy  (Wilcoxon, Friedman)
  scikit-posthocs  (Nemenyi) — optional, install via: pip install scikit-posthocs
"""

import sys
import argparse
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import mlflow
from mlflow.tracking import MlflowClient
from scipy import stats

from experiments.models.common.constants import EXPERIMENT_TYPE_GRID_SEARCH
from experiments.models.common.utils import print_section

DEFAULT_MLFLOW_DB = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
DEFAULT_OUTPUT    = PROJECT_ROOT / "experiments" / "reports" / "outputs"

try:
    import scikit_posthocs as sp
    HAS_POSTHOCS = True
except ImportError:
    HAS_POSTHOCS = False


# Data loading

def load_runs(tracking_uri: str = None) -> pd.DataFrame:
    """Loads all FINISHED grid-search runs from MLflow."""
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
                "run_id":      run.info.run_id,
                "classifier":  tags.get("classifier", "Unknown"),
                "dataset":     tags.get("dataset", "Unknown"),
                "feature_set": tags.get("feature_set", "Unknown"),
                "roc_auc":     metrics.get("roc_auc", np.nan),
                "f1":          metrics.get("f1", np.nan),
                "ece":         metrics.get("ece", np.nan),
            })
    return pd.DataFrame(rows).dropna(subset=["roc_auc"])


# Confidence intervals (bootstrap)

def bootstrap_ci(
    scores: np.ndarray,
    n_bootstrap: int = 10_000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """
    Computes a bootstrap confidence interval for the mean of *scores*.

    Returns
    -------
    (lower, upper) : float pair
    """
    rng = np.random.default_rng(seed)
    boot_means = [
        rng.choice(scores, size=len(scores), replace=True).mean()
        for _ in range(n_bootstrap)
    ]
    alpha = (1 - ci) / 2
    return float(np.quantile(boot_means, alpha)), float(np.quantile(boot_means, 1 - alpha))


# Wilcoxon signed-rank test

def wilcoxon_test(
    df: pd.DataFrame,
    clf_a: str,
    clf_b: str,
    metric: str = "roc_auc",
) -> Dict:
    """
    Pairwise Wilcoxon signed-rank test between two classifiers.

    Pairs are matched by (dataset, feature_set) so that the test compares
    apples to apples — same experimental conditions.

    Returns a dict with: statistic, p_value, significant (α=0.05), direction.
    """
    a = df[df["classifier"] == clf_a].set_index(["dataset", "feature_set"])[metric]
    b = df[df["classifier"] == clf_b].set_index(["dataset", "feature_set"])[metric]
    common_idx = a.index.intersection(b.index)

    if len(common_idx) < 3:
        return {
            "clf_a": clf_a, "clf_b": clf_b,
            "n_pairs": len(common_idx),
            "statistic": np.nan, "p_value": np.nan,
            "significant": None, "direction": "insufficient data",
        }

    a_vals = a.loc[common_idx].values
    b_vals = b.loc[common_idx].values

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stat, p = stats.wilcoxon(a_vals, b_vals, alternative="two-sided")

    direction = f"{clf_a} > {clf_b}" if a_vals.mean() > b_vals.mean() else f"{clf_b} > {clf_a}"
    return {
        "clf_a": clf_a, "clf_b": clf_b,
        "n_pairs": len(common_idx),
        "mean_a": float(a_vals.mean()), "mean_b": float(b_vals.mean()),
        "statistic": float(stat), "p_value": float(p),
        "significant": p < 0.05, "direction": direction,
    }


# Friedman test

def friedman_test(df: pd.DataFrame, metric: str = "roc_auc") -> Dict:
    """
    Friedman test across all classifiers.  Groups by (dataset, feature_set),
    checks whether the ROC AUC distributions differ significantly.

    Returns: statistic, p_value, significant.
    """
    pivot = df.pivot_table(index=["dataset", "feature_set"], columns="classifier", values=metric)
    pivot = pivot.dropna()

    if pivot.shape[0] < 3 or pivot.shape[1] < 2:
        return {"statistic": np.nan, "p_value": np.nan, "significant": None,
                "n_blocks": pivot.shape[0], "n_classifiers": pivot.shape[1]}

    stat, p = stats.friedmanchisquare(*[pivot[col].values for col in pivot.columns])
    return {
        "statistic": float(stat), "p_value": float(p),
        "significant": p < 0.05,
        "n_blocks": pivot.shape[0], "n_classifiers": pivot.shape[1],
    }


# Nemenyi post-hoc test

def nemenyi_test(df: pd.DataFrame, metric: str = "roc_auc") -> Optional[pd.DataFrame]:
    """
    Nemenyi post-hoc test (requires scikit-posthocs).
    Returns a p-value matrix DataFrame, or None if unavailable.
    """
    if not HAS_POSTHOCS:
        print("[!] scikit-posthocs not installed. Skipping Nemenyi test.")
        print("    Install via: pip install scikit-posthocs")
        return None

    pivot = df.pivot_table(index=["dataset", "feature_set"], columns="classifier", values=metric)
    pivot = pivot.dropna()
    if pivot.shape[0] < 3:
        print("[!] Not enough matched pairs for Nemenyi test.")
        return None

    return sp.posthoc_nemenyi_friedman(pivot.values)


# Main runner

def run_all_tests(tracking_uri: str = None, output_dir: Path = None) -> None:
    print_section("STATISTICAL SIGNIFICANCE TESTS (Chapter 5)")
    df = load_runs(tracking_uri)

    if df.empty:
        print("[!] No completed runs found.")
        return

    out = Path(output_dir or DEFAULT_OUTPUT)
    out.mkdir(parents=True, exist_ok=True)

    classifiers = df["classifier"].dropna().unique().tolist()

    # 1. Bootstrap CIs per classifier
    print("\n--- Bootstrap 95% Confidence Intervals (ROC AUC) ---")
    ci_rows = []
    for clf in classifiers:
        scores = df[df["classifier"] == clf]["roc_auc"].values
        lo, hi = bootstrap_ci(scores)
        mean   = scores.mean()
        ci_rows.append({"classifier": clf, "n": len(scores),
                        "mean_roc_auc": mean, "ci_lower": lo, "ci_upper": hi})
        print(f"  {clf:<30}: {mean:.4f} [{lo:.4f}, {hi:.4f}]")
    ci_df = pd.DataFrame(ci_rows)
    ci_df.to_csv(out / "ci_roc_auc.csv", index=False)

    # 2. Wilcoxon pairwise
    print("\n--- Wilcoxon Signed-Rank Tests ---")
    wilcoxon_rows = []
    for i, clf_a in enumerate(classifiers):
        for clf_b in classifiers[i+1:]:
            result = wilcoxon_test(df, clf_a, clf_b)
            sig_str = "YES *" if result.get("significant") else "no"
            print(f"  {result['clf_a']} vs {result['clf_b']}: "
                  f"p={result['p_value']:.4f}  significant={sig_str}  ({result['direction']})")
            wilcoxon_rows.append(result)
    pd.DataFrame(wilcoxon_rows).to_csv(out / "wilcoxon_results.csv", index=False)

    # 3. Friedman test
    print("\n--- Friedman Test (all classifiers) ---")
    friedman = friedman_test(df)
    print(f"  chi2={friedman['statistic']:.4f}  p={friedman['p_value']:.4f}  "
          f"significant={'YES *' if friedman.get('significant') else 'no'}")

    # 4. Nemenyi (optional)
    nemenyi = nemenyi_test(df)
    if nemenyi is not None:
        print("\n--- Nemenyi Post-Hoc p-value Matrix ---")
        print(nemenyi.to_string(float_format="{:.4f}".format))
        nemenyi.to_csv(out / "nemenyi_pvalues.csv")

    print(f"\n[+] All statistical test results saved to: {out}")


def main():
    parser = argparse.ArgumentParser(
        description="Run statistical significance tests on Chapter 5 experiment results."
    )
    parser.add_argument("--tracking-uri", type=str, default=None)
    parser.add_argument("--output-dir",   type=str, default=None)
    args = parser.parse_args()
    run_all_tests(args.tracking_uri, args.output_dir)


if __name__ == "__main__":
    main()
