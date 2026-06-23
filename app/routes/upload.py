from fastapi import APIRouter, UploadFile, File
from app.services.pdf_service import extract_text_from_pdf
import os
from app.services.chunk_service import chunk_text
from app.services.embedding_service import generate_embeddings
router = APIRouter()

UPLOAD_DIR = "uploads"

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    text = extract_text_from_pdf(file_path)
    chunks = chunk_text(text)
    embeddings = generate_embeddings(chunks)
    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "characters": len(text),
        "total_chunks": len(chunks),
        "first_chunk": chunks[0],
        "embedding_dimension": len(embeddings[0])
    }