"""
Sentence-aware text chunking service.

Splits text at sentence boundaries (., !, ?, blank lines) instead of
arbitrary word counts, so each chunk is a coherent set of complete sentences.
Overlap rolls back by whole sentences — never mid-sentence.
"""

import re
# from app.services.pdf_service import extract_text_from_pdf_with_pages
# pages = extract_text_from_pdf_with_pages("uploads/your_scanned_file.pdf")
# print(pages[0][1])  # first page raw text

def _split_sentences(text: str) -> list[str]:
    """
    Split text into individual sentences using punctuation and paragraph breaks.
    Handles common abbreviations by requiring the punctuation be followed by
    whitespace or end-of-string.
    """
    # Split on: sentence-ending punctuation followed by whitespace, or on
    # paragraph breaks (2+ newlines). Keep the delimiter attached to the left.
    parts = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
    return [s.strip() for s in parts if s.strip()]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks that respect sentence boundaries.

    Args:
        text:       The full document text to split.
        chunk_size: Target maximum character length of each chunk.
        overlap:    Character budget to re-include from the previous chunk
                    (rolled back by whole sentences).

    Returns:
        A list of text chunk strings.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0

    for sentence in sentences:
        s_len = len(sentence) + 1  # +1 for the joining space

        # If adding this sentence would overflow and we already have content,
        # flush the current chunk and roll back by `overlap` chars of sentences.
        if current_chars + s_len > chunk_size and current:
            chunks.append(" ".join(current))

            # Roll back: keep the last N sentences that fit within `overlap`
            overlap_sentences: list[str] = []
            overlap_chars = 0
            for s in reversed(current):
                if overlap_chars + len(s) + 1 > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_chars += len(s) + 1

            current = overlap_sentences
            current_chars = overlap_chars

        current.append(sentence)
        current_chars += s_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_text_with_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = 500,
    overlap: int = 100,
) -> tuple[list[str], list[int]]:
    """
    Sentence-aware chunking across a list of (page_number, text) tuples.
    Each page is chunked independently so page numbers are always accurate.

    Args:
        pages:      List of (1-indexed page number, page text) tuples.
        chunk_size: Target maximum character length per chunk.
        overlap:    Overlap budget in characters (whole sentences only).

    Returns:
        (chunks, page_numbers) — parallel lists of the same length.
    """
    chunks: list[str] = []
    page_numbers: list[int] = []

    for page_num, text in pages:
        if not text.strip():
            continue
        page_chunks = chunk_text(text, chunk_size, overlap)
        chunks.extend(page_chunks)
        page_numbers.extend([page_num] * len(page_chunks))

    return chunks, page_numbers