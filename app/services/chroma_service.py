import chromadb

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(name="study_materials")


def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    filename: str,
    upload_time: str = "",
) -> None:
    """
    Store text chunks and their embeddings in ChromaDB.
    Deletes existing chunks for the same filename before inserting,
    preventing duplicates on re-upload.
    """
    # Remove any previously stored chunks for this file
    existing = collection.get(where={"source": filename})
    if existing and existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": filename, "chunk_index": i, "upload_time": upload_time}
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search_chunks(
    question_embedding: list[float], n_results: int = 5
) -> dict:
    """
    Query ChromaDB for the most relevant chunks given a question embedding.
    """
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    return results


def list_documents() -> list[dict]:
    """
    Return a list of all unique documents stored in ChromaDB,
    with their chunk count and upload time.
    """
    try:
        all_data = collection.get(include=["metadatas"])
        metadatas = all_data.get("metadatas") or []
    except Exception:
        return []

    docs: dict[str, dict] = {}
    for meta in metadatas:
        src = meta.get("source", "Unknown")
        if src not in docs:
            docs[src] = {
                "filename": src,
                "chunk_count": 0,
                "upload_time": meta.get("upload_time", ""),
            }
        docs[src]["chunk_count"] += 1

    return list(docs.values())


def delete_document(filename: str) -> int:
    """
    Delete all chunks associated with the given filename from ChromaDB.
    Returns the number of chunks deleted.
    """
    existing = collection.get(where={"source": filename})
    ids = existing.get("ids") or []
    if ids:
        collection.delete(ids=ids)
    return len(ids)