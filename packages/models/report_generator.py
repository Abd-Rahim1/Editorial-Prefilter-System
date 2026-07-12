"""
PDF Report Generator using ReportLab for complete Layer 3 model comparison documentation.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

logger = logging.getLogger("ReportGenerator")

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class ModelComparisonReportGenerator:
    """Generates professional publication-quality PDF report summarizing ML model comparison."""

    def __init__(self, output_pdf_path: Path):
        self.output_pdf_path = output_pdf_path
        if HAS_REPORTLAB:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()
        else:
            self.styles = None

    def _setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            "CoverTitle",
            parent=self.styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=32,
            textColor=colors.HexColor("#1A365D"),
            alignment=1,
            spaceAfter=20,
        )
        self.subtitle_style = ParagraphStyle(
            "CoverSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=40,
        )
        self.h1_style = ParagraphStyle(
            "Heading1Custom",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1A365D"),
            spaceBefore=15,
            spaceAfter=10,
        )
        self.h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=12,
            spaceAfter=8,
        )
        self.body_style = ParagraphStyle(
            "BodyCustom",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=10,
        )

    def generate_pdf(self, df: pd.DataFrame, best_model: Dict[str, Any], summary: Dict[str, Any], charts_dir: Path) -> None:
        """
        Build and write the full PDF report to disk.
        """
        logger.info("Generating PDF comparison report...")
        if not HAS_REPORTLAB:
            logger.warning("reportlab module is not installed. Skipping PDF generation.")
            return
        self.output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(self.output_pdf_path),
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        story = []

        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph("Layer 3 Machine Learning Comparison Report", self.title_style))
        story.append(Paragraph("Automated Evaluation & Best Model Selection for Scientific Paper Prefiltering", self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1A365D"), spaceAfter=30))

        cover_info = [
            [Paragraph("<b>Generation Date:</b>", self.body_style), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.body_style)],
            [Paragraph("<b>Total Models Evaluated:</b>", self.body_style), Paragraph(str(summary.get("total_models", 0)), self.body_style)],
            [Paragraph("<b>Algorithms Evaluated:</b>", self.body_style), Paragraph(", ".join(summary.get("algorithms_evaluated", [])), self.body_style)],
            [Paragraph("<b>Feature Sets / Experiments:</b>", self.body_style), Paragraph(", ".join(summary.get("experiments_evaluated", [])), self.body_style)],
        ]
        t_cover = Table(cover_info, colWidths=[2.2 * inch, 4.3 * inch])
        t_cover.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t_cover)
        story.append(PageBreak())

        story.append(Paragraph("Executive Summary", self.h1_style))
        summary_text = (
            f"This comprehensive comparison report evaluates <b>{summary.get('total_models', 0)}</b> distinct machine learning models trained "
            f"across multiple algorithms (<b>{', '.join(summary.get('algorithms_evaluated', []))}</b>) and feature set configurations. "
            f"The primary goal of Layer 3 is to calibrate probability recommendations before forwarding candidates to Layer 4 (Explainable AI).<br/><br/>"
            f"Across all experiments, models achieved a mean F1-score of <b>{summary.get('mean_f1', 0.0):.4f}</b>, a mean ROC-AUC of <b>{summary.get('mean_roc_auc', 0.0):.4f}</b>, "
            f"and a mean Brier reliability score of <b>{summary.get('mean_brier_score', 0.0):.4f}</b>. "
            f"The top performing algorithm identified is <b>{summary.get('best_algorithm', 'N/A')}</b> utilizing feature set <b>Experiment {summary.get('best_experiment', 'N/A')}</b>."
        )
        story.append(Paragraph(summary_text, self.body_style))
        story.append(Spacer(1, 15))

        story.append(Paragraph("Experimental Setup", self.h1_style))
        setup_text = (
            "<b>• Algorithms Evaluated:</b> Logistic Regression, Random Forest, and XGBoost.<br/>"
            "<b>• Probability Calibration:</b> Scikit-Learn CalibratedClassifierCV using Platt Scaling (sigmoid method) with 5-fold Cross-Validation.<br/>"
            "<b>• Train/Test Split:</b> Standardized 80/20 stratified split with fixed random state 42.<br/>"
            "<b>• Feature Preprocessing:</b> StandardScaler applied to numeric features across Experiments A, B, C, and D.<br/>"
            "<b>• Evaluation Metrics:</b> Accuracy, Precision, Recall, F1-score, ROC-AUC, Brier Score Loss, and runtime latency."
        )
        story.append(Paragraph(setup_text, self.body_style))
        story.append(Spacer(1, 15))

        story.append(Paragraph("Complete Model Comparison Table", self.h1_style))
        table_data = [["Rank", "Algorithm", "Exp", "Mode", "F1", "ROC-AUC", "Acc", "Brier"]]
        for _, row in df.iterrows():
            table_data.append([
                str(row.get("overall_rank", "")),
                str(row.get("algorithm", ""))[:14],
                str(row.get("experiment", "")),
                str(row.get("approach", ""))[:12],
                f"{row.get('f1_score', 0.0):.3f}",
                f"{row.get('roc_auc', 0.0):.3f}",
                f"{row.get('accuracy', 0.0):.3f}",
                f"{row.get('brier_score', 0.0):.3f}",
            ])
        t_comp = Table(table_data, colWidths=[0.5*inch, 1.5*inch, 0.6*inch, 1.3*inch, 0.7*inch, 0.7*inch, 0.6*inch, 0.6*inch])
        t_comp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ]))
        story.append(t_comp)
        story.append(PageBreak())

        story.append(Paragraph("Top 10 Ranked Models", self.h1_style))
        top10_data = [["Rank", "Algorithm", "Exp", "Approach", "F1", "ROC-AUC", "Brier"]]
        for _, row in df.head(10).iterrows():
            top10_data.append([
                f"#{row.get('overall_rank', '')}",
                str(row.get("algorithm", "")),
                str(row.get("experiment", "")),
                str(row.get("approach", "")),
                f"{row.get('f1_score', 0.0):.4f}",
                f"{row.get('roc_auc', 0.0):.4f}",
                f"{row.get('brier_score', 0.0):.4f}",
            ])
        t_top10 = Table(top10_data, colWidths=[0.6*inch, 1.8*inch, 0.6*inch, 1.5*inch, 0.7*inch, 0.7*inch, 0.6*inch])
        t_top10.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EDF2F7")]),
        ]))
        story.append(t_top10)
        story.append(Spacer(1, 20))

        story.append(Paragraph("Best Model Selection & Layer 4 Recommendation", self.h1_style))
        best_metrics = best_model.get("metrics", {})
        best_cfg = best_model.get("configuration", {})
        best_info = [
            [Paragraph("<b>Algorithm:</b>", self.body_style), Paragraph(str(best_model.get("algorithm")), self.body_style)],
            [Paragraph("<b>Experiment / Feature Set:</b>", self.body_style), Paragraph(f"Experiment {best_model.get('experiment')}", self.body_style)],
            [Paragraph("<b>Configuration Approach:</b>", self.body_style), Paragraph(str(best_cfg.get("approach", "baseline")), self.body_style)],
            [Paragraph("<b>F1-Score:</b>", self.body_style), Paragraph(f"{best_metrics.get('f1_score', 0.0):.4f}", self.body_style)],
            [Paragraph("<b>ROC-AUC Score:</b>", self.body_style), Paragraph(f"{best_metrics.get('roc_auc', 0.0):.4f}", self.body_style)],
            [Paragraph("<b>Accuracy:</b>", self.body_style), Paragraph(f"{best_metrics.get('accuracy', 0.0):.4f}", self.body_style)],
            [Paragraph("<b>Brier Reliability Score:</b>", self.body_style), Paragraph(f"{best_metrics.get('brier_score', 0.0):.4f}", self.body_style)],
            [Paragraph("<b>Prediction Time (s):</b>", self.body_style), Paragraph(f"{best_metrics.get('prediction_time_seconds', 0.0):.6f}", self.body_style)],
            [Paragraph("<b>Selection Rationale:</b>", self.body_style), Paragraph(str(best_model.get("reason_for_selection")), self.body_style)],
        ]
        t_best = Table(best_info, colWidths=[2.2 * inch, 4.3 * inch])
        t_best.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EBF8FF")),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#3182CE")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t_best)
        story.append(Spacer(1, 15))

        rec_text = (
            f"<b>CRITICAL RECOMMENDATION:</b> Based on quantitative evaluation across all priority criteria, the calibrated "
            f"<b>{best_model.get('algorithm')}</b> model from <b>Experiment {best_model.get('experiment')}</b> is officially recommended. "
            f"This serialized model artifact will be used as the authoritative classifier for Layer 4 (Explainable AI)."
        )
        story.append(Paragraph(rec_text, self.body_style))
        story.append(PageBreak())

        story.append(Paragraph("Visual Comparison Charts", self.h1_style))
        chart_files = [
            "ranking.png", "algorithm_comparison.png", "experiment_comparison.png",
            "f1_score.png", "roc_auc.png", "brier_score.png",
            "accuracy.png", "precision.png", "recall.png",
            "training_time.png", "prediction_time.png", "feature_count.png", "heatmap_metrics.png"
        ]
        for img_name in chart_files:
            img_path = charts_dir / img_name
            if img_path.exists():
                story.append(Paragraph(f"Figure: {img_name.replace('.png', '').replace('_', ' ').title()}", self.h2_style))
                story.append(Image(str(img_path), width=6.5 * inch, height=3.8 * inch))
                story.append(Spacer(1, 15))
                if img_name in ["experiment_comparison.png", "brier_score.png", "recall.png", "feature_count.png"]:
                    story.append(PageBreak())

        doc.build(story)
