"""
Tests for Multilingual OCR Language Detection and Configuration.

Requirements:
- Detect installed language packs among eng, hin, kan using pytesseract.get_languages(config="").
- Build safe plus-separated language strings (e.g. 'eng+hin+kan', 'eng+hin').
- Gracefully fall back to 'eng' when additional languages or detection fails.
- Pass detected languages into every image and scanned PDF OCR call.
"""

import io
import pytest
from PIL import Image
import pytesseract
import ocr


def test_get_available_ocr_languages_all_installed(monkeypatch):
    """When eng, hin, and kan are all installed, build combined 'eng+hin+kan'."""
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "hin", "kan", "osd"])
    lang_str = ocr.get_available_ocr_languages()
    assert lang_str == "eng+hin+kan"


def test_get_available_ocr_languages_english_and_hindi(monkeypatch):
    """When eng and hin are installed, build 'eng+hin'."""
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "hin", "osd"])
    lang_str = ocr.get_available_ocr_languages()
    assert lang_str == "eng+hin"


def test_get_available_ocr_languages_english_and_kannada(monkeypatch):
    """When eng and kan are installed, build 'eng+kan'."""
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "kan", "osd"])
    lang_str = ocr.get_available_ocr_languages()
    assert lang_str == "eng+kan"


def test_get_available_ocr_languages_only_english(monkeypatch):
    """When only eng is installed, return 'eng'."""
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "osd"])
    lang_str = ocr.get_available_ocr_languages()
    assert lang_str == "eng"


def test_get_available_ocr_languages_exception_fallback(monkeypatch):
    """When pytesseract.get_languages raises an exception, safely fall back to 'eng' without crashing."""
    def crash_get_languages(config=""):
        raise RuntimeError("Tesseract binary not found or tessdata inaccessible")

    monkeypatch.setattr(pytesseract, "get_languages", crash_get_languages)
    lang_str = ocr.get_available_ocr_languages()
    assert lang_str == "eng"


def test_get_available_ocr_languages_unrelated_installed(monkeypatch):
    """When only unrelated languages are installed, fall back to 'eng'."""
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["fra", "deu", "spa"])
    lang_str = ocr.get_available_ocr_languages()
    assert lang_str == "eng"


def test_image_ocr_invokes_with_detected_languages(monkeypatch):
    """_extract_from_image must pass the detected multilingual language string to pytesseract.image_to_string."""
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "hin", "kan"])

    captured_lang = []

    def mock_image_to_string(img, lang=None, **kwargs):
        captured_lang.append(lang)
        return "Hemoglobin 14.0 g/dL"

    monkeypatch.setattr(pytesseract, "image_to_string", mock_image_to_string)

    # Create dummy in-memory image bytes
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    result = ocr._extract_from_image(image_bytes)

    assert result == "Hemoglobin 14.0 g/dL"
    assert len(captured_lang) == 1
    assert captured_lang[0] == "eng+hin+kan"


def test_scanned_pdf_ocr_invokes_with_detected_languages(monkeypatch):
    """_extract_from_pdf (scanned fallback) must pass detected multilingual languages to pytesseract."""
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "hin", "kan"])

    # Force scanned PDF branch by returning empty digital text
    class FakeEmptyPage:
        def extract_text(self):
            return ""

    class FakePdfReader:
        def __init__(self, stream):
            self.pages = [FakeEmptyPage()]

    monkeypatch.setattr("pypdf.PdfReader", FakePdfReader)

    # Mock pdf2image.convert_from_bytes
    dummy_img = Image.new("RGB", (50, 50), color=(255, 255, 255))
    monkeypatch.setattr("pdf2image.convert_from_bytes", lambda file_bytes, **kwargs: [dummy_img])

    captured_lang = []

    def mock_image_to_string(img, lang=None, **kwargs):
        captured_lang.append(lang)
        return "Platelets 250,000 /mcL"

    monkeypatch.setattr(pytesseract, "image_to_string", mock_image_to_string)

    result = ocr._extract_from_pdf(b"%PDF-1.4 dummy scanned pdf")

    assert result == "Platelets 250,000 /mcL"
    assert len(captured_lang) == 1
    assert captured_lang[0] == "eng+hin+kan"