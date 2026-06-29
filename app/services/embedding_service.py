from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")


def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """
    Generate vector embeddings for a list of text chunks.

    Args:
        chunks: List of text strings to embed.

    Returns:
        List of embedding vectors (as Python float lists).
    """
    return model.encode(chunks).tolist()