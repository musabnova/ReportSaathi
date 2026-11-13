"""
Tests for Telegram Bot File Validation & Size Enforcement.

Requirements:
- Valid PDF, JPG, JPEG and PNG
- Incorrect extension/MIME combinations
- Missing metadata
- Oversized files rejected before download
"""

import asyncio
import pytest
import bot


def test_valid_file_formats():
    """Valid PDF, JPG, JPEG, and PNG files with matching MIME types are accepted."""
    test_cases = [
        ("report.pdf", "application/pdf", "application/pdf"),
        ("REPORT.PDF", "application/pdf", "application/pdf"),
        ("scan.jpg", "image/jpeg", "image/jpeg"),
        ("scan.jpeg", "image/jpeg", "image/jpeg"),
        ("photo.png", "image/png", "image/png"),
        ("report.pdf", "application/pdf; charset=binary", "application/pdf"),
        ("scan.jpg", "image/jpg", "image/jpg"),
    ]
    for filename, mime, expected_mime in test_cases:
        is_valid, result = bot.validate_telegram_file_metadata(filename, mime)
        assert is_valid is True, f"Failed for {filename} with MIME {mime}: {result}"
        assert result == expected_mime


@pytest.mark.parametrize(
    "filename,mime",
    [
        ("report.pdf", "image/png"),
        ("report.pdf", "image/jpeg"),
        ("scan.jpg", "application/pdf"),
        ("scan.jpeg", "image/png"),
        ("photo.png", "application/pdf"),
        ("photo.png", "image/jpeg"),
    ],
)
def test_incorrect_extension_mime_combinations(filename, mime):
    """Files with mismatched extension and MIME type must be rejected."""
    is_valid, reason = bot.validate_telegram_file_metadata(filename, mime)
    assert is_valid is False
    assert "File format mismatch" in reason


@pytest.mark.parametrize(
    "filename,mime",
    [
        ("document.docx", "application/pdf"),
        ("archive.zip", "application/pdf"),
        ("script.py", "text/plain"),
        ("malicious.exe", "application/octet-stream"),
        ("notes.txt", "text/plain"),
    ],
)
def test_unsupported_extensions_rejected(filename, mime):
    """Unsupported document extensions must be rejected."""
    is_valid, reason = bot.validate_telegram_file_metadata(filename, mime)
    assert is_valid is False
    assert "Unsupported file format" in reason


@pytest.mark.parametrize(
    "filename,mime,expected_substr",
    [
        (None, "application/pdf", "missing"),
        ("", "application/pdf", "missing"),
        ("   ", "application/pdf", "missing"),
        ("report_no_ext", "application/pdf", "no extension"),
        ("report.pdf", None, "missing"),
        ("report.pdf", "", "missing"),
        ("report.pdf", "   ", "missing"),
    ],
)
def test_missing_or_malformed_metadata(filename, mime, expected_substr):
    """Documents with missing name, missing extension, or missing MIME must be rejected safely."""
    is_valid, reason = bot.validate_telegram_file_metadata(filename, mime)
    assert is_valid is False
    assert expected_substr.lower() in reason.lower()


def test_oversized_document_rejected_before_download(monkeypatch):
    """Documents larger than 5 MB must be rejected immediately without downloading bytes."""
    download_called = False

    async def fake_download(file_id):
        nonlocal download_called
        download_called = True
        return b"fake_bytes"

    sent_messages = []

    async def fake_telegram_post(method, payload):
        sent_messages.append({"method": method, "payload": payload})
        return {"ok": True, "result": {}}

    monkeypatch.setattr(bot, "_download_telegram_file_bytes", fake_download)
    monkeypatch.setattr(bot, "_telegram_post", fake_telegram_post)

    oversized_doc = {
        "file_name": "heavy_scan.pdf",
        "file_size": 6 * 1024 * 1024,  # 6 MB (> 5 MB)
        "mime_type": "application/pdf",
        "file_id": "file_heavy_123",
    }

    asyncio.run(bot._handle_document_upload(chat_id=123, document=oversized_doc))

    assert download_called is False, "Oversized file should never trigger download!"
    assert len(sent_messages) == 1
    assert "exceeds limit" in sent_messages[0]["payload"]["text"]


def test_oversized_photo_rejected_before_download(monkeypatch):
    """Photos larger than 5 MB must be rejected immediately without downloading bytes."""
    download_called = False

    async def fake_download(file_id):
        nonlocal download_called
        download_called = True
        return b"fake_bytes"

    sent_messages = []

    async def fake_telegram_post(method, payload):
        sent_messages.append({"method": method, "payload": payload})
        return {"ok": True, "result": {}}

    monkeypatch.setattr(bot, "_download_telegram_file_bytes", fake_download)
    monkeypatch.setattr(bot, "_telegram_post", fake_telegram_post)

    oversized_photo_list = [
        {"file_id": "thumb_1", "file_size": 1000},
        {"file_id": "photo_full", "file_size": 7 * 1024 * 1024},  # 7 MB (> 5 MB)
    ]

    asyncio.run(bot._handle_photo_upload(chat_id=123, photo_list=oversized_photo_list))

    assert download_called is False, "Oversized photo should never trigger download!"
    assert len(sent_messages) == 1
    assert "exceeds 5 MB limit" in sent_messages[0]["payload"]["text"]


def test_mismatch_document_rejected_in_dispatcher(monkeypatch):
    """Document with mismatching extension/MIME rejected before downloading."""
    download_called = False

    async def fake_download(file_id):
        nonlocal download_called
        download_called = True
        return b"fake_bytes"

    sent_messages = []

    async def fake_telegram_post(method, payload):
        sent_messages.append({"method": method, "payload": payload})
        return {"ok": True, "result": {}}

    monkeypatch.setattr(bot, "_download_telegram_file_bytes", fake_download)
    monkeypatch.setattr(bot, "_telegram_post", fake_telegram_post)

    mismatched_doc = {
        "file_name": "report.pdf",
        "file_size": 200 * 1024,
        "mime_type": "image/png",  # Mismatched!
        "file_id": "file_mismatch_999",
    }

    asyncio.run(bot._handle_document_upload(chat_id=123, document=mismatched_doc))

    assert download_called is False
    assert len(sent_messages) == 1
    assert "File format mismatch" in sent_messages[0]["payload"]["text"]
