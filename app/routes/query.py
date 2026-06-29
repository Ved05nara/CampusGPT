import json
import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.chroma_service import collection, search_chunks
from app.services.embedding_service import model as embed_model
from app.services.llm_service import (
    generate_answer,
    generate_general_overview,
    stream_answer,
    stream_general_overview,
    compute_confidence,
)
from app.services.memory_service import add_message, clear_history, get_history

logger = logging.getLogger(__name__)
router = APIRouter()

NO_ANSWER_MSG = "I could not find that information in the uploaded notes."

# ── Tuned thresholds ───────────────────────────────────────────────────────────
# all-MiniLM-L6-v2 L2 distances: <0.5 = very relevant, 0.5–0.8 = relevant,
# >0.8 = loosely related, >1.0 = likely off-topic.
# Keep only chunks below this distance; if none survive → fall back to general.
RELEVANCE_DISTANCE_THRESHOLD = 0.8

# How many recent user turns to blend into the search query for follow-ups
SEARCH_HISTORY_TURNS = 2


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_search_query(question: str, history: list[dict]) -> str:
    """
    Blend the last N user messages into the search query so that
    follow-up questions like "explain it further" retrieve the right chunks.
    """
    recent = [
        m["content"] for m in history if m["role"] == "user"
    ][-SEARCH_HISTORY_TURNS:]
    return " ".join(recent + [question])


def _retrieve(question: str, history: list[dict]) -> tuple[list, list, list]:
    """Embed question (with history context) and fetch top-k chunks from ChromaDB."""
    search_query = _build_search_query(question, history)
    embedding = embed_model.encode(search_query).tolist()
    results = search_chunks(embedding)
    docs  = results.get("documents", [[]])[0] if results else []
    metas = results.get("metadatas", [[]])[0] if results else []
    dists = results.get("distances", [[]])[0] if results else []
    return docs, metas, dists


def _filter_by_relevance(
    docs: list, metas: list, dists: list
) -> tuple[list, list, list]:
    """
    Drop any chunk whose L2 distance exceeds the threshold.
    This prevents off-topic chunks from polluting the LLM prompt.
    """
    filtered = [
        (d, m, dist)
        for d, m, dist in zip(docs, metas, dists)
        if dist <= RELEVANCE_DISTANCE_THRESHOLD
    ]
    if not filtered:
        return [], [], []
    docs_f, metas_f, dists_f = zip(*filtered)
    return list(docs_f), list(metas_f), list(dists_f)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ── Utility endpoints ──────────────────────────────────────────────────────────

@router.get("/stats")
def stats():
    return {"total_chunks": collection.count()}


@router.get("/health")
def health():
    return {"status": "running", "chunks": collection.count()}


@router.post("/reset-chat")
def reset_chat(session_id: str = "default"):
    clear_history(session_id)
    return {"message": "Chat history cleared", "session_id": session_id}


# ── Request model ──────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    session_id: str = Field(
        default="default", description="Session identifier for chat memory"
    )


# ── Non-streaming /query ───────────────────────────────────────────────────────

@router.post("/query")
async def query_notes(request: QueryRequest):
    """Non-streaming fallback. Prefer /query-stream for production."""
    try:
        history = get_history(request.session_id)
        docs, metas, dists = _retrieve(request.question, history)
        docs, metas, dists = _filter_by_relevance(docs, metas, dists)

        needs_general = not docs

        if needs_general:
            overview = generate_general_overview(request.question)
            answer = (
                "I couldn't find that information in your uploaded notes, "
                f"but here's a general overview:\n\n{overview}"
            )
            add_message(request.session_id, "user", request.question)
            add_message(request.session_id, "assistant", answer)
            return {
                "question": request.question,
                "answer": answer,
                "sources": [],
                "chunks_data": [],
                "confidence_score": 0.0,
                "answer_source": "general",
                "session_id": request.session_id,
            }

        start = time.time()
        answer = generate_answer(request.question, docs, history)
        logger.info("LLM response time: %.2f sec", time.time() - start)

        add_message(request.session_id, "user", request.question)
        add_message(request.session_id, "assistant", answer)

        confidence = compute_confidence(dists)
        sources = list({m.get("source", "N/A") for m in metas})
        chunks_data = [
            {"source": m.get("source", "N/A"), "text": d}
            for d, m in zip(docs, metas)
        ]

        if answer.strip() == NO_ANSWER_MSG:
            sources, confidence, chunks_data = [], 0.0, []

        return {
            "question": request.question,
            "answer": answer,
            "sources": sources,
            "chunks_data": chunks_data,
            "confidence_score": confidence,
            "answer_source": "notes",
            "session_id": request.session_id,
        }

    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


# ── Streaming /query-stream ────────────────────────────────────────────────────

@router.post("/query-stream")
async def query_notes_stream(request: QueryRequest):
    """
    SSE streaming endpoint. Yields tokens as they are generated by Groq.
    Final event: {"done": true, "confidence_score": X, "sources": [...], ...}
    """
    history = get_history(request.session_id)
    docs, metas, dists = _retrieve(request.question, history)
    docs, metas, dists = _filter_by_relevance(docs, metas, dists)

    needs_general = not docs

    def generate():
        full_answer = ""
        try:
            if needs_general:
                prefix = (
                    "I couldn't find that information in your uploaded notes, "
                    "but here's a general overview:\n\n"
                )
                full_answer += prefix
                yield _sse({"token": prefix})

                for tok in stream_general_overview(request.question):
                    full_answer += tok
                    yield _sse({"token": tok})

                sources, chunks_data, confidence = [], [], 0.0
                answer_source = "general"

            else:
                for tok in stream_answer(request.question, docs, history):
                    full_answer += tok
                    yield _sse({"token": tok})

                confidence = compute_confidence(dists)
                sources = list({m.get("source", "N/A") for m in metas})
                chunks_data = [
                    {"source": m.get("source", "N/A"), "text": d}
                    for d, m in zip(docs, metas)
                ]
                answer_source = "notes"

                if full_answer.strip() == NO_ANSWER_MSG:
                    sources, chunks_data, confidence = [], [], 0.0

            add_message(request.session_id, "user", request.question)
            add_message(request.session_id, "assistant", full_answer)

            yield _sse({
                "done": True,
                "confidence_score": confidence,
                "sources": sources,
                "answer_source": answer_source,
                "chunks_data": chunks_data,
            })

        except Exception as exc:
            logger.exception("Stream generation failed")
            yield _sse({"error": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )