import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chroma_service import collection, search_chunks
from app.services.embedding_service import model
from app.services.llm_service import generate_answer
from app.services.memory_service import add_message, clear_history, get_history

logger = logging.getLogger(__name__)

router = APIRouter()

NO_ANSWER_MSG = "I could not find that information in the uploaded notes."
HISTORY_CONTEXT_TURNS = 3  # How many recent user turns to include in search query


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------


@router.get("/stats")
def stats():
    """Return the total number of stored chunks."""
    return {"total_chunks": collection.count()}


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "running", "chunks": collection.count()}


@router.post("/reset-chat")
def reset_chat():
    """Clear the conversation history."""
    clear_history()
    return {"message": "Chat history cleared"}


# ---------------------------------------------------------------------------
# Query endpoint
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str


@router.post("/query")
async def query_notes(request: QueryRequest):
    """
    Accept a question, retrieve relevant chunks from ChromaDB,
    and return an LLM-generated answer grounded in those chunks.
    """
    try:
        history = get_history()

        # Build a richer search query by appending recent context
        recent_user_questions = [
            msg["content"]
            for msg in history
            if msg["role"] == "user"
        ][-HISTORY_CONTEXT_TURNS:]

        search_query = " ".join(recent_user_questions + [request.question])

        question_embedding = model.encode(search_query).tolist()
        results = search_chunks(question_embedding)

        documents = results.get("documents", [[]])[0] if results else []
        metadatas = results.get("metadatas", [[]])[0] if results else []
        distances = results.get("distances", [[]])[0] if results else []

        # No chunks found — return early without calling the LLM
        if not documents:
            answer = NO_ANSWER_MSG
            add_message("user", request.question)
            add_message("assistant", answer)
            return {
                "question": request.question,
                "answer": answer,
                "sources": [],
            }

        logger.debug("Question: %s", request.question)
        logger.debug(
            "Retrieved %d chunks (top distance: %.4f)",
            len(documents),
            distances[0] if distances else -1,
        )

        start = time.time()
        answer = generate_answer(
            question=request.question,
            retrieved_chunks=documents,
            chat_history=history,
        )
        logger.info("LLM response time: %.2f sec", time.time() - start)

        add_message("user", request.question)
        add_message("assistant", answer)

        sources = list({meta.get("source", "N/A") for meta in metadatas})
        if answer.strip() == NO_ANSWER_MSG:
            sources = []

        return {
            "question": request.question,
            "answer": answer,
            "sources": sources,
        }

    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc