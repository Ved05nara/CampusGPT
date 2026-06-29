from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.

    Args:
        pdf_path: Filesystem path to the PDF file.

    Returns:
        Concatenated text content from all pages.

    Raises:
        ValueError: If the PDF has no extractable text (e.g. scanned image PDF).
    """
    reader = PdfReader(pdf_path)
    pages_text: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            pages_text.append(page_text)

    if not pages_text:
        raise ValueError(
            "No extractable text found in the PDF. "
            "It may be a scanned image — consider using an OCR tool."
        )

    return "\n".join(pages_text)