import logging
import os

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.services.chunk_service import chunk_text
from app.services.chroma_service import store_chunks
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
    and store everything in ChromaDB.
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

    try:
        contents = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        text = extract_text_from_pdf(file_path)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        store_chunks(chunks, embeddings, file.filename)

        logger.info(
            "Uploaded '%s': %d chars, %d chunks", file.filename, len(text), len(chunks)
        )

        return {
            "message": "File uploaded and indexed successfully",
            "filename": file.filename,
            "characters": len(text),
            "total_chunks": len(chunks),
            "embedding_dimension": len(embeddings[0]) if embeddings else 0,
        }

    except ValueError as exc:
        # Raised by pdf_service for unextractable PDFs
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Upload failed for '%s'", file.filename)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc