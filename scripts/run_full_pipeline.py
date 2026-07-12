#!/usr/bin/env python3
"""
run_full_pipeline.py — Production-Aligned Terminal End-to-End Pipeline Runner
Accepts one PDF manuscript and executes all four layers sequentially using
the shared execution pipeline package:

    PDF
      ↓
    Layer 1: Parsing & Deterministic Editorial Rules Engine
      ↓
    Layer 2: Qwen Semantic Evaluation Engine
      ↓
    Layer 3: Frozen Probabilistic Classification & Policy Decision (Layer3Service)
      ↓
    Layer 4: Controlled Explanation Engine (ExplanationGenerator)

Usage:
    python scripts/run_full_pipeline.py --pdf path/to/manuscript.pdf [--mode real|mock] [--persist] [--output path/to/report.json]
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root and packages are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
PACKAGES_DIR = PROJECT_ROOT / "packages"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TerminalPipelineRunner")


def format_box(title: str, content: List[str], width: int = 78) -> str:
    """Formats a clean ASCII summary box for terminal display."""
    lines = [f"+{'-' * (width - 2)}+", f"| {title.ljust(width - 4)} |", f"+{'-' * (width - 2)}+"]
    for line in content:
        while len(line) > width - 4:
            lines.append(f"| {line[:width - 4]} |")
            line = "  " + line[width - 4:]
        lines.append(f"| {line.ljust(width - 4)} |")
    lines.append(f"+{'-' * (width - 2)}+")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute full 4-layer TFG editorial prefilter pipeline on a single PDF manuscript."
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="Absolute or relative path to the PDF manuscript to evaluate."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["real", "mock"],
        default="real",
        help="Execution mode for Layer 2 LLM scoring ('real' connects to Ollama; 'mock' uses deterministic scoring)."
    )
    parser.add_argument(
        "--conference",
        type=str,
        default="iclr_2017",
        help="Target alignment venue string."
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Saves all layer outputs and reports to PostgreSQL database."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save the exact 5-section Layer 4 master JSON report."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed execution breakdowns."
    )
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> Dict[str, Any]:
    t_start = time.perf_counter()
    pdf_path = Path(args.pdf).resolve()

    if not pdf_path.exists() or not pdf_path.is_file():
        logger.error("Input PDF file does not exist or is invalid: %s", pdf_path)
        sys.exit(1)

    stem_id = pdf_path.stem
    manuscript_id = stem_id

    # If persistence is requested, generate an auto-incremented database manuscript ID
    if args.persist:
        try:
            from pipeline.persistence import create_initial_manuscript
            manuscript_id = str(create_initial_manuscript(pdf_path.name, stem_id))
            logger.info("Persisting run: initial manuscript record created with ID '%s'", manuscript_id)
        except Exception as db_init_err:
            logger.error("Failed to initialize manuscript in DB: %s", db_init_err)
            sys.exit(1)

    # Invoke the shared PipelineOrchestrator
    from pipeline.orchestrator import PipelineOrchestrator
    try:
        result = PipelineOrchestrator.run(
            pdf_path=str(pdf_path),
            conference=args.conference,
            mode=args.mode,
            persist=args.persist,
            manuscript_id=manuscript_id
        )
    except Exception as run_err:
        logger.error("Pipeline run failed: %s", run_err)
        sys.exit(1)

    report_dict = result.to_master_report_dict()
    l3_prediction = result.layer3_prediction
    hard_flags = result.layer1_violations
    qwen_scores = result.layer2_scores
    title = result.title

    # Optional JSON output save
    if args.output:
        try:
            out_path = Path(args.output).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(report_dict, fh, indent=4, ensure_ascii=False)
            logger.info("Saved master JSON report snapshot to: %s", out_path)
        except Exception as exc:
            logger.error("Could not save JSON report snapshot: %s", exc)
            sys.exit(1)

    # Print clean terminal formatting summary
    total_time = time.perf_counter() - t_start
    display_title = title
    if str(title).lower().strip() in ("removed", "unknown", "none", ""):
        display_title = "Unavailable / anonymized"

    summary_lines = [
        f"Manuscript ID      : {manuscript_id}",
        f"Title              : {display_title}",
        f"Venue              : {args.conference}",
        f"Evaluation Mode    : {args.mode.upper()}",
        f"Total Runtime      : {total_time:.2f} seconds",
        "",
        "LAYER 1 -- DETERMINISTIC EDITORIAL CHECKS",
        f"  Total Violations  : {len(hard_flags)}",
        f"  Critical Failures : {sum(1 for v in hard_flags if getattr(v, 'severity', '') == 'critical')}",
        "",
        "LAYER 2 -- QWEN SEMANTIC EVALUATION",
        f"  Overall Quality   : {qwen_scores.get('overall_quality', 0.0):.4f}",
        f"  Structural Comp.  : {qwen_scores.get('structural_completeness', 0.0):.4f}",
        f"  Methodological    : {qwen_scores.get('methodological_strength', 0.0):.4f}",
        "",
        "LAYER 3 -- PROBABILISTIC CLASSIFICATION & POLICY",
        f"  Decision          : {l3_prediction.decision.upper()}",
        f"  P(Accept)         : {l3_prediction.accept_probability:.4f}",
        f"  P(Desk Reject)    : {l3_prediction.desk_reject_probability:.4f}",
        f"  Confidence        : {l3_prediction.confidence_level}",
        ""
    ]

    # Layer 4 TreeSHAP verification display
    shap_meta = report_dict.get("feature_importance", {}).get("shap_metadata", {})
    summary_lines.extend([
        "LAYER 4 -- TREE SHAP VERIFICATION",
        f"  Explained Output  : P(Accept)",
        f"  Base Value        : {shap_meta.get('base_value', 0.0):.4f}",
        f"  Attribution Sum   : {shap_meta.get('attribution_sum', 0.0):.4f}",
        f"  Reconstructed     : {shap_meta.get('reconstructed_output', 0.0):.4f}",
        f"  Additivity Error  : {shap_meta.get('additivity_error', 0.0):.8f}",
        f"  Status            : {shap_meta.get('additivity_status', 'PASS')}",
        ""
    ])

    summary_lines.append("TOP LOCAL MODEL CONTRIBUTIONS")
    ranked_features = report_dict.get("feature_importance", {}).get("ranked_features", [])
    for i, rf in enumerate(ranked_features[:3], 1):
        rf_name = rf.get("name", "")
        rf_val = rf.get("shap_value", 0.0)
        rf_dir = rf.get("direction", "")
        feat_raw_val = l3_prediction.feature_vector.get(rf_name, 0.0)
        summary_lines.extend([
            f"  {i}. {rf_name}",
            f"     value: {feat_raw_val:.4f}",
            f"     SHAP : {rf_val:+.4f}",
            f"     direction: {rf_dir}"
        ])

    summary_lines.extend([
        "",
        "ASSISTED RECOMMENDATION",
    ])

    narrative_str = report_dict.get("natural_language_explanation", {}).get("text", "")
    for para in narrative_str.split("\n\n"):
        para_lines = para.strip().split("\n")
        for pl in para_lines:
            if pl.strip():
                summary_lines.append(f"  {pl.strip()}")

    print("\n" + format_box(f"TFG PIPELINE EVALUATION SUMMARY [{manuscript_id}]", summary_lines) + "\n")
    return report_dict


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args)
