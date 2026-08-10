"""
PDF text extraction service with tiered fallback for scanned/handwritten PDFs.

Extraction order per page:
  1. pypdf          — fast, text-based PDFs
  2. pdfplumber     — tables and complex layouts
  3. Tesseract OCR  — scanned/handwritten pages (binary installed via winget)
  4. Gemini Vision  — optional fallback when Tesseract also fails (needs GEMINI_API_KEY)
"""

import io
import logging
import os
import sys

from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

logger = logging.getLogger(__name__)

# ── Tesseract path (Windows) ───────────────────────────────────────────────────
_TESSERACT_WIN_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── Gemini (optional Tier 4) ───────────────────────────────────────────────────
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_MODEL   = "gemini-2.0-flash"       # update if quota changes
_GEMINI_PROMPT  = (
    "This is a scanned page from a student's study notes. "
    "Transcribe ALL the text you can see exactly as written, "
    "preserving structure, bullet points, and mathematical notation. "
    "Output only the transcribed text — no commentary, no explanations."
)


# ── Tier 2: pdfplumber ─────────────────────────────────────────────────────────

def _pdfplumber_page(pdf_path: str, page_num: int) -> str:
    """Extract text using pdfplumber; handles tables too. page_num is 1-indexed."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            if text and text.strip():
                return text.strip()
            tables = page.extract_tables()
            if tables:
                rows = []
                for table in tables:
                    for row in table:
                        rows.append(" | ".join(str(cell or "").strip() for cell in row))
                return "\n".join(rows)
    except ImportError:
        logger.debug("pdfplumber not installed — skipping.")
    except Exception as exc:
        logger.debug("pdfplumber failed on page %d: %s", page_num, exc)
    return ""


# ── Tier 3: Tesseract OCR ──────────────────────────────────────────────────────

def _tesseract_page(pdf_path: str, page_num: int) -> str:
    """
    Render a PDF page to a high-resolution image and run Tesseract OCR on it.
    Requires: pymupdf (fitz), pytesseract, Pillow, and the Tesseract binary.
    page_num is 1-indexed.
    """
    try:
        import fitz  # pymupdf
        import pytesseract
        from PIL import Image

        # Set Tesseract binary path explicitly on Windows
        if sys.platform == "win32" and os.path.exists(_TESSERACT_WIN_PATH):
            pytesseract.pytesseract.tesseract_cmd = _TESSERACT_WIN_PATH

        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]

        # 3× zoom → ~220 DPI — better accuracy for handwriting
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        doc.close()

        # PSM 6 = assume a single uniform block of text (good for notes pages)
        text = pytesseract.image_to_string(img, config="--psm 6")
        return text.strip()

    except ImportError as exc:
        logger.warning(
            "OCR dependency missing (%s). "
            "Run: pip install pymupdf pytesseract Pillow",
            exc,
        )
    except pytesseract.TesseractNotFoundError:
        logger.warning(
            "Tesseract binary not found. "
            "Install it with: winget install UB-Mannheim.TesseractOCR"
        )
    except Exception as exc:
        logger.warning("Tesseract OCR failed on page %d: %s", page_num, exc)

    return ""


# ── Tier 4: Gemini Vision (optional) ──────────────────────────────────────────

def _gemini_page(pdf_path: str, page_num: int) -> str:
    """
    Render a PDF page to an image and transcribe via Gemini Vision.
    Only called if Tesseract fails and GEMINI_API_KEY is set.
    Requires the google-genai package: pip install google-genai
    """
    if not _GEMINI_API_KEY:
        return ""

    try:
        import fitz  # pymupdf
        from google import genai
        from google.genai import types

        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()

        client = genai.Client(api_key=_GEMINI_API_KEY)
        response = client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                _GEMINI_PROMPT,
            ],
        )
        text = (response.text or "").strip()
        if text:
            logger.info("Page %d: transcribed via Gemini Vision (%d chars).", page_num, len(text))
        return text

    except ImportError as exc:
        logger.warning("google-genai not installed: %s", exc)
    except Exception as exc:
        logger.warning("Gemini Vision failed on page %d: %s", page_num, exc)

    return ""


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_text_from_pdf_with_pages(pdf_path: str) -> list[tuple[int, str]]:
    """
    Extract text from a PDF, returning (page_number, text) tuples (1-indexed).

    Tier 1 — pypdf        (text-based PDFs, instant)
    Tier 2 — pdfplumber   (tables / complex layouts)
    Tier 3 — Tesseract    (scanned/handwritten pages — primary OCR)
    Tier 4 — Gemini Vision (optional fallback if GEMINI_API_KEY is set)

    Raises:
        ValueError: If no text could be extracted from any page by any method.
    """
    reader = PdfReader(pdf_path)
    pages: list[tuple[int, str]] = []

    for i, pdf_page in enumerate(reader.pages, start=1):

        # Tier 1 — pypdf
        text = pdf_page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
            continue

        # Tier 2 — pdfplumber
        text = _pdfplumber_page(pdf_path, i)
        if text:
            logger.info("Page %d: extracted via pdfplumber.", i)
            pages.append((i, text))
            continue

        # Tier 3 — Tesseract OCR
        logger.debug("Page %d: trying Tesseract OCR.", i)
        text = _tesseract_page(pdf_path, i)
        if text:
            logger.info("Page %d: extracted via Tesseract OCR (%d chars).", i, len(text))
            pages.append((i, text))
            continue

        # Tier 4 — Gemini Vision (optional)
        if _GEMINI_API_KEY:
            logger.debug("Page %d: Tesseract failed — trying Gemini Vision.", i)
            text = _gemini_page(pdf_path, i)
            if text:
                pages.append((i, text))
                continue

        logger.warning("Page %d: no text could be extracted by any method.", i)

    if not pages:
        raise ValueError(
            "No extractable text found in this PDF. "
            "Ensure Tesseract is installed (winget install UB-Mannheim.TesseractOCR) "
            "for handwritten/scanned documents."
        )

    return pages


def extract_text_from_pdf(pdf_path: str) -> str:
    """Convenience wrapper — returns all pages joined as a single string."""
    pages = extract_text_from_pdf_with_pages(pdf_path)
    return "\n".join(text for _, text in pages)