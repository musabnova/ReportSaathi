"""
ReportSaathi - Backend Explainer Module
Explains medical laboratory reports in plain, everyday language using Gemini.

MEDICAL DISCLAIMER:
This module is strictly for educational and health-literacy purposes.
It does NOT provide medical diagnoses, treatment plans, or medicine/dosage recommendations.
Always consult a qualified healthcare professional regarding any medical results.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

# Robust environment variable loading: checks backend/.env first, then default locations
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

# Configure basic logging
logger = logging.getLogger(__name__)

# Supported natural languages
SUPPORTED_LANGUAGES = {
    "english": "English",
    "hindi": "Hindi",
    "kannada": "Kannada",
}

# Standard default educational disclaimer
DEFAULT_DISCLAIMER = "This is educational information, not a medical diagnosis."


# ---------------------------------------------------------------------------
# Custom Safe Exception Hierarchy
# Categorizes errors for safe caller handling without exposing internal secrets.
# ---------------------------------------------------------------------------
class AIConfigurationError(Exception):
    """Raised when API key or model configuration is missing or invalid."""
    pass


class AIQuotaExceededError(Exception):
    """Raised when the AI service rate limit or quota has been reached."""
    pass


class AIModelUnavailableError(Exception):
    """Raised when the configured Gemini model is unavailable, not found, or deprecated."""
    pass


class AIServiceError(Exception):
    """Raised when the Gemini API service returns a server or connectivity error."""
    pass


class AIResponseParseError(Exception):
    """Raised when Gemini output cannot be safely parsed into the required JSON schema."""
    pass


# ---------------------------------------------------------------------------
# Structured Output Models (Pydantic)
# These models define the exact JSON format Gemini is required to return.
# ---------------------------------------------------------------------------
class LabTestItem(BaseModel):
    name: str = Field(
        description="Name of the laboratory test, e.g., 'Hemoglobin', 'Fasting Blood Glucose'"
    )
    value: str = Field(
        description="Reported value with units exactly as in the report, e.g., '9.1 g/dL'"
    )
    normal_range: str = Field(
        description="Reference or normal range provided in the report, or 'Not specified' if absent"
    )
    status: Literal["normal", "high", "low", "unknown"] = Field(
        description="Comparison against reference range: 'normal', 'high', 'low', or 'unknown'"
    )
    meaning: str = Field(
        description="Simple, everyday non-diagnostic explanation of what this test measures and what this value means"
    )


class ReportExplanationSchema(BaseModel):
    summary: str = Field(
        description="Simple, friendly overview explaining the overall report in the requested language"
    )
    tests: List[LabTestItem] = Field(
        description="List of detected lab tests. Must be empty [] if input text is not a lab report"
    )
    questions_for_doctor: List[str] = Field(
        description="Helpful, non-diagnostic questions the patient can ask their doctor"
    )
    disclaimer: str = Field(
        description="Educational disclaimer explicitly stating this is educational information, not a medical diagnosis"
    )


# ---------------------------------------------------------------------------
# System Instruction for Gemini
# Enforces medical safety rules, plain-language persona, and structured response.
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """
You are ReportSaathi, a friendly, empathetic, and patient-first health-literacy assistant.
Your goal is to explain laboratory test reports in simple, plain everyday language so anyone can understand them.

STRICT MEDICAL SAFETY RULES (NON-NEGOTIABLE):
1. NEVER DIAGNOSE: Never claim or imply a medical diagnosis (e.g., do NOT say "You have anemia" or "The patient has diabetes"). Instead, state whether the test value is above, below, or within the lab's reference range, and describe what physiological process doctors monitor with this test in everyday words.
2. NEVER PRESCRIBE MEDICINES OR DOSAGES: Never suggest medications, supplements, home remedies, or treatment plans.
3. NEVER INVENT OR HALLUCINATE VALUES: Only extract test values and reference ranges that are explicitly in the text. If a reference range is missing, record normal_range as "Not specified" and status as "unknown".
4. PRESERVE ORIGINAL VALUES: Keep original test numbers and measurement units intact.
5. COMMUNICATE UNCERTAINTY: Emphasize that only a qualified physician can interpret lab tests in the context of clinical history and physical examination.

NON-MEDICAL TEXT DETECTION:
If the input text does NOT look like a medical lab report (e.g., random chat, receipts, code, general articles, non-medical text, or gibberish):
- Return an empty list for "tests": []
- Return an empty list for "questions_for_doctor": []
- In "summary", explain clearly and politely that the text does not contain a recognizable medical lab report, and request a clear lab report.

LANGUAGE SUPPORT:
- The user will specify a language (English, Hindi, or Kannada).
- Keep all JSON field names in English ("summary", "tests", "name", "value", "normal_range", "status", "meaning", "questions_for_doctor", "disclaimer").
- For Hindi: Translate "summary", "meaning", "questions_for_doctor", and "disclaimer" into clear, natural everyday Hindi (Devanagari script). Keep test names recognizable.
- For Kannada: Translate "summary", "meaning", "questions_for_doctor", and "disclaimer" into clear, natural everyday Kannada script. Keep test names recognizable.
- For English: Use clear, jargon-free English.

ALLOWED STATUS VALUES:
Every test must have "status" set strictly to one of:
- "normal"
- "high"
- "low"
- "unknown"
"""


def _get_gemini_client() -> genai.Client:
    """
    Initializes and returns the official Google GenAI Client.
    Reads GEMINI_API_KEY from environment variables.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    # Guard against missing or default placeholder key
    if not api_key or api_key.strip() == "" or api_key == "your_gemini_api_key_here":
        raise AIConfigurationError(
            "GEMINI_API_KEY is not configured. Please set a valid Gemini API key in backend/.env"
        )

    # Initialize client using the official google-genai SDK
    return genai.Client(api_key=api_key)


def _clean_json_text(raw_text: str) -> str:
    """
    Removes Markdown code block markers (```json ... ```) if Gemini includes them.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()


def _sanitize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures the parsed dictionary adheres strictly to the expected schema
    and allowed status values.
    """
    allowed_statuses = {"normal", "high", "low", "unknown"}

    summary = data.get("summary", "")
    tests_raw = data.get("tests", [])
    questions = data.get("questions_for_doctor", [])
    disclaimer = data.get("disclaimer") or DEFAULT_DISCLAIMER

    sanitized_tests = []
    if isinstance(tests_raw, list):
        for item in tests_raw:
            if isinstance(item, dict):
                status = str(item.get("status", "unknown")).lower().strip()
                if status not in allowed_statuses:
                    status = "unknown"

                sanitized_tests.append({
                    "name": str(item.get("name", "Unknown Test")).strip(),
                    "value": str(item.get("value", "")).strip(),
                    "normal_range": str(item.get("normal_range", "Not specified")).strip(),
                    "status": status,
                    "meaning": str(item.get("meaning", "")).strip(),
                })

    sanitized_questions = []
    if isinstance(questions, list):
        for q in questions:
            if isinstance(q, str) and q.strip():
                sanitized_questions.append(q.strip())

    return {
        "summary": summary,
        "tests": sanitized_tests,
        "questions_for_doctor": sanitized_questions,
        "disclaimer": disclaimer,
    }


def explain_report(text: str, language: str = "English") -> Dict[str, Any]:
    """
    Explains a medical lab report using Gemini and returns structured JSON.

    Args:
        text (str): The raw text extracted from the medical report.
        language (str): Target explanation language ("English", "Hindi", or "Kannada").

    Returns:
        Dict[str, Any]: Structured dictionary containing:
            - summary: Overview explanation
            - tests: List of individual test details with normal/high/low status
            - questions_for_doctor: Clarifying questions for patient-doctor discussion
            - disclaimer: Mandatory medical disclaimer

    Raises:
        AIConfigurationError: Missing or invalid API key / parameters.
        AIModelUnavailableError: Configured model not found or deprecated.
        AIQuotaExceededError: Rate limit or quota exhausted.
        AIServiceError: Transient upstream Gemini API errors.
        AIResponseParseError: Output could not be decoded as JSON.
    """
    # Validate and normalize language selection
    normalized_lang = SUPPORTED_LANGUAGES.get(language.strip().lower(), "English")

    # Guard against empty or blank input text
    if not text or not text.strip():
        return {
            "summary": "No medical report text was provided to analyze. Please provide report text or upload a document.",
            "tests": [],
            "questions_for_doctor": [],
            "disclaimer": DEFAULT_DISCLAIMER,
        }

    # Retrieve configured Gemini model name (default to active gemini-3.5-flash-lite)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Initialize SDK client
    client = _get_gemini_client()

    # User prompt combining instructions, target language, and report content
    prompt = f"""
Target Language: {normalized_lang}

Please analyze the following extracted text from a medical lab report and explain it.
Follow all safety rules and output STRICT JSON matching the schema.

Report Text:
\"\"\"
{text}
\"\"\"
"""

    # Generation configuration requesting structured JSON schema
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=ReportExplanationSchema,
        temperature=0.2,
        http_options=types.HttpOptions(timeout=30000),
    )

    # Attempt generation with retry on JSON parse failure
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            logger.info(f"Calling Gemini model '{model_name}' (attempt {attempt + 1}/2)...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            response_text = response.text
            if not response_text:
                raise AIResponseParseError("Received empty response from Gemini API.")

            cleaned_text = _clean_json_text(response_text)
            parsed_json = json.loads(cleaned_text)

            # Sanitize and validate fields
            return _sanitize_result(parsed_json)

        except json.JSONDecodeError as jde:
            last_error = jde
            logger.warning(f"JSON decode failed on attempt {attempt + 1}: {jde}. Retrying...")
            prompt += "\n\nNote: Your previous response was not valid JSON. Ensure your output is purely valid JSON."

        except ClientError as ce:
            # ClientError from google-genai SDK (4xx responses)
            msg = str(ce)
            code = getattr(ce, "code", None)
            logger.error(f"Gemini ClientError (code={code}): {msg}")

            if code == 404 or "NOT_FOUND" in msg or "no longer available" in msg:
                raise AIModelUnavailableError(
                    f"Configured model '{model_name}' is unavailable or no longer supported. "
                    "Please update GEMINI_MODEL in backend/.env (e.g. 'gemini-3.5-flash')."
                ) from ce
            elif code == 429 or "RESOURCE_EXHAUSTED" in msg:
                raise AIQuotaExceededError(
                    "Gemini API rate limit or quota exceeded. Please try again shortly."
                ) from ce
            elif code in (400, 401, 403) or "API_KEY" in msg:
                raise AIConfigurationError(
                    "Gemini API authentication failed. Please verify GEMINI_API_KEY in backend/.env."
                ) from ce
            else:
                raise AIServiceError(f"Gemini API client request failed.") from ce

        except ServerError as se:
            # ServerError from google-genai SDK (5xx responses)
            msg = str(se)
            logger.error(f"Gemini ServerError: {msg}")
            raise AIServiceError(
                "Gemini service is temporarily experiencing high load. Please try again shortly."
            ) from se

        except APIError as api_err:
            logger.error(f"Gemini APIError: {api_err}")
            raise AIServiceError("Gemini service communication error.") from api_err

        except (AIConfigurationError, AIModelUnavailableError, AIQuotaExceededError, AIServiceError):
            # Re-raise explicit classified errors
            raise

        except Exception as e:
            logger.error(f"Unexpected error while explaining report: {e}")
            raise AIServiceError("An unexpected error occurred while communicating with the AI service.") from e

    # If parsing failed after retry
    raise AIResponseParseError(
        f"Failed to parse Gemini response as valid JSON after retry: {last_error}"
    )
