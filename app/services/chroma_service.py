import chromadb

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(name="study_materials")


def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    filename: str,
    upload_time: str = "",
    subject: str = "",
    semester: str = "",
    department: str = "",
    page_numbers: list[int] | None = None,
) -> None:
    """
    Store text chunks and their embeddings in ChromaDB with rich metadata.
    Deletes existing chunks for the same filename before inserting,
    preventing duplicates on re-upload.

    Metadata stored per chunk:
        source, chunk_index, page_number, upload_time,
        subject, semester, department
    """
    existing = collection.get(where={"source": filename})
    if existing and existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]

    metadatas = [
        {
            "source": filename,
            "chunk_index": i,
            "page_number": (page_numbers[i] if page_numbers and i < len(page_numbers) else 0),
            "upload_time": upload_time,
            "subject": subject.strip().lower(),
            "semester": semester.strip().lower(),
            "department": department.strip().lower(),
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def _build_where(
    subject: str | None = None,
    semester: str | None = None,
    department: str | None = None,
    filename: str | None = None,
) -> dict | None:
    """
    Build a ChromaDB `where` filter from optional metadata fields.
    Combines multiple conditions with $and.
    Returns None if no filters are active (fetch all).
    """
    clauses = []

    if filename:
        clauses.append({"source": {"$eq": filename}})
    if subject:
        clauses.append({"subject": {"$eq": subject.strip().lower()}})
    if semester:
        clauses.append({"semester": {"$eq": semester.strip().lower()}})
    if department:
        clauses.append({"department": {"$eq": department.strip().lower()}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search_chunks(
    question_embedding: list[float],
    n_results: int = 5,
    subject: str | None = None,
    semester: str | None = None,
    department: str | None = None,
    filename: str | None = None,
) -> dict:
    """
    Query ChromaDB for the most relevant chunks given a question embedding.
    Optionally filter by subject, semester, department, or filename.
    """
    where = _build_where(subject, semester, department, filename)

    kwargs = dict(
        query_embeddings=[question_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where

    return collection.query(**kwargs)


def list_documents(
    subject: str | None = None,
    semester: str | None = None,
    department: str | None = None,
) -> list[dict]:
    """
    Return all unique documents stored in ChromaDB with their metadata.
    Optionally filter by subject, semester, or department.
    """
    try:
        where = _build_where(subject=subject, semester=semester, department=department)
        kwargs = {"include": ["metadatas"]}
        if where:
            kwargs["where"] = where
        all_data = collection.get(**kwargs)
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
                "subject": meta.get("subject", ""),
                "semester": meta.get("semester", ""),
                "department": meta.get("department", ""),
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