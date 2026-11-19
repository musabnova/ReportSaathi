"""
ReportSaathi - Backend OCR Module
Extracts text from images (JPG, PNG) and PDF documents using Tesseract OCR and pypdf.

MEDICAL DISCLAIMER:
This module extracts raw text from medical lab reports for educational analysis.
It does NOT perform clinical interpretation, diagnosis, or treatment recommendations.
Uploaded files are processed entirely in-memory and are never permanently stored.
"""

import os
import io
import re
import logging
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError
import pytesseract
import pypdf
from pypdf.errors import PdfReadError

# Robust environment variable loading: checks backend/.env first
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom OCR Exceptions
# ---------------------------------------------------------------------------
class TesseractUnavailableError(Exception):
    """Raised when the Tesseract binary, PATH, or tessdata language packs are unavailable."""
    pass


# ---------------------------------------------------------------------------
# File Signature (Magic Bytes) Definitions
# Used to verify that files are genuine JPG, PNG, or PDF files.
# ---------------------------------------------------------------------------
JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PDF_SIGNATURE = b"%PDF"


def validate_file_signature(file_bytes: bytes) -> str:
    """
    Validates the actual binary signature (magic bytes) of the uploaded file.

    Returns:
        str: Detected MIME type ('image/jpeg', 'image/png', or 'application/pdf').

    Raises:
        ValueError: If the file header does not match allowed signatures.
    """
    if len(file_bytes) < 4:
        raise ValueError("File is too small to determine a valid file signature.")

    if file_bytes.startswith(JPEG_SIGNATURE):
        return "image/jpeg"
    elif file_bytes.startswith(PNG_SIGNATURE):
        return "image/png"
    elif file_bytes.startswith(PDF_SIGNATURE) or (b"%PDF-" in file_bytes[:1024]):
        return "application/pdf"
    else:
        raise ValueError(
            "Invalid file signature. Uploaded content does not match a valid JPG, PNG, or PDF format."
        )


# ---------------------------------------------------------------------------
# Windows Tesseract & Poppler Configuration
# ---------------------------------------------------------------------------
def _configure_ocr_binaries() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Reads optional TESSERACT_CMD, TESSDATA_PREFIX, and POPPLER_PATH environment variables.
    Configures pytesseract.tesseract_cmd and os.environ['TESSDATA_PREFIX'].

    Returns:
        Tuple of (tesseract_cmd, tessdata_prefix, poppler_path)
    """
    # 1. Configure Tesseract Executable
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    elif os.name == "nt":
        # Check standard default installation path on Windows if unset
        default_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(default_win_path):
            pytesseract.pytesseract.tesseract_cmd = default_win_path
            tesseract_cmd = default_win_path

    # 2. Configure TESSDATA_PREFIX (Directory holding eng.traineddata)
    tessdata_prefix = os.getenv("TESSDATA_PREFIX")
    if tessdata_prefix and os.path.exists(tessdata_prefix):
        os.environ["TESSDATA_PREFIX"] = tessdata_prefix
    elif os.name == "nt":
        # Check known user and installation candidate paths
        candidate_tessdata = [
            os.path.expanduser(r"~\tessract\tessdata"),
            os.path.expanduser(r"~\tesseract\tessdata"),
            r"C:\Program Files\Tesseract-OCR\tessdata",
        ]
        for candidate in candidate_tessdata:
            if os.path.exists(os.path.join(candidate, "eng.traineddata")):
                os.environ["TESSDATA_PREFIX"] = candidate
                tessdata_prefix = candidate
                break

    # 3. Configure Poppler Path for PDF rendering
    poppler_path = os.getenv("POPPLER_PATH")
    if poppler_path and not os.path.exists(poppler_path):
        logger.warning(f"POPPLER_PATH was set to '{poppler_path}', but directory does not exist.")
        poppler_path = None

    return tesseract_cmd, tessdata_prefix, poppler_path


# Run initial setup
_configure_ocr_binaries()


# ---------------------------------------------------------------------------
# Multilingual OCR Language Detection
# ---------------------------------------------------------------------------
TARGET_OCR_LANGUAGES = ["eng", "hin", "kan"]
DEFAULT_OCR_LANGUAGE = "eng"


def get_available_ocr_languages() -> str:
    """
    Detects installed Tesseract language packs using pytesseract.get_languages(config="").
    Builds a combined language string (e.g. 'eng+hin+kan') using available languages
    among eng, hin, and kan.
    Falls back gracefully to 'eng' if language detection fails or if only English is present.

    Returns:
        str: Plus-separated language string suitable for pytesseract (e.g., 'eng+hin+kan' or 'eng').
    """
    try:
        installed = pytesseract.get_languages(config="")
        if isinstance(installed, list):
            available = [lang for lang in TARGET_OCR_LANGUAGES if lang in installed]
            if available:
                return "+".join(available)
    except Exception as e:
        logger.warning(
            f"Could not query Tesseract installed languages: {e}. Falling back to '{DEFAULT_OCR_LANGUAGE}'."
        )

    return DEFAULT_OCR_LANGUAGE


# ---------------------------------------------------------------------------
# Text Cleaning Helper
# ---------------------------------------------------------------------------
def clean_text(raw_text: str) -> str:
    """
    Cleans OCR-extracted text by trimming leading/trailing whitespace per line
    and condensing excessive blank lines while preserving meaningful line breaks.

    Args:
        raw_text (str): Raw string extracted from image or PDF.

    Returns:
        str: Cleaned, structured text.
    """
    if not raw_text:
        return ""

    # Normalize carriage returns
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Split into lines and strip trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]

    # Condense 3 or more consecutive empty lines into at most 2 empty lines
    cleaned_lines = []
    empty_count = 0
    for line in lines:
        if not line:
            empty_count += 1
            if empty_count <= 2:
                cleaned_lines.append("")
        else:
            empty_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


# ---------------------------------------------------------------------------
# In-Memory Image Text Extraction
# ---------------------------------------------------------------------------
def _extract_from_image(file_bytes: bytes) -> str:
    """
    Extracts text from an image (JPG, PNG) entirely in memory using Pillow and pytesseract.
    Converts image to grayscale ('L') for improved contrast before running OCR.
    No image data is saved to disk.

    Args:
        file_bytes (bytes): Binary content of the image.

    Returns:
        str: Raw text extracted from image.

    Raises:
        ValueError: For unreadable image format.
        TesseractUnavailableError: If Tesseract or traineddata language files are missing.
        RuntimeError: For other OCR processing failures.
    """
    try:
        # Re-verify configuration before extraction
        _configure_ocr_binaries()

        # Open image from in-memory byte buffer (never written to disk)
        with Image.open(io.BytesIO(file_bytes)) as image:
            # Convert to grayscale for cleaner contrast
            grayscale_image = image.convert("L")
            # Detect available OCR languages (eng, hin, kan)
            ocr_lang = get_available_ocr_languages()
            # Run Tesseract OCR in-memory with multilingual support
            text = pytesseract.image_to_string(grayscale_image, lang=ocr_lang)
            return text

    except UnidentifiedImageError as e:
        logger.error("Failed to identify image format.")
        raise ValueError("Uploaded file is not a valid or readable image.") from e

    except pytesseract.TesseractNotFoundError as e:
        logger.error("Tesseract OCR binary not found on the system.")
        raise TesseractUnavailableError(
            "Tesseract OCR is not installed or not in PATH. Please verify TESSERACT_CMD in backend/.env."
        ) from e

    except pytesseract.TesseractError as te:
        err_msg = str(te)
        logger.error(f"Tesseract OCR engine error: {err_msg}")
        if "tessdata" in err_msg or "Failed loading language" in err_msg or "Error opening data file" in err_msg:
            raise TesseractUnavailableError(
                f"Tesseract language data missing or inaccessible: {err_msg}. "
                "Please ensure TESSDATA_PREFIX points to a directory containing 'eng.traineddata'."
            ) from te
        raise RuntimeError(f"OCR engine failure: {err_msg}") from te

    except Exception as e:
        logger.error(f"Image OCR extraction error: {e}")
        raise RuntimeError(f"Failed to extract text from image: {str(e)}") from e


# ---------------------------------------------------------------------------
# In-Memory PDF Text Extraction
# ---------------------------------------------------------------------------
def _extract_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from a PDF file entirely in memory:
    1. First attempts digital text extraction using pypdf.
    2. If digital text is empty (scanned PDF), renders pages in memory using
       pdf2image and performs Tesseract OCR on each page.
    No PDF or rendered page files are permanently stored on disk.

    Args:
        file_bytes (bytes): Binary content of the PDF.

    Returns:
        str: Extracted text from PDF.

    Raises:
        ValueError: Corrupted or invalid PDF.
        TesseractUnavailableError: If OCR is required and Tesseract is unavailable.
        RuntimeError: Processing failures.
    """
    # 1. Attempt digital text extraction with pypdf
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        extracted_pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(page_text.strip())

        digital_text = "\n\n".join(extracted_pages).strip()
        if digital_text:
            logger.info("Successfully extracted digital text directly from PDF.")
            return digital_text

    except PdfReadError as e:
        logger.error("Failed to read PDF structure.")
        raise ValueError("Uploaded file is corrupted or not a valid PDF.") from e
    except Exception as e:
        logger.warning(f"Digital PDF extraction failed, trying OCR fallback: {e}")

    # 2. Scanned PDF fallback using pdf2image + pytesseract
    logger.info("PDF has no selectable digital text. Falling back to in-memory OCR page-by-page...")
    try:
        from pdf2image import convert_from_bytes

        _, _, poppler_path = _configure_ocr_binaries()
        poppler_kwargs = {}
        if poppler_path:
            poppler_kwargs["poppler_path"] = poppler_path

        # Convert in-memory PDF bytes to in-memory PIL images
        pages = convert_from_bytes(file_bytes, **poppler_kwargs)
        ocr_pages = []
        ocr_lang = get_available_ocr_languages()

        for page_img in pages:
            gray_img = page_img.convert("L")
            page_ocr_text = pytesseract.image_to_string(gray_img, lang=ocr_lang)
            if page_ocr_text.strip():
                ocr_pages.append(page_ocr_text.strip())

        return "\n\n".join(ocr_pages).strip()

    except ImportError:
        raise RuntimeError(
            "pdf2image is required for scanned PDF OCR. Please install it with 'pip install pdf2image'."
        )
    except pytesseract.TesseractNotFoundError as e:
        raise TesseractUnavailableError(
            "Tesseract OCR is not installed or not in PATH. Please verify TESSERACT_CMD in backend/.env."
        ) from e
    except pytesseract.TesseractError as te:
        err_msg = str(te)
        logger.error(f"Tesseract engine error on PDF: {err_msg}")
        if "tessdata" in err_msg or "Failed loading language" in err_msg or "Error opening data file" in err_msg:
            raise TesseractUnavailableError(
                f"Tesseract language data missing: {err_msg}. Please set TESSDATA_PREFIX in backend/.env."
            ) from te
        raise RuntimeError(f"OCR engine failure on PDF: {err_msg}") from te
    except Exception as e:
        logger.error(f"Scanned PDF OCR failed: {e}")
        raise RuntimeError(
            f"Failed to perform OCR on scanned PDF: {str(e)}. "
            "Ensure Poppler is installed and POPPLER_PATH is configured in .env."
        ) from e


# ---------------------------------------------------------------------------
# Main Public Interface
# ---------------------------------------------------------------------------
def extract_text(file_bytes: bytes, content_type: Optional[str] = None) -> str:
    """
    Main function to extract cleaned text from uploaded medical report files.
    Validates binary file signature and executes all operations in-memory.

    Args:
        file_bytes (bytes): Binary contents of the uploaded file.
        content_type (Optional[str]): MIME type hint from the client.

    Returns:
        str: Cleaned, structured text extracted from the document.

    Raises:
        ValueError: For empty files, invalid signatures, or unreadable files.
        TesseractUnavailableError: If OCR binary or language data is missing.
        RuntimeError: For general OCR or processing failures.
    """
    # Guard against empty bytes
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Uploaded file is empty. Please provide a file with content.")

    # Validate actual file signature (magic bytes) to prevent spoofing
    detected_mime = validate_file_signature(file_bytes)

    # Re-verify against optional passed content_type if provided
    if content_type:
        normalized_hint = content_type.lower().split(";")[0].strip()
        if normalized_hint == "image/jpg":
            normalized_hint = "image/jpeg"
        if normalized_hint in ("image/jpeg", "image/png", "application/pdf"):
            if normalized_hint != detected_mime:
                logger.warning(
                    f"MIME hint '{normalized_hint}' differs from detected signature '{detected_mime}'. Using signature."
                )

    raw_text = ""

    # Route based on detected signature
    if detected_mime in ("image/jpeg", "image/png"):
        raw_text = _extract_from_image(file_bytes)
    elif detected_mime == "application/pdf":
        raw_text = _extract_from_pdf(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type: '{detected_mime}'. "
            "Only JPG, JPEG, PNG, and PDF files are supported."
        )

    # Clean and return structured text
    return clean_text(raw_text)
