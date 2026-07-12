"""
Main entry point for Layer 3 Model Comparison Pipeline.
Orchestrates experiment discovery, table generation, chart creation, best model selection, and PDF reporting.
"""

import os
import sys
from pathlib import Path

# Add parent directory to sys.path if executed directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from config import EXPERIMENTS_MODELS_DIR, REPORTS_COMPARISON_DIR
from utils import ModelComparatorUtils
from plots import ModelComparatorPlots
from report_generator import ModelComparisonReportGenerator


def main():
    print("Loading experiments...")
    base_dir = Path(EXPERIMENTS_MODELS_DIR)
    output_dir = Path(REPORTS_COMPARISON_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading metrics...")
    df = ModelComparatorUtils.load_all_experiments(base_dir)

    if df.empty:
        print("[WARNING] No experiments discovered. Terminating comparison pipeline.")
        return

    print("Building comparison table...")
    df_ranked = ModelComparatorUtils.rank_models(df)
    summary = ModelComparatorUtils.generate_summary_stats(df_ranked)

    print("Selecting best model...")
    best_model = ModelComparatorUtils.select_best_model(df_ranked, output_dir)

    print("Saving outputs...")
    ModelComparatorUtils.export_tables(df_ranked, output_dir)

    print("Generating charts...")
    charts_dir = output_dir / "plots"
    ModelComparatorPlots.generate_all_plots(df_ranked, charts_dir)

    print("Generating PDF...")
    pdf_path = output_dir / "model_comparison.pdf"
    pdf_gen = ModelComparisonReportGenerator(pdf_path)
    try:
        pdf_gen.generate_pdf(df_ranked, best_model, summary, charts_dir)
    except Exception as e:
        print(f"[WARNING] Could not generate PDF report: {e}")

    print("Completed successfully.")


if __name__ == "__main__":
    main()
