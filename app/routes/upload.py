import logging
import os
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Form, HTTPException, UploadFile, File

from app.services.chunk_service import chunk_text
from app.services.chroma_service import store_chunks, list_documents
from app.services.embedding_service import generate_embeddings
from app.services.pdf_service import extract_text_from_pdf_with_pages

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    subject: str = Form(default=""),
    semester: str = Form(default=""),
    department: str = Form(default=""),
):
    """
    Accept a PDF upload with optional metadata (subject, semester, department).
    Extracts text page-by-page, chunks it, embeds it, and stores in ChromaDB.
    """
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDF files are accepted.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    existing_docs = list_documents()
    already_exists = any(d["filename"] == file.filename for d in existing_docs)

    try:
        contents = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        upload_time = datetime.now(timezone.utc).isoformat()

        # Extract text with page number tracking
        pages = extract_text_from_pdf_with_pages(file_path)
        full_text = "\n".join(text for _, text in pages)

        # Build page_number lookup: for each chunk we'll track which page it came from
        chunks, page_numbers = chunk_text_with_pages(pages)

        embeddings = generate_embeddings(chunks)
        store_chunks(
            chunks=chunks,
            embeddings=embeddings,
            filename=file.filename,
            upload_time=upload_time,
            subject=subject,
            semester=semester,
            department=department,
            page_numbers=page_numbers,
        )

        logger.info(
            "Uploaded '%s' [subject=%s, semester=%s, dept=%s]: %d chars, %d chunks",
            file.filename, subject, semester, department, len(full_text), len(chunks),
        )

        return {
            "message": "File uploaded and indexed successfully",
            "filename": file.filename,
            "characters": len(full_text),
            "total_chunks": len(chunks),
            "embedding_dimension": len(embeddings[0]) if embeddings else 0,
            "replaced_existing": already_exists,
            "upload_time": upload_time,
            "subject": subject,
            "semester": semester,
            "department": department,
        }

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Upload failed for '%s'", file.filename)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc


def chunk_text_with_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = 500,
    overlap: int = 100,
) -> tuple[list[str], list[int]]:
    """
    Chunk a list of (page_number, text) tuples while tracking which page
    each chunk originated from.

    Returns:
        chunks: list of text strings
        page_numbers: list of page numbers parallel to chunks
    """
    chunks: list[str] = []
    page_numbers: list[int] = []

    for page_num, text in pages:
        if not text.strip():
            continue
        words = text.split()
        current_words: list[str] = []
        current_chars = 0

        for word in words:
            word_len = len(word) + 1
            if current_chars + word_len > chunk_size and current_words:
                chunks.append(" ".join(current_words))
                page_numbers.append(page_num)

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
            page_numbers.append(page_num)

    return chunks, page_numbers


@router.post("/upload-multiple")
async def upload_multiple_pdfs(
    files: List[UploadFile] = File(...),
    subject: str = Form(default=""),
    semester: str = Form(default=""),
    department: str = Form(default=""),
):
    """Accept multiple PDF uploads with shared metadata."""
    results = []
    for file in files:
        try:
            result = await upload_pdf(
                file=file,
                subject=subject,
                semester=semester,
                department=department,
            )
            results.append(result)
        except HTTPException as exc:
            results.append({"filename": file.filename, "error": exc.detail})
        except Exception as exc:
            results.append({"filename": file.filename, "error": str(exc)})
    return {"results": results}