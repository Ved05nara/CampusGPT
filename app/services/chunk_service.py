def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks, breaking only at word boundaries
    to avoid cutting words mid-token.

    Args:
        text: The full document text to split.
        chunk_size: Target maximum character length of each chunk.
        overlap: Number of characters to overlap between consecutive chunks.

    Returns:
        A list of text chunk strings.
    """
    words = text.split()
    chunks = []
    current_chars = 0
    current_words: list[str] = []

    for word in words:
        word_len = len(word) + 1  # +1 for the space

        if current_chars + word_len > chunk_size and current_words:
            chunks.append(" ".join(current_words))

            # Roll back by `overlap` characters worth of words
            overlap_words: list[str] = []
            overlap_chars = 0
            for w in reversed(current_words):
                if overlap_chars + len(w) + 1 > overlap:
                    break
                overlap_words.insert(0, w)
                overlap_chars += len(w) + 1

            current_words = overlap_words
            current_chars = overlap_chars

        current_words.append(word)
        current_chars += word_len

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks