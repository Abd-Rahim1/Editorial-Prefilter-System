"""
test_terminal_pipeline_runner.py — Integration Tests for run_full_pipeline.py CLI
Verifies the end-to-end terminal pipeline runner across all 4 layers using
real and mock execution modes, exact 5-section Layer 4 report snapshotting (`--output`),
and strict error handling.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RUNNER_SCRIPT = PROJECT_ROOT / "scripts" / "run_full_pipeline.py"

MINIMAL_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 130 >>
stream
BT
/F1 12 Tf
70 700 Td
(Abstract: This is a test academic paper on deep learning and neural networks for natural language processing.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000447 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
519
%%EOF
"""


@pytest.fixture
def temp_pdf_file():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(MINIMAL_PDF_BYTES)
        f.flush()
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass


def test_runner_mock_mode_and_json_snapshot(temp_pdf_file):
    """Test full 4-layer sequential run in --mode mock and verify --output snapshot."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out_f:
        out_json_path = out_f.name

    try:
        cmd = [
            sys.executable,
            str(RUNNER_SCRIPT),
            "--pdf", temp_pdf_file,
            "--mode", "mock",
            "--conference", "iclr_2017",
            "--output", out_json_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        assert result.returncode == 0, f"Script failed: {result.stderr}\nOutput: {result.stdout}"
        assert "TFG PIPELINE EVALUATION SUMMARY" in result.stdout
        assert "LAYER 1 -- DETERMINISTIC EDITORIAL CHECKS" in result.stdout
        assert "LAYER 2 -- QWEN SEMANTIC EVALUATION" in result.stdout
        assert "LAYER 3 -- PROBABILISTIC CLASSIFICATION & POLICY" in result.stdout
        assert "LAYER 4 -- TREE SHAP VERIFICATION" in result.stdout
        assert "ASSISTED RECOMMENDATION" in result.stdout

        # Verify exact 5-section master JSON snapshot
        assert os.path.exists(out_json_path)
        with open(out_json_path, "r", encoding="utf-8") as fh:
            report = json.load(fh)

        # Verify exactly the 5 required top-level sections
        required_keys = {"prediction", "feature_importance", "editorial_rules", "semantic_scores", "natural_language_explanation"}
        assert set(report.keys()) == required_keys

        # Verify Layer 3 decision preservation
        l3_dec = report["prediction"]["decision"]
        assert str(l3_dec).upper() in {"DESK_REJECT", "MANUAL_REVIEW", "PEER_REVIEW"}
        assert "accept_probability" in report["prediction"]
        assert "desk_reject_probability" in report["prediction"]

    finally:
        if os.path.exists(out_json_path):
            try:
                os.remove(out_json_path)
            except Exception:
                pass


def test_runner_missing_pdf_exits_non_zero():
    """Verify that passing a non-existent PDF file exits with return code 1."""
    cmd = [
        sys.executable,
        str(RUNNER_SCRIPT),
        "--pdf", "non_existent_manuscript_999.pdf"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    assert result.returncode == 1
    assert "Input PDF file does not exist or is invalid" in result.stderr or result.stdout


def test_runner_direct_invocation(temp_pdf_file):
    """Verify that run_pipeline function can be invoked directly inside Python context."""
    from scripts.run_full_pipeline import run_pipeline, parse_args
    import argparse

    args = argparse.Namespace(
        pdf=temp_pdf_file,
        mode="mock",
        conference="iclr_2017",
        persist=False,
        output=None,
        verbose=False
    )
    report = run_pipeline(args)
    assert isinstance(report, dict)
    assert "prediction" in report
    assert "feature_importance" in report
