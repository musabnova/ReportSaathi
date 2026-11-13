"""
ReportSaathi - Backend API
Main FastAPI application entry point with health check and report explanation endpoints.

MEDICAL DISCLAIMER:
This application is for educational and informational purposes only.
It does NOT provide medical advice, diagnosis, or treatment recommendations.
Always consult a qualified healthcare professional with any questions regarding medical conditions.
Uploaded medical reports and text are processed strictly in-memory and are never permanently stored.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Robust environment variable loading
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

# Import OCR extraction, magic byte validation, and Gemini explainer with custom errors
from ocr import extract_text, validate_file_signature, TesseractUnavailableError
from explainer import (
    explain_report,
    DEFAULT_DISCLAIMER,
    AIConfigurationError,
    AIModelUnavailableError,
    AIQuotaExceededError,
    AIServiceError,
    AIResponseParseError,
)
from db import log_usage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants & Constraints
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB maximum upload limit
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/pdf",
}

# Supported Natural Languages
ALLOWED_LANGUAGES = {
    "english": "English",
    "hindi": "Hindi",
    "kannada": "Kannada",
}

# Standard medical disclaimer for API consumers
MEDICAL_DISCLAIMER = (
    "Disclaimer: ReportSaathi provides educational explanations only. "
    "It does not provide medical diagnoses, treatment plans, or medicine recommendations. "
    "Always discuss your medical reports and symptoms directly with a qualified doctor."
)

# Initialize FastAPI application
app = FastAPI(
    title="ReportSaathi API",
    description="A plain-language medical report explainer API. For educational purposes only.",
    version="0.1.0",
)

# Configure Cross-Origin Resource Sharing (CORS)
# Currently allowing all origins for development; will restrict to specific domains in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class ExplainTextRequest(BaseModel):
    text: str = Field(..., description="Raw text of the medical report to explain")
    language: str = Field(
        default="English",
        description="Target explanation language: 'English', 'Hindi', or 'Kannada'",
    )


def _validate_language(language_input: str) -> str:
    """
    Validates that the requested language is strictly English, Hindi, or Kannada.

    Returns:
        str: Canonical capitalized language name ('English', 'Hindi', 'Kannada').

    Raises:
        HTTPException (400): If the language is not supported.
    """
    clean_lang = language_input.strip().lower()
    if clean_lang not in ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language. Supported languages are: English, Hindi, Kannada.",
        )
    return ALLOWED_LANGUAGES[clean_lang]


def _log_report_usage(source: str, language: str, explanation: dict) -> None:
    """
    Extracts anonymous operational metrics (test count, abnormal test count)
    and logs them to the Supabase database.

    PRIVACY GUARANTEE:
    Only aggregate numerical counts, the source channel, and the language are recorded.
    Report text, OCR text, patient information, and test names/values are NEVER logged.

    Non-blocking:
    Any error during database logging is caught and handled safely so that
    a database hiccup never interrupts a successful report explanation response.
    """
    try:
        tests = explanation.get("tests", []) if isinstance(explanation, dict) else []
        tests_count = len(tests)
        abnormal_count = sum(
            1
            for t in tests
            if isinstance(t, dict) and str(t.get("status", "")).strip().lower() in ("high", "low")
        )

        log_usage(
            source=source,
            language=language,
            tests_count=tests_count,
            abnormal_count=abnormal_count,
        )
    except Exception as e:
        logger.warning(f"Failed to record usage metrics to database: {e}")


# ---------------------------------------------------------------------------
# Basic & Health Check Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    """Root endpoint providing service status and medical disclaimer."""
    return {
        "service": "ReportSaathi API",
        "status": "running",
        "disclaimer": MEDICAL_DISCLAIMER,
    }


@app.get("/health")
def health_check():
    """Health check endpoint to verify backend service availability."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Explanation Endpoints
# ---------------------------------------------------------------------------
@app.post("/explain-text", status_code=status.HTTP_200_OK)
def explain_text_endpoint(payload: ExplainTextRequest):
    """
    Explains pasted medical report text using Gemini.

    Accepts JSON containing 'text' and optional 'language' (English, Hindi, Kannada).
    Returns structured explanation including test values, status, meanings,
    questions for the doctor, and an educational disclaimer.
    """
    # 1. Validate language restriction
    target_lang = _validate_language(payload.language)

    # 2. Validate non-empty text input
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report text cannot be empty. Please provide valid report text.",
        )

    # Privacy rule: Log only metadata, never log patient or medical text content
    logger.info(
        f"Processing /explain-text: chars={len(raw_text)}, language='{target_lang}'"
    )

    try:
        explanation = explain_report(raw_text, language=target_lang)

        # Log anonymous usage statistics (source='web')
        _log_report_usage(source="web", language=target_lang, explanation=explanation)

        return explanation

    except AIConfigurationError as ce:
        logger.error(f"AI configuration error: {ce}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service authentication error. Please verify GEMINI_API_KEY in backend/.env.",
        )
    except AIModelUnavailableError as me:
        logger.error(f"AI model unavailable error: {me}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(me),
        )
    except AIQuotaExceededError as qe:
        logger.warning(f"AI quota exceeded: {qe}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limit or quota exceeded. Please try again shortly.",
        )
    except AIServiceError as se:
        logger.error(f"AI service error: {se}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is temporarily experiencing high load. Please try again in a few moments.",
        )
    except AIResponseParseError as pe:
        logger.error(f"AI response parse error: {pe}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate a valid structured explanation. Please try again.",
        )
    except ValueError as ve:
        logger.warning(f"Validation error during text explanation: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Unexpected error during text explanation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the report explanation.",
        )


@app.post("/explain-file", status_code=status.HTTP_200_OK)
def explain_file_endpoint(
    file: UploadFile = File(..., description="Uploaded medical report image or PDF"),
    language: str = Form("English", description="Target language ('English', 'Hindi', 'Kannada')"),
):
    """
    Extracts text from an uploaded report file (JPG, PNG, PDF) using OCR,
    then explains the extracted content using Gemini.

    - Validates file extensions, MIME types, and actual binary signatures.
    - Enforces 5 MB file size limit.
    - Restricts language to English, Hindi, or Kannada.
    - Processes files strictly in-memory (no permanent disk storage).
    - Returns structured explanation plus the raw extracted text.
    """
    # 1. Validate language restriction
    target_lang = _validate_language(language)

    # 2. Validate file presence
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file was uploaded. Please upload a medical report file.",
        )

    # 3. Validate file extension
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file format '{ext}'. Allowed formats: JPG, JPEG, PNG, PDF.",
        )

    # 4. Normalize MIME type hint
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_CONTENT_TYPES:
        ext_to_mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }
        content_type = ext_to_mime.get(ext, content_type)

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type '{content_type}'. Allowed types: JPG, PNG, PDF.",
        )

    # 5. Read file safely in memory with 5 MB size limit
    # Read MAX_FILE_SIZE_BYTES + 1 to detect oversize uploads without loading arbitrarily large data
    file_bytes = file.file.read(MAX_FILE_SIZE_BYTES + 1)

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty. Please provide a valid file.",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 5 MB limit. Please upload a smaller file.",
        )

    # 6. Validate actual file signature (magic bytes) to prevent extension spoofing
    try:
        detected_mime = validate_file_signature(file_bytes)
    except ValueError as ve:
        logger.warning(f"File signature validation failed for '{file.filename}': {ve}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(ve),
        )

    # Privacy rule: Log only metadata, never the contents of medical reports
    logger.info(
        f"Processing /explain-file: filename='{file.filename}', size_bytes={len(file_bytes)}, "
        f"detected_mime='{detected_mime}', language='{target_lang}'"
    )

    # 7. Extract text via OCR entirely in-memory
    try:
        extracted_text = extract_text(file_bytes, detected_mime)
    except TesseractUnavailableError as tue:
        logger.error(f"Tesseract OCR unavailable: {tue}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(tue),
        )
    except ValueError as ve:
        logger.warning(f"Validation error during OCR: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from the uploaded document: {str(e)}",
        )

    # Check if any readable text was extracted
    if not extracted_text or not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any readable text from the document. Please ensure the document is clear and legible.",
        )

    # 8. Explain extracted report text with Gemini
    try:
        explanation = explain_report(extracted_text, language=target_lang)

        # Log anonymous usage statistics (source='web')
        _log_report_usage(source="web", language=target_lang, explanation=explanation)

        # Return structured explanation alongside raw extracted text
        return {
            **explanation,
            "extracted_text": extracted_text,
        }

    except AIConfigurationError as ce:
        logger.error(f"AI configuration error: {ce}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service authentication error. Please verify GEMINI_API_KEY in backend/.env.",
        )
    except AIModelUnavailableError as me:
        logger.error(f"AI model unavailable error: {me}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(me),
        )
    except AIQuotaExceededError as qe:
        logger.warning(f"AI quota exceeded: {qe}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limit or quota exceeded. Please try again shortly.",
        )
    except AIServiceError as se:
        logger.error(f"AI service error: {se}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is temporarily experiencing high load. Please try again in a few moments.",
        )
    except AIResponseParseError as pe:
        logger.error(f"AI response parse error: {pe}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate a valid structured explanation. Please try again.",
        )
    except ValueError as ve:
        logger.warning(f"Validation error during file report explanation: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Unexpected error during report explanation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the report explanation.",
        )
