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
import hmac
import asyncio
import logging
import ipaddress
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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
from bot import (
    init_telegram_bot,
    shutdown_telegram_bot,
    handle_telegram_update,
    track_background_task,
    get_bot_token,
    get_secret_token,
)

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

# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes Telegram Bot (webhook or local polling) on startup,
    and safely terminates background tasks on shutdown.
    """
    try:
        await init_telegram_bot()
    except Exception as e:
        logger.warning(f"Telegram Bot startup error: {e}")
    yield
    try:
        await shutdown_telegram_bot()
    except Exception as e:
        logger.warning(f"Telegram Bot shutdown error: {e}")


# Number of trusted reverse proxies in front of the application (e.g., Render load balancer = 1)
FORWARDED_PROXIES_COUNT = int(os.getenv("FORWARDED_PROXIES_COUNT", "1").strip() or "1")


def get_client_ip(request: Request) -> str:
    """
    Securely extracts the client IP address without blindly trusting client-supplied
    X-Forwarded-For headers.

    Behind a reverse proxy (like Render's Envoy load balancer), the proxy appends the
    connecting client's authentic IP to the end of the X-Forwarded-For header. Blindly
    taking the first IP allows attackers to spoof arbitrary IPs by prepending them.
    By indexing from the right (-FORWARDED_PROXIES_COUNT), we extract the genuine IP
    recorded by the trusted reverse proxy layer.

    Validates that the candidate is a syntactically valid IPv4 or IPv6 address.
    Falls back safely to request.client.host or '127.0.0.1'.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        raw_ips = [item.strip() for item in forwarded.split(",") if item.strip()]
        if raw_ips:
            # Select the IP at the boundary of our trusted reverse proxy count
            proxy_index = -FORWARDED_PROXIES_COUNT
            candidate = raw_ips[proxy_index] if abs(proxy_index) <= len(raw_ips) else raw_ips[0]
            try:
                validated_ip = ipaddress.ip_address(candidate)
                return str(validated_ip)
            except ValueError:
                logger.warning(
                    f"Malformed IP '{candidate}' encountered in X-Forwarded-For header: '{forwarded}'"
                )

    if request.client and request.client.host:
        try:
            return str(ipaddress.ip_address(request.client.host))
        except ValueError:
            pass

    return "127.0.0.1"


# API Rate Limiter Setup
# Defaults to in-memory moving-window rate limiting per worker.
# Automatically switches to shared distributed rate limiting if REDIS_URL is configured.
RATE_LIMIT_TEXT = os.getenv("RATE_LIMIT_TEXT", "15/minute").strip() or "15/minute"
RATE_LIMIT_FILE = os.getenv("RATE_LIMIT_FILE", "10/minute").strip() or "10/minute"
_redis_url = os.getenv("REDIS_URL", "").strip()
_storage_uri = _redis_url if _redis_url else "memory://"

limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=_storage_uri,
    default_limits=[],
)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    client_ip = get_client_ip(request)
    logger.warning(
        f"Rate limit exceeded for client {client_ip} on {request.method} {request.url.path}."
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded. Too many report explanation requests. Please wait a moment and try again."
        },
    )


# Initialize FastAPI application
app = FastAPI(
    title="ReportSaathi API",
    description="A plain-language medical report explainer API. For educational purposes only.",
    version="0.1.0",
    lifespan=lifespan,
)

# Attach rate limiter to app state and middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure Cross-Origin Resource Sharing (CORS)
# Reads ALLOWED_ORIGINS from environment variables (comma-separated).
# Defaults to wildcard ("*") for local development if unset or set to "*".
_raw_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").strip()
if _raw_allowed_origins == "*" or not _raw_allowed_origins:
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [
        origin.strip().rstrip("/")
        for origin in _raw_allowed_origins.split(",")
        if origin.strip().rstrip("/")
    ]
    if not ALLOWED_ORIGINS:
        ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
# Telegram Bot Webhook Endpoint
# ---------------------------------------------------------------------------
@app.post("/telegram/webhook", status_code=status.HTTP_200_OK)
async def telegram_webhook_endpoint(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """
    Secure Webhook endpoint for receiving Telegram updates in production.
    Validates X-Telegram-Bot-Api-Secret-Token to ensure requests originate from Telegram.
    Updates are dispatched asynchronously so Telegram receives an immediate 200 OK acknowledgment.
    """
    expected_secret = get_secret_token()
    if not expected_secret:
        logger.warning("Rejected Telegram webhook: TELEGRAM_SECRET_TOKEN not configured.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook secret not configured.",
        )

    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        expected_secret, x_telegram_bot_api_secret_token
    ):
        logger.warning("Rejected Telegram webhook update: invalid or missing secret token header.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram secret token header.",
        )

    token = get_bot_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram Bot is not configured on this server.",
        )

    try:
        update_data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload in Telegram update.",
        )

    # Dispatch processing asynchronously to ensure immediate HTTP 200 response to Telegram
    track_background_task(handle_telegram_update(update_data))

    return {"ok": True}


# ---------------------------------------------------------------------------
# Explanation Endpoints
# ---------------------------------------------------------------------------
@app.post("/explain-text", status_code=status.HTTP_200_OK)
@limiter.limit(RATE_LIMIT_TEXT)
def explain_text_endpoint(request: Request, payload: ExplainTextRequest):
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
@limiter.limit(RATE_LIMIT_FILE)
def explain_file_endpoint(
    request: Request,
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
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while extracting text from the document. Please ensure the document is clear and try again.",
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
