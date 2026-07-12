"""
train.py — Offline Retraining & Candidate Evaluation Pipeline
Executable script (`python -m packages.calibration.offline.train`) for offline development or retraining.

Runs dataset loading, two-stage model & calibration selection, evaluation against target benchmarks,
and exports candidate model bundles to an isolated candidate folder (`artifacts/candidates/<timestamp>/`).

IMPORTANT: This script NEVER overwrites production models (`packages/calibration/models/`) and
NEVER modifies finalized evaluation study results (`experiments/evaluation_models/`).
To promote a verified candidate into production, explicitly run `python -m packages.calibration.offline.promote_model`.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .dataset import load_dataset_splits
from .model_selection import select_best_model
from .evaluator import evaluate_model, verify_against_winner_benchmarks
from .exporter import export_model_bundle
from ..common.constants import PACKAGE_ROOT


def main(args: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Layer 3 Offline Retraining & Candidate Evaluation")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction of dataset reserved for test split")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=str, default=None, help="Optional custom candidate output directory")
    parser.add_argument("--require-pass", action="store_true", help="Exit with code 1 if candidate fails verification benchmarks")

    parsed = parser.parse_args(args)

    print(f"[{datetime.now().isoformat()}] Starting Layer 3 Offline Candidate Training (Seed: {parsed.seed})...")

    # 1. Load data
    try:
        X_train, X_test, y_train, y_test = load_dataset_splits(test_size=parsed.test_size, random_seed=parsed.seed)
        print(f"  Loaded dataset: {len(X_train)} train rows, {len(X_test)} test rows.")
    except Exception as e:
        print(f"[ERROR] Could not load dataset splits: {e}", file=sys.stderr)
        return 1

    # 2. Split train into train and validation for two-stage selection
    from sklearn.model_selection import train_test_split
    strat = y_train if len(y_train.value_counts()) >= 2 else None
    X_tr, X_val, y_tr, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=parsed.seed, stratify=strat)

    # 3. Two-stage model & calibration selection
    print("  Executing two-stage model and calibration selection...")
    selection = select_best_model(X_tr, y_tr, X_val, y_val, random_seed=parsed.seed)
    winner_name = selection["winning_classifier"]
    winner_cal = selection["winning_calibration"]
    winner_model = selection["winning_model"]

    print(f"  Selected Candidate: {winner_name} (Calibration: {winner_cal})")

    # 4. Final test evaluation
    print("  Evaluating candidate on isolated test fold...")
    test_metrics = evaluate_model(winner_model, X_test, y_test)
    print(f"    ROC AUC: {test_metrics['roc_auc']:.4f}")
    print(f"    MCC:     {test_metrics['mcc']:.4f}")
    print(f"    F1:      {test_metrics['f1']:.4f}")
    print(f"    ECE:     {test_metrics['ece']:.4f}")

    # 5. Verify against benchmarks
    passed, reasons = verify_against_winner_benchmarks(test_metrics)
    if passed:
        print("  [SUCCESS] Candidate model passed all performance verification benchmarks.")
    else:
        print("  [WARNING] Candidate model did not meet target benchmarks:")
        for r in reasons:
            print(f"    - {r}")
        if parsed.require_pass:
            return 2

    # 6. Export candidate bundle
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(parsed.output_dir) if parsed.output_dir else (PACKAGE_ROOT / "artifacts" / "candidates" / f"candidate_{ts_str}")
    
    files = export_model_bundle(
        model=winner_model,
        metrics=test_metrics,
        output_dir=out_path,
        classifier_name=winner_name,
        calibration_method=winner_cal,
        model_version=f"{winner_name}-{ts_str}"
    )

    print(f"\n[{datetime.now().isoformat()}] Candidate bundle successfully exported to: {out_path}")
    print("  Files created:")
    for k, p in files.items():
        print(f"    - {k}: {p}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
