"""
ReportSaathi - Telegram Bot Module
Asynchronous Telegram Bot client integrated natively into FastAPI using httpx.

KEY CAPABILITIES:
- Supports /start, /help, and /language commands.
- Interactive inline keyboards for language selection (English, Hindi, Kannada).
- Processes pasted text, photos (JPG, PNG), and PDF documents in-memory.
- Enforces 5 MB file size limit before downloading.
- Runs CPU/network-bound OCR and Gemini logic via asyncio.to_thread().
- Supports dual deployment: Webhook for Render production, Long Polling for local dev.
- Secures webhook updates with X-Telegram-Bot-Api-Secret-Token.
- Splits long responses safely within Telegram's 4096-character limit while preserving disclaimers.
- Logs usage anonymously to Supabase (source="telegram").
"""

import os
import io
import json
import html
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Set, Union
import httpx

# Import existing core modules
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

logger = logging.getLogger(__name__)

# Constants & Constraints
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB maximum upload limit
TELEGRAM_MSG_MAX_LENGTH = 4000          # Telegram max is 4096, buffer for formatting safety

# File format validation: maps allowed extensions to expected MIME types
EXTENSION_TO_MIMES = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg", "image/jpg"},
    ".jpeg": {"image/jpeg", "image/jpg"},
    ".png": {"image/png"},
}
ALLOWED_FILE_EXTENSIONS = set(EXTENSION_TO_MIMES.keys())
ALLOWED_MIME_TYPES = {mime for mimes in EXTENSION_TO_MIMES.values() for mime in mimes}

# In-memory user language preference store (chat_id -> language)
# Defaults to English if not explicitly set
USER_LANGUAGES: Dict[int, str] = {}

# Background task tracking for unhandled exception logging and graceful shutdown
ACTIVE_BACKGROUND_TASKS: Set[asyncio.Task] = set()

# Background polling task reference for cancellation during shutdown
_polling_task: Optional[asyncio.Task] = None
_bot_is_running: bool = False


# ---------------------------------------------------------------------------
# Background Task Tracking
# ---------------------------------------------------------------------------
def track_background_task(coro) -> asyncio.Task:
    """
    Schedules an asyncio task, tracks it in ACTIVE_BACKGROUND_TASKS,
    and attaches a done callback to safely capture and log unhandled exceptions.
    """
    task = asyncio.create_task(coro)
    ACTIVE_BACKGROUND_TASKS.add(task)

    def _on_task_done(t: asyncio.Task) -> None:
        ACTIVE_BACKGROUND_TASKS.discard(t)
        try:
            if not t.cancelled():
                exc = t.exception()
                if exc:
                    logger.error(
                        f"Unhandled exception in Telegram background task: {exc}",
                        exc_info=exc,
                    )
        except Exception as log_err:
            logger.error(f"Error checking background task completion status: {log_err}")

    task.add_done_callback(_on_task_done)
    return task


# ---------------------------------------------------------------------------
# Configuration Helpers
# ---------------------------------------------------------------------------
def get_bot_token() -> Optional[str]:
    """Retrieves and validates TELEGRAM_BOT_TOKEN from environment."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or "your_telegram" in token.lower() or token.lower() == "none":
        return None
    return token


def get_secret_token() -> Optional[str]:
    """
    Retrieves the webhook security token from environment.
    Returns None if missing or empty (never defaults to an insecure fallback).
    """
    token = os.getenv("TELEGRAM_SECRET_TOKEN", "").strip()
    return token if token else None


def validate_telegram_file_metadata(
    file_name: Optional[str], mime_type: Optional[str]
) -> Tuple[bool, str]:
    """
    Validates file extension and MIME type together.
    Rejects files if:
    - file_name or mime_type metadata is missing/empty.
    - file extension is unsupported.
    - MIME type is unsupported or does not match the extension.

    Returns:
        Tuple of (is_valid: bool, validated_mime_or_error_reason: str)
    """
    if not file_name or not isinstance(file_name, str) or not file_name.strip():
        return False, "Document file name metadata is missing."

    _, ext = os.path.splitext(file_name.lower().strip())
    if not ext:
        return False, "Document file has no extension. Please upload a file ending with .pdf, .jpg, or .png."

    if ext not in EXTENSION_TO_MIMES:
        return (
            False,
            f"Unsupported file format '{ext}'. ReportSaathi supports PDF, JPG, and PNG documents only.",
        )

    clean_mime = (mime_type or "").lower().split(";")[0].strip()
    if not clean_mime:
        return False, "Document MIME type metadata is missing."

    allowed_mimes = EXTENSION_TO_MIMES[ext]
    if clean_mime not in allowed_mimes:
        return (
            False,
            f"File format mismatch: MIME type '{clean_mime}' does not match file extension '{ext}'.",
        )

    return True, clean_mime


def get_telegram_api_url() -> Optional[str]:
    """Returns the base Telegram Bot API URL."""
    token = get_bot_token()
    if not token:
        return None
    return f"https://api.telegram.org/bot{token}"


def get_user_language(chat_id: int) -> str:
    """Gets the user's preferred language, defaulting to English."""
    return USER_LANGUAGES.get(chat_id, "English")


# ---------------------------------------------------------------------------
# Telegram API Async Dispatcher
# ---------------------------------------------------------------------------
async def _telegram_post(method: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sends an asynchronous POST request to the Telegram Bot API."""
    base_url = get_telegram_api_url()
    if not base_url:
        return None

    # Defensive cleaning: never transmit reply_markup if None, empty, or not a dict
    cleaned_payload: Dict[str, Any] = {}
    for key, value in payload.items():
        if key == "reply_markup":
            if isinstance(value, dict) and value:
                cleaned_payload[key] = value
            # Intentionally omit reply_markup when None, empty, or invalid
        else:
            cleaned_payload[key] = value

    url = f"{base_url}/{method}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=cleaned_payload)
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"Telegram API {method} returned error: {data.get('description')}")
            return data
    except Exception as e:
        logger.warning(f"Telegram API request to {method} failed: {e}")
        return None


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[Union[Dict[str, Any], str]] = None,
) -> None:
    """
    Sends a formatted message to a Telegram chat, splitting safely if needed.
    Completely omits 'reply_markup' when none is provided, avoiding Telegram's
    'Bad Request: object expected as reply markup' error caused by null values.
    """
    # Normalize reply_markup if passed as a JSON string or dict
    resolved_markup: Optional[Dict[str, Any]] = None
    if isinstance(reply_markup, dict) and reply_markup:
        resolved_markup = reply_markup
    elif isinstance(reply_markup, str) and reply_markup.strip():
        try:
            parsed = json.loads(reply_markup)
            if isinstance(parsed, dict) and parsed:
                resolved_markup = parsed
        except Exception as e:
            logger.warning(f"Could not parse reply_markup string: {e}")

    # Chunking helper for Telegram 4096-character limit
    chunks = _split_message(text, max_len=TELEGRAM_MSG_MAX_LENGTH)
    for i, chunk in enumerate(chunks):
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        # Attach reply_markup only to the final chunk and only if valid dict object
        if i == len(chunks) - 1 and resolved_markup is not None:
            payload["reply_markup"] = resolved_markup

        await _telegram_post("sendMessage", payload)


async def send_chat_action(chat_id: int, action: str = "typing") -> None:
    """Sends a chat action notification (e.g. typing, upload_document)."""
    await _telegram_post("sendChatAction", {"chat_id": chat_id, "action": action})


async def answer_callback_query(callback_query_id: str, text: Optional[str] = None) -> None:
    """Answers a Telegram callback query from an inline keyboard button."""
    payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    await _telegram_post("answerCallbackQuery", payload)


def _split_message(text: str, max_len: int = TELEGRAM_MSG_MAX_LENGTH) -> List[str]:
    """Splits text safely into chunks at line breaks, preserving formatting."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk: List[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_len:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            # If a single line is absurdly long
            while len(line) > max_len:
                chunks.append(line[:max_len])
                line = line[max_len:]
        current_chunk.append(line)
        current_len += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks if chunks else [text]


# ---------------------------------------------------------------------------
# Keyboards & Navigation
# ---------------------------------------------------------------------------
def get_language_inline_keyboard() -> Dict[str, Any]:
    """Returns an inline keyboard with language options."""
    return {
        "inline_keyboard": [
            [
                {"text": "🇬🇧 English", "callback_data": "set_lang:English"},
                {"text": "🇮🇳 हिंदी (Hindi)", "callback_data": "set_lang:Hindi"},
                {"text": "🇮🇳 ಕನ್ನಡ (Kannada)", "callback_data": "set_lang:Kannada"},
            ]
        ]
    }


# ---------------------------------------------------------------------------
# Explanation Formatter (HTML Format)
# ---------------------------------------------------------------------------
def format_explanation_html(explanation: Dict[str, Any], language: str) -> str:
    """
    Formats the structured Gemini JSON response into an accessible,
    clean Telegram HTML message with emojis and medical disclaimers.
    """
    summary = html.escape(explanation.get("summary", "No summary available."))
    tests = explanation.get("tests", [])
    questions = explanation.get("questions_for_doctor", [])
    disclaimer = html.escape(explanation.get("disclaimer", DEFAULT_DISCLAIMER))

    # Detect non-lab document
    if len(tests) == 0 and len(questions) == 0:
        return (
            "ℹ️ <b>No Laboratory Results Found</b>\n\n"
            f"{summary}\n\n"
            "💡 <i>Tip: Please upload or paste a laboratory pathology report (e.g. Complete Blood Count, Lipid Profile, Thyroid Panel, Blood Sugar) containing test names, values, and reference ranges.</i>\n\n"
            f"⚠️ <i>{disclaimer}</i>"
        )

    # Status icon mapping
    status_icons = {
        "normal": "🟢",
        "high": "🔴",
        "low": "🔵",
        "unknown": "⚪",
    }

    parts = [
        "📋 <b>ReportSaathi — Medical Report Explanation</b>",
        f"🌐 <i>Language: {language}</i>\n",
        f"<b>Summary:</b>\n{summary}\n",
    ]

    if tests:
        parts.append(f"🔬 <b>Test Results Breakdown ({len(tests)}):</b>")
        for test in tests:
            name = html.escape(test.get("name", "Test"))
            value = html.escape(str(test.get("value", "N/A")))
            normal_range = html.escape(str(test.get("normal_range", "Not specified")))
            raw_status = (test.get("status") or "unknown").lower().strip()
            status_icon = status_icons.get(raw_status, "⚪")
            status_label = raw_status.capitalize()
            meaning = html.escape(test.get("meaning", ""))

            parts.append(
                f"{status_icon} <b>{name}</b>: <code>{value}</code>\n"
                f"   • Ref Range: {normal_range}\n"
                f"   • Status: <b>{status_label}</b>\n"
                f"   • Meaning: {meaning}\n"
            )

    if questions:
        parts.append("🩺 <b>Questions to Ask Your Doctor:</b>")
        for i, q in enumerate(questions, 1):
            parts.append(f"{i}. {html.escape(q)}")
        parts.append("")

    # Persistent Medical Disclaimer
    parts.append(f"⚠️ <b>Medical Disclaimer:</b>\n<i>{disclaimer}</i>")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# File Downloader (In-Memory Only)
# ---------------------------------------------------------------------------
async def _download_telegram_file_bytes(file_id: str) -> Optional[bytes]:
    """
    Fetches the file path from Telegram and downloads file bytes into memory.
    The file is never saved to disk.
    """
    token = get_bot_token()
    if not token:
        return None

    # 1. Get file path from Telegram
    file_info = await _telegram_post("getFile", {"file_id": file_id})
    if not file_info or not file_info.get("ok"):
        return None

    file_path = file_info.get("result", {}).get("file_path")
    if not file_path:
        return None

    # 2. Download bytes via HTTPS directly into memory
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(download_url)
            if resp.status_code == 200:
                return resp.content
            logger.warning(f"Failed to download Telegram file: HTTP {resp.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Error downloading file from Telegram: {e}")
        return None


# ---------------------------------------------------------------------------
# Core Update Processor
# ---------------------------------------------------------------------------
async def handle_telegram_update(update: Dict[str, Any]) -> None:
    """
    Main entry point for handling incoming Telegram updates (messages & callback queries).
    Supports commands, pasted text, document uploads, and photos.
    """
    try:
        # 1. Handle Inline Keyboard Callback Queries (Language selection)
        if "callback_query" in update:
            await _handle_callback_query(update["callback_query"])
            return

        # 2. Handle Message Updates
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]

        # Check for commands or text
        text = message.get("text", "").strip()

        if text.startswith("/start"):
            await _handle_start_command(chat_id)
            return

        if text.startswith("/help"):
            await _handle_help_command(chat_id)
            return

        if text.startswith("/language"):
            await _handle_language_command(chat_id)
            return

        # 3. Handle Direct Text Report Pasting
        if text:
            await _process_text_report(chat_id, text)
            return

        # 4. Handle Document Uploads (PDF, JPG, PNG)
        if "document" in message:
            await _handle_document_upload(chat_id, message["document"])
            return

        # 5. Handle Compressed Photo Uploads
        if "photo" in message:
            await _handle_photo_upload(chat_id, message["photo"])
            return

        # Unsupported message types (voice, video, sticker, etc.)
        await send_message(
            chat_id,
            "⚠️ <b>Unsupported content type</b>\n\n"
            "Please upload a medical report as a <b>PDF</b>, <b>JPG</b>, or <b>PNG</b> file, or paste the text directly into the chat.",
        )

    except Exception as e:
        logger.error(f"Error handling Telegram update: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------
async def _handle_start_command(chat_id: int) -> None:
    welcome_text = (
        "👋 <b>Welcome to ReportSaathi!</b>\n\n"
        "I help you understand clinical laboratory reports in clear, plain language.\n\n"
        "<b>How to use:</b>\n"
        "1. 📸 <b>Send a photo</b> of your lab report\n"
        "2. 📄 <b>Upload a PDF</b> or document (up to 5 MB)\n"
        "3. ✍️ <b>Paste text</b> directly into the chat\n\n"
        "🌐 <b>Select your preferred explanation language below:</b>"
    )
    await send_message(chat_id, welcome_text, reply_markup=get_language_inline_keyboard())


async def _handle_help_command(chat_id: int) -> None:
    help_text = (
        "ℹ️ <b>ReportSaathi — Help & Guidelines</b>\n\n"
        "<b>Commands:</b>\n"
        "• /start — Welcome message & language options\n"
        "• /language — Change explanation language (English, Hindi, Kannada)\n"
        "• /help — Show this help message\n\n"
        "<b>Supported Formats:</b>\n"
        "• Images: JPG, JPEG, PNG\n"
        "• Documents: PDF\n"
        "• File limit: 5 MB max\n\n"
        "<b>Privacy Guarantee:</b>\n"
        "All documents and texts are processed strictly in-memory during analysis. No patient files or personal medical reports are permanently stored.\n\n"
        "⚠️ <b>Educational Notice:</b>\n"
        "ReportSaathi is an educational health-literacy assistant, not a doctor. It does not provide medical diagnoses or prescriptions. Always consult a healthcare professional."
    )
    await send_message(chat_id, help_text)


async def _handle_language_command(chat_id: int) -> None:
    current_lang = get_user_language(chat_id)
    text = (
        f"🌐 <b>Language Settings</b>\n\n"
        f"Current language: <b>{current_lang}</b>\n\n"
        "Choose your preferred explanation language:"
    )
    await send_message(chat_id, text, reply_markup=get_language_inline_keyboard())


async def _handle_callback_query(callback: Dict[str, Any]) -> None:
    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]

    if data.startswith("set_lang:"):
        selected_lang = data.split(":", 1)[1]
        if selected_lang in ("English", "Hindi", "Kannada"):
            USER_LANGUAGES[chat_id] = selected_lang
            await answer_callback_query(
                callback_id,
                text=f"Language set to {selected_lang}",
            )
            confirm_msg = (
                f"✅ Explanation language updated to <b>{selected_lang}</b>.\n\n"
                "You can now send a lab report photo, PDF, or paste report text to begin analysis."
            )
            await send_message(chat_id, confirm_msg)


# ---------------------------------------------------------------------------
# Message & File Processing Pipeline
# ---------------------------------------------------------------------------
async def _process_text_report(chat_id: int, raw_text: str) -> None:
    """Processes pasted report text, queries Gemini, and sends back explanation."""
    lang = get_user_language(chat_id)
    await send_chat_action(chat_id, "typing")

    await send_message(
        chat_id,
        "⏳ <b>Analyzing your report with AI...</b>\n<i>Please wait a few moments while we review your measurements.</i>"
    )

    try:
        # Non-blocking: execute synchronous Gemini explainer in worker thread
        explanation = await asyncio.to_thread(explain_report, raw_text, language=lang)

        # Log anonymous usage to Supabase (source='telegram')
        tests = explanation.get("tests", []) if isinstance(explanation, dict) else []
        abnormal_count = sum(
            1 for t in tests if isinstance(t, dict) and str(t.get("status", "")).strip().lower() in ("high", "low")
        )
        await asyncio.to_thread(
            log_usage,
            source="telegram",
            language=lang,
            tests_count=len(tests),
            abnormal_count=abnormal_count,
        )

        formatted_html = format_explanation_html(explanation, lang)
        await send_message(chat_id, formatted_html)

    except (AIConfigurationError, AIModelUnavailableError, AIQuotaExceededError, AIServiceError, AIResponseParseError) as aie:
        logger.warning(f"AI error during Telegram text explanation: {aie}")
        await send_message(
            chat_id,
            "⚠️ <b>Service Temporarily Busy</b>\n\n"
            "Our medical explanation service is experiencing high demand. Please try sending your report again in a few moments."
        )
    except Exception as e:
        logger.error(f"Unexpected error processing text report for Telegram: {e}")
        await send_message(
            chat_id,
            "❌ <b>Error Analyzing Report</b>\n\n"
            "An error occurred while analyzing the text. Please check that the input contains legible test data and try again."
        )


async def _handle_document_upload(chat_id: int, document: Dict[str, Any]) -> None:
    """Validates and processes uploaded document (PDF, JPG, PNG)."""
    file_id = document.get("file_id")
    if not file_id:
        await send_message(
            chat_id,
            "❌ <b>Invalid File</b>\n\nTelegram did not provide a valid file ID for this document. Please try re-uploading.",
        )
        return

    file_name = document.get("file_name")
    file_size = document.get("file_size", 0)
    mime_type = document.get("mime_type")

    # 1. Enforce 5 MB file size limit before downloading
    if file_size > MAX_FILE_SIZE_BYTES:
        await send_message(
            chat_id,
            f"⚠️ <b>File size exceeds limit</b>\n\n"
            f"Your document ({round(file_size / (1024 * 1024), 2)} MB) exceeds the 5 MB limit. Please upload a smaller file.",
        )
        return

    # 2. Validate format extension and MIME type together
    is_valid, validation_result = validate_telegram_file_metadata(file_name, mime_type)
    if not is_valid:
        await send_message(
            chat_id,
            f"⚠️ <b>Invalid document format</b>\n\n{html.escape(validation_result)}",
        )
        return

    # validation_result holds the validated clean MIME type
    await _process_in_memory_file(chat_id, file_id, file_name or "document", validation_result)


async def _handle_photo_upload(chat_id: int, photo_list: List[Dict[str, Any]]) -> None:
    """Selects the highest resolution photo and processes it."""
    if not photo_list:
        return

    # Telegram sorts photos by size ascending; grab highest resolution
    highest_res = photo_list[-1]
    file_id = highest_res.get("file_id")
    file_size = highest_res.get("file_size", 0)

    if not file_id:
        await send_message(
            chat_id,
            "❌ <b>Invalid Photo</b>\n\nTelegram did not provide a valid file ID for this photo. Please try re-uploading.",
        )
        return

    # 1. Enforce 5 MB limit
    if file_size > MAX_FILE_SIZE_BYTES:
        await send_message(
            chat_id,
            "⚠️ <b>Image exceeds 5 MB limit</b>\n\nPlease compress or take a lower resolution photo and try again.",
        )
        return

    await _process_in_memory_file(chat_id, file_id, "photo.jpg", "image/jpeg")


async def _process_in_memory_file(
    chat_id: int, file_id: str, file_name: str, mime_hint: str
) -> None:
    """Downloads file strictly in-memory, extracts text with OCR, and explains via Gemini."""
    lang = get_user_language(chat_id)
    await send_chat_action(chat_id, "upload_document")

    await send_message(
        chat_id,
        f"📄 <b>Received document:</b> <code>{html.escape(file_name)}</code>\n\n"
        "⏳ <i>Downloading and scanning text with OCR in-memory...</i>"
    )

    # Download bytes into memory
    file_bytes = await _download_telegram_file_bytes(file_id)
    if not file_bytes:
        await send_message(
            chat_id,
            "❌ <b>Download Failed</b>\n\nCould not retrieve file from Telegram. Please try uploading again."
        )
        return

    # Validate binary signature
    try:
        detected_mime = validate_file_signature(file_bytes)
    except ValueError as ve:
        await send_message(
            chat_id,
            f"⚠️ <b>Invalid file header</b>\n\n{html.escape(str(ve))}"
        )
        return

    # Extract text with OCR (run in threadpool to prevent blocking)
    try:
        extracted_text = await asyncio.to_thread(extract_text, file_bytes, detected_mime)
    except TesseractUnavailableError as tue:
        logger.error(f"OCR error on Telegram upload: {tue}")
        await send_message(
            chat_id,
            "⚠️ <b>OCR Service Unavailable</b>\n\nOur optical character recognition service is temporarily unavailable. Please try pasting the text directly."
        )
        return
    except Exception as e:
        logger.error(f"OCR extraction failed on Telegram file: {e}")
        await send_message(
            chat_id,
            "❌ <b>Text Extraction Failed</b>\n\nCould not extract text from the document. Please ensure the document is clear, flat, and legible."
        )
        return

    if not extracted_text or not extracted_text.strip():
        await send_message(
            chat_id,
            "⚠️ <b>No readable text found</b>\n\nCould not detect any text in the document. Please ensure the photo is well-lit and sharp, or paste the text directly."
        )
        return

    # Explain extracted text via Gemini
    await send_chat_action(chat_id, "typing")
    await _process_text_report(chat_id, extracted_text)


# ---------------------------------------------------------------------------
# Lifespan Integration (Webhook & Polling Modes)
# ---------------------------------------------------------------------------
async def init_telegram_bot() -> None:
    """
    Initializes Telegram Bot during FastAPI application startup.
    - If TELEGRAM_BOT_TOKEN is not configured or placeholder: skips gracefully.
    - If WEBHOOK_URL or RENDER_EXTERNAL_URL is set: registers Webhook.
    - Otherwise (local dev): starts background long polling.
    """
    token = get_bot_token()
    if not token:
        logger.info("Telegram Bot token is not configured or is a placeholder. Telegram Bot integration disabled.")
        return

    webhook_base = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
    force_polling = os.getenv("TELEGRAM_POLLING", "false").lower() in ("true", "1", "yes")

    if webhook_base and not force_polling:
        # ── Webhook Mode (Production on Render) ──
        webhook_url = f"{webhook_base.rstrip('/')}/telegram/webhook"
        secret_token = get_secret_token()
        logger.info(f"Registering Telegram webhook at: {webhook_url}")

        res = await _telegram_post(
            "setWebhook",
            {
                "url": webhook_url,
                "secret_token": secret_token,
                "drop_pending_updates": False,
            },
        )
        if res and res.get("ok"):
            logger.info("✅ Telegram Bot webhook registered successfully.")
        else:
            logger.warning(f"Failed to register Telegram webhook: {res}")
    else:
        # ── Long Polling Mode (Local Development) ──
        # Clear any existing webhook so polling can receive updates
        await _telegram_post("deleteWebhook", {"drop_pending_updates": False})
        logger.info("Starting Telegram Bot in Long Polling mode for local development...")
        global _polling_task, _bot_is_running
        _bot_is_running = True
        _polling_task = asyncio.create_task(_run_polling_loop())


async def shutdown_telegram_bot() -> None:
    """Cleans up Telegram bot background tasks on application shutdown."""
    global _bot_is_running, _polling_task
    _bot_is_running = False
    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        logger.info("Telegram Bot polling task stopped.")

    if ACTIVE_BACKGROUND_TASKS:
        logger.info(f"Shutting down {len(ACTIVE_BACKGROUND_TASKS)} active Telegram background tasks...")
        pending = [t for t in ACTIVE_BACKGROUND_TASKS if not t.done()]
        if pending:
            done, still_pending = await asyncio.wait(pending, timeout=2.0)
            for t in still_pending:
                t.cancel()
            if still_pending:
                await asyncio.gather(*still_pending, return_exceptions=True)
        ACTIVE_BACKGROUND_TASKS.clear()
        logger.info("All Telegram background tasks shut down.")


async def _run_polling_loop() -> None:
    """Background long-polling loop for local development without webhooks."""
    offset = 0
    logger.info("Telegram Bot polling loop active.")
    while _bot_is_running:
        try:
            base_url = get_telegram_api_url()
            if not base_url:
                break

            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.post(
                    f"{base_url}/getUpdates",
                    json={"offset": offset, "timeout": 25, "limit": 20},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for update in updates:
                            update_id = update.get("update_id", 0)
                            offset = max(offset, update_id + 1)
                            # Handle each update asynchronously with exception tracking
                            track_background_task(handle_telegram_update(update))
                elif resp.status_code == 409:
                    logger.warning("Conflict: Telegram webhook is active. Disabling polling.")
                    break
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Error in Telegram polling loop: {e}")
            await asyncio.sleep(4.0)

        await asyncio.sleep(0.5)
