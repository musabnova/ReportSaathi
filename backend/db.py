"""
ReportSaathi - Database Module
Handles lightweight anonymous usage logging to Supabase (PostgreSQL).

PRIVACY & MEDICAL SAFETY:
This module logs strictly aggregate, anonymous operational metrics.
It NEVER stores:
- Medical report text or OCR text
- Patient names or demographic data
- Individual test names or numerical results
- Uploaded files or binary documents

Only 4 non-identifying fields are logged:
- source (e.g., 'web', 'telegram')
- language (e.g., 'English', 'Hindi', 'Kannada')
- tests_count (integer)
- abnormal_count (integer)
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logger
logger = logging.getLogger(__name__)

# Explicitly load backend/.env relative to this file's location
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()


def _sanitize_supabase_url(url: Optional[str]) -> Optional[str]:
    """
    Sanitizes the Supabase URL by trimming whitespace, removing trailing slashes,
    and stripping accidental '/rest/v1' path suffixes so the Supabase client
    can append API paths correctly.
    """
    if not url:
        return None
    cleaned = url.strip()
    if "/rest/v1" in cleaned:
        cleaned = cleaned.split("/rest/v1")[0]
    return cleaned.rstrip("/")


# Cache client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Retrieves or initializes the Supabase client instance.

    Returns:
        Client: An active Supabase client instance, or None if credentials
                are missing or initialization fails.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    raw_url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    url = _sanitize_supabase_url(raw_url)

    if not url or not key:
        logger.warning(
            "Supabase credentials (SUPABASE_URL / SUPABASE_KEY) are not configured. "
            "Usage logging will be skipped."
        )
        return None

    try:
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        logger.warning(
            f"Failed to initialize Supabase client: {type(e).__name__}. "
            "Usage logging will be disabled."
        )
        return None


def log_usage(
    source: str,
    language: str,
    tests_count: int,
    abnormal_count: int,
) -> bool:
    """
    Logs anonymous usage statistics into the Supabase 'reports_log' table.

    Non-blocking / Resilient:
    If database insertion fails for any reason (network timeout, configuration,
    quota, or database downtime), this function safely catches the exception,
    logs an internal warning, and returns False without interrupting or failing
    the user's report explanation.

    Args:
        source: Entry point identifier (e.g., 'web', 'telegram').
        language: Language of the explanation ('English', 'Hindi', 'Kannada').
        tests_count: Total number of lab tests analyzed.
        abnormal_count: Number of lab tests flagged as 'high' or 'low'.

    Returns:
        bool: True if logged successfully, False otherwise.
    """
    try:
        client = get_supabase_client()
        if client is None:
            return False

        # Strictly anonymous metadata payload
        payload = {
            "source": str(source or "unknown").strip().lower(),
            "language": str(language or "English").strip(),
            "tests_count": max(0, int(tests_count)),
            "abnormal_count": max(0, int(abnormal_count)),
        }

        # Insert into public.reports_log table
        response = client.table("reports_log").insert(payload).execute()

        # Check if insert returned created data
        if response.data:
            logger.info(
                f"Usage logged successfully: source='{payload['source']}', "
                f"lang='{payload['language']}', tests={payload['tests_count']}, "
                f"abnormal={payload['abnormal_count']}"
            )
            return True
        else:
            logger.warning("Supabase insert completed but returned no record data.")
            return False

    except Exception as e:
        # Non-blocking: database failures must never break the user experience
        logger.warning(
            f"Non-fatal error logging usage to Supabase ({type(e).__name__}): {e}"
        )
        return False

