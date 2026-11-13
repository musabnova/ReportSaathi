"""
Shared pytest fixtures and test configuration for ReportSaathi backend tests.
"""

import sys
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is always in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Set test environment variables before importing app modules
os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
os.environ["TELEGRAM_SECRET_TOKEN"] = "test_webhook_secret_key_12345"
os.environ["GEMINI_API_KEY"] = "mock_gemini_test_api_key"
os.environ["SUPABASE_URL"] = "https://mocktest.supabase.co"
os.environ["SUPABASE_KEY"] = "mock_supabase_test_key"
os.environ["ALLOWED_ORIGINS"] = "*"

import main
import bot
import explainer
import ocr
import db


@pytest.fixture
def client():
    """Provides a FastAPI TestClient instance."""
    return TestClient(main.app)


@pytest.fixture
def mock_explanation_data():
    """Returns a standard mock structured explanation dictionary."""
    return {
        "summary": "Your hemoglobin level is slightly below the normal reference range, suggesting mild anemia.",
        "tests": [
            {
                "name": "Hemoglobin",
                "value": "11.2 g/dL",
                "normal_range": "13.0 - 17.0 g/dL",
                "status": "low",
                "meaning": "Below standard healthy range.",
            },
            {
                "name": "WBC",
                "value": "6,500 /mcL",
                "normal_range": "4,000 - 11,000 /mcL",
                "status": "normal",
                "meaning": "Within healthy reference range.",
            },
        ],
        "questions_for_doctor": [
            "What could be causing the low hemoglobin level?",
            "Do I need iron supplements?",
        ],
        "disclaimer": "This is educational information, not a medical diagnosis.",
    }


@pytest.fixture
def mock_services(monkeypatch, mock_explanation_data):
    """Mocks external Gemini explainer, OCR, Supabase DB, and Telegram post calls."""
    # Mock Gemini explain_report
    def fake_explain_report(text, language="English"):
        data = dict(mock_explanation_data)
        data["requested_language"] = language
        return data

    monkeypatch.setattr(main, "explain_report", fake_explain_report)
    monkeypatch.setattr(bot, "explain_report", fake_explain_report)

    # Mock OCR extract_text
    def fake_extract_text(file_bytes, mime_type):
        return "Hemoglobin 11.2 g/dL (Reference: 13.0 - 17.0 g/dL)\nWBC 6,500 /mcL"

    monkeypatch.setattr(main, "extract_text", fake_extract_text)
    monkeypatch.setattr(bot, "extract_text", fake_extract_text)

    # Mock validate_file_signature in main & bot
    def fake_validate_sig(file_bytes):
        if file_bytes.startswith(b"%PDF"):
            return "application/pdf"
        elif file_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif file_bytes.startswith(b"\x89PNG"):
            return "image/png"
        raise ValueError("Invalid file signature")

    monkeypatch.setattr(main, "validate_file_signature", fake_validate_sig)
    monkeypatch.setattr(bot, "validate_file_signature", fake_validate_sig)

    # Mock Supabase db.log_usage
    monkeypatch.setattr(main, "log_usage", lambda **kwargs: True)
    monkeypatch.setattr(bot, "log_usage", lambda **kwargs: True)

    # Mock Telegram outgoing calls
    captured_messages = []

    async def fake_telegram_post(method, payload):
        captured_messages.append({"method": method, "payload": payload})
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 999}}
        if method == "answerCallbackQuery":
            return {"ok": True}
        return {"ok": True, "result": {}}

    monkeypatch.setattr(bot, "_telegram_post", fake_telegram_post)

    return captured_messages
