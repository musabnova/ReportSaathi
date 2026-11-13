"""
Tests for Core ReportSaathi API Routes.

Routes:
- GET /
- GET /health
- POST /explain-text
- POST /explain-file

All external services (Gemini, OCR, Supabase) are strictly mocked.
No real patient data or network requests are used.
"""

import io
import pytest
from fastapi.testclient import TestClient
import main
import explainer


# ---------------------------------------------------------------------------
# 1. Health & Root Endpoints
# ---------------------------------------------------------------------------
def test_read_root(client):
    """GET / must return service status and medical disclaimer."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ReportSaathi API"
    assert data["status"] == "running"
    assert "Disclaimer:" in data["disclaimer"]


def test_health_check(client):
    """GET /health must return ok status for load balancers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 2. POST /explain-text
# ---------------------------------------------------------------------------
def test_explain_text_valid_english(client, mock_services):
    """POST /explain-text returns structured explanation in English."""
    payload = {
        "text": "Hemoglobin: 11.2 g/dL (Normal: 13.0 - 17.0 g/dL)\nWBC: 6,500 /mcL",
        "language": "English",
    }
    response = client.post("/explain-text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "tests" in data
    assert len(data["tests"]) == 2
    assert "questions_for_doctor" in data
    assert "disclaimer" in data
    assert data.get("requested_language") == "English"


def test_explain_text_valid_languages(client, mock_services):
    """POST /explain-text supports Hindi and Kannada."""
    for lang in ["Hindi", "Kannada"]:
        payload = {
            "text": "Platelet Count: 250,000 /mcL",
            "language": lang,
        }
        response = client.post("/explain-text", json=payload)
        assert response.status_code == 200
        assert response.json().get("requested_language") == lang


def test_explain_text_empty_input(client):
    """POST /explain-text rejects empty or whitespace-only input."""
    response = client.post("/explain-text", json={"text": "   ", "language": "English"})
    assert response.status_code == 400
    assert "Report text cannot be empty" in response.json()["detail"]


def test_explain_text_unsupported_language(client):
    """POST /explain-text rejects unsupported languages."""
    response = client.post(
        "/explain-text",
        json={"text": "Hemoglobin 14.0", "language": "Spanish"},
    )
    assert response.status_code == 400
    assert "Unsupported language" in response.json()["detail"]


def test_explain_text_quota_exceeded(client, monkeypatch):
    """POST /explain-text returns HTTP 429 when Gemini quota is exceeded."""
    def fake_quota_error(text, language="English"):
        raise explainer.AIQuotaExceededError("Quota limit hit")

    monkeypatch.setattr(main, "explain_report", fake_quota_error)

    response = client.post(
        "/explain-text",
        json={"text": "Glucose 100 mg/dL", "language": "English"},
    )
    assert response.status_code == 429
    assert "quota exceeded" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 3. POST /explain-file
# ---------------------------------------------------------------------------
def test_explain_file_valid_pdf(client, mock_services):
    """POST /explain-file successfully processes a valid PDF upload."""
    pdf_bytes = b"%PDF-1.4 dummy synthetic pdf test content"
    files = {"file": ("blood_report.pdf", pdf_bytes, "application/pdf")}
    data = {"language": "English"}

    response = client.post("/explain-file", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert "extracted_text" in res_data
    assert "summary" in res_data
    assert "tests" in res_data
    assert len(res_data["tests"]) == 2


def test_explain_file_valid_images(client, mock_services):
    """POST /explain-file successfully processes valid PNG and JPG uploads."""
    # PNG test
    png_bytes = b"\x89PNG\r\n\x1a\n synthetic png test content"
    files_png = {"file": ("report_photo.png", png_bytes, "image/png")}
    res_png = client.post("/explain-file", files=files_png, data={"language": "English"})
    assert res_png.status_code == 200
    assert "extracted_text" in res_png.json()
    assert "tests" in res_png.json()

    # JPG test
    jpg_bytes = b"\xff\xd8\xff\xe0 synthetic jpg test content"
    files_jpg = {"file": ("report_photo.jpg", jpg_bytes, "image/jpeg")}
    res_jpg = client.post("/explain-file", files=files_jpg, data={"language": "English"})
    assert res_jpg.status_code == 200
    assert "extracted_text" in res_jpg.json()
    assert "tests" in res_jpg.json()


def test_explain_file_unsupported_extension(client):
    """POST /explain-file rejects files with unsupported extensions (.docx)."""
    docx_bytes = b"PK\x03\x04 fake docx"
    files = {"file": ("report.docx", docx_bytes, "application/vnd.openxmlformats")}
    response = client.post("/explain-file", files=files, data={"language": "English"})
    assert response.status_code == 415
    assert "Unsupported file format" in response.json()["detail"]


def test_explain_file_oversized(client):
    """POST /explain-file rejects files larger than 5 MB."""
    huge_bytes = b"%PDF" + b"0" * (5 * 1024 * 1024 + 10)
    files = {"file": ("large_report.pdf", huge_bytes, "application/pdf")}
    response = client.post("/explain-file", files=files, data={"language": "English"})
    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"]


def test_explain_file_signature_mismatch(client, monkeypatch):
    """POST /explain-file rejects files whose actual magic bytes do not match expected types."""
    # Spoofed file named .pdf with text content
    fake_pdf = b"Hello, I am plain text, not a real PDF!"
    files = {"file": ("spoofed.pdf", fake_pdf, "application/pdf")}

    response = client.post("/explain-file", files=files, data={"language": "English"})
    assert response.status_code == 415
    assert "Invalid file signature" in response.json()["detail"]
