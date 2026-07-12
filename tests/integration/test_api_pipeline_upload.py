"""
test_api_pipeline_upload.py — Integration Tests for FastAPI Pipeline Upload Workflow
"""

import os
import sys
import time
import io
import json
import pytest
from pathlib import Path

# Ensure apps/api and packages are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))
sys.path.insert(0, str(PROJECT_ROOT / "packages"))

from fastapi.testclient import TestClient
from main import app

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
def api_client():
    os.environ["DEMO_AUTH_ENABLED"] = "true"
    os.environ["ENVIRONMENT"] = "development"
    return TestClient(app)


def test_api_pipeline_upload_flow(api_client):
    """
    Test the full API upload, status, list, prediction, explanation, and report endpoints.
    """
    pdf_file = io.BytesIO(MINIMAL_PDF_BYTES)
    headers = {"Authorization": "Bearer dummy-admin-token"}
    
    # 1. POST /api/v1/pipelines/evaluate (Upload PDF)
    response = api_client.post(
        "/api/v1/pipelines/evaluate",
        files={"file": ("test_manuscript.pdf", pdf_file, "application/pdf")},
        data={"version": "v5", "mode": "mock"},
        headers=headers
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "manuscript_id" in res_data
    assert res_data["status"] == "processing"
    
    m_id = res_data["manuscript_id"]
    
    # 2. Wait a bit for background process to finish in mock mode
    time.sleep(2)
    
    # 3. GET /api/v1/pipelines/status/{manuscript_id}
    status_response = api_client.get(f"/api/v1/pipelines/status/{m_id}", headers=headers)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["success"] is True
    assert "stage_progress" in status_data
    
    # 4. GET /api/manuscripts (List manuscripts)
    list_response = api_client.get("/api/manuscripts", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["success"] is True
    assert len(list_data["manuscripts"]) > 0
    
    # Find uploaded manuscript in the list
    uploaded_m = next((m for m in list_data["manuscripts"] if m["id"] == m_id), None)
    assert uploaded_m is not None
    assert uploaded_m["status"] == "reviewed"
    
    # 5. GET /api/manuscripts/{manuscript_id}/prediction
    pred_response = api_client.get(f"/api/manuscripts/{m_id}/prediction", headers=headers)
    assert pred_response.status_code == 200
    pred_data = pred_response.json()
    assert pred_data["success"] is True
    assert "prediction" in pred_data
    assert "desk_reject_probability" in pred_data["prediction"]
    
    # 6. GET /api/manuscripts/{manuscript_id}/explanation
    exp_response = api_client.get(f"/api/manuscripts/{m_id}/explanation", headers=headers)
    assert exp_response.status_code == 200
    exp_data = exp_response.json()
    assert exp_data["success"] is True
    assert "explanation" in exp_data
    assert "explanation_text" in exp_data["explanation"]
    
    # 7. GET /api/manuscripts/{manuscript_id}/report
    rep_response = api_client.get(f"/api/manuscripts/{m_id}/report", headers=headers)
    assert rep_response.status_code == 200
    rep_data = rep_response.json()
    assert "prediction" in rep_data
    assert "feature_importance" in rep_data
    assert "editorial_rules" in rep_data
    assert "semantic_scores" in rep_data
    assert "natural_language_explanation" in rep_data
