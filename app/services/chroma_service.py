import chromadb

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(name="study_materials")


def store_chunks(chunks: list[str], embeddings: list[list[float]], filename: str) -> None:
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
    metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

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