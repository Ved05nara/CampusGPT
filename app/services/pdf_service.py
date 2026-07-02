from pypdf import PdfReader


def extract_text_from_pdf_with_pages(pdf_path: str) -> list[tuple[int, str]]:
    """
    Extract text from a PDF file, returning a list of (page_number, text) tuples.
    Page numbers are 1-indexed.

    Raises:
        ValueError: If no extractable text is found across all pages.
    """
    reader = PdfReader(pdf_path)
    pages: list[tuple[int, str]] = []

    for i, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text and page_text.strip():
            pages.append((i, page_text))

    if not pages:
        raise ValueError(
            "No extractable text found in the PDF. "
            "It may be a scanned image — consider using an OCR tool."
        )

    return pages


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Convenience wrapper — returns all pages as a single string.
    Kept for backward compatibility.
    """
    pages = extract_text_from_pdf_with_pages(pdf_path)
    return "\n".join(text for _, text in pages)