import logging
import os
import time
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.services.chunk_service import chunk_text
from app.services.chroma_service import store_chunks, list_documents
from app.services.embedding_service import generate_embeddings
from app.services.pdf_service import extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accept a PDF upload, extract its text, chunk it, embed it,
    and store everything in ChromaDB with an upload timestamp.
    """
    # Validate file type
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDF files are accepted.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Warn if already indexed (will be replaced)
    existing_docs = list_documents()
    already_exists = any(d["filename"] == file.filename for d in existing_docs)

    try:
        contents = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        upload_time = datetime.now(timezone.utc).isoformat()
        text = extract_text_from_pdf(file_path)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        store_chunks(chunks, embeddings, file.filename, upload_time)

        logger.info(
            "Uploaded '%s': %d chars, %d chunks", file.filename, len(text), len(chunks)
        )

        return {
            "message": "File uploaded and indexed successfully",
            "filename": file.filename,
            "characters": len(text),
            "total_chunks": len(chunks),
            "embedding_dimension": len(embeddings[0]) if embeddings else 0,
            "replaced_existing": already_exists,
            "upload_time": upload_time,
        }

    except ValueError as exc:
        # Raised by pdf_service for unextractable PDFs
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Upload failed for '%s'", file.filename)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

@router.post("/upload-multiple")
async def upload_multiple_pdfs(files: List[UploadFile] = File(...)):
    """
    Accept multiple PDF uploads, process each, and return a list of results.
    """
    results = []
    for file in files:
        try:
            result = await upload_pdf(file)
            results.append(result)
        except HTTPException as exc:
            results.append({"filename": file.filename, "error": exc.detail})
        except Exception as exc:
            results.append({"filename": file.filename, "error": str(exc)})
    return {"results": results}