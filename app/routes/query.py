import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.chroma_service import collection, search_chunks
from app.services.embedding_service import model
from app.services.llm_service import generate_answer, compute_confidence
from app.services.memory_service import add_message, clear_history, get_history

logger = logging.getLogger(__name__)

router = APIRouter()

NO_ANSWER_MSG = "I could not find that information in the uploaded notes."
HISTORY_CONTEXT_TURNS = 3  # How many recent user turns to include in search query
# L2 distance above this means the top chunk is too dissimilar — skip LLM entirely.
# ChromaDB L2 distances: 0 = perfect, ~1.2+ = unrelated topic.
RELEVANCE_DISTANCE_THRESHOLD = 1.2



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
def reset_chat(session_id: str = "default"):
    """Clear the conversation history for the given session."""
    clear_history(session_id)
    return {"message": "Chat history cleared", "session_id": session_id}


# ---------------------------------------------------------------------------
# Query endpoint
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str
    session_id: str = Field(default="default", description="Session identifier for chat memory")


@router.post("/query")
async def query_notes(request: QueryRequest):
    """
    Accept a question, retrieve relevant chunks from ChromaDB,
    and return an LLM-generated answer grounded in those chunks.
    Returns confidence_score (0-100) alongside the answer.
    """
    try:
        history = get_history(request.session_id)

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
            add_message(request.session_id, "user", request.question)
            add_message(request.session_id, "assistant", answer)
            return {
                "question": request.question,
                "answer": answer,
                "sources": [],
                "confidence_score": 0.0,
                "session_id": request.session_id,
            }

        # Relevance gate — if even the closest chunk is too far away, the question
        # is almost certainly outside the scope of the uploaded notes.
        top_distance = distances[0] if distances else float("inf")
        if top_distance > RELEVANCE_DISTANCE_THRESHOLD:
            logger.info(
                "Question out of scope (top distance: %.4f > threshold %.2f): %s",
                top_distance,
                RELEVANCE_DISTANCE_THRESHOLD,
                request.question,
            )
            answer = NO_ANSWER_MSG
            add_message(request.session_id, "user", request.question)
            add_message(request.session_id, "assistant", answer)
            return {
                "question": request.question,
                "answer": answer,
                "sources": [],
                "confidence_score": 0.0,
                "session_id": request.session_id,
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

        add_message(request.session_id, "user", request.question)
        add_message(request.session_id, "assistant", answer)

        confidence_score = compute_confidence(distances)

        sources = list({meta.get("source", "N/A") for meta in metadatas})
        if answer.strip() == NO_ANSWER_MSG:
            sources = []
            confidence_score = 0.0

        return {
            "question": request.question,
            "answer": answer,
            "sources": sources,
            "confidence_score": confidence_score,
            "session_id": request.session_id,
        }

    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc