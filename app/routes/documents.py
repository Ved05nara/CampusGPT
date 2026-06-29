import logging
import os

from fastapi import APIRouter, HTTPException

from app.services.chroma_service import list_documents, delete_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "uploads"


@router.get("")
def get_documents():
    """
    Return a list of all documents indexed in ChromaDB,
    including filename, chunk count, and upload time.
    """
    docs = list_documents()
    return {"documents": docs, "total": len(docs)}


@router.delete("/{filename}")
def remove_document(filename: str):
    """
    Delete all chunks for the given filename from ChromaDB
    and remove the file from disk if it exists.
    """
    chunks_deleted = delete_document(filename)

    if chunks_deleted == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{filename}' not found in the index.",
        )

    # Also remove from disk
    file_path = os.path.join(UPLOAD_DIR, filename)
    removed_from_disk = False
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            removed_from_disk = True
        except OSError as exc:
            logger.warning("Could not delete file '%s' from disk: %s", file_path, exc)

    logger.info("Deleted '%s': %d chunks removed", filename, chunks_deleted)

    return {
        "message": f"Document '{filename}' deleted successfully.",
        "chunks_deleted": chunks_deleted,
        "removed_from_disk": removed_from_disk,
    }
