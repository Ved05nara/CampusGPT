"""
LLM service — powered by Groq API for fast inference (~500 tok/sec).
Requires GROQ_API_KEY in your .env file.
"""
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
MODEL = "llama-3.3-70b-versatile"

# ── System prompts ─────────────────────────────────────────────────────────────

_NOTES_SYSTEM = (
    "You are a study assistant that answers questions EXCLUSIVELY from the student notes provided.\n\n"
    "STRICT RULES — follow ALL of these without any exception:\n"
    "1. Answer ONLY using text found inside the [NOTES START] / [NOTES END] block.\n"
    "2. Do NOT use your training knowledge, general knowledge, or anything outside the notes block.\n"
    "3. If the answer is NOT present in the notes, respond with EXACTLY this sentence and nothing else:\n"
    '   "I could not find that information in the uploaded notes."\n'
    "4. Never guess, infer beyond the notes, or say phrases like 'generally', 'typically', or 'in most cases'.\n"
    "5. When the notes do contain the answer: be clear, use bullet points where helpful, and quote the notes.\n"
    "6. Use conversation history ONLY to resolve pronouns like 'it' or 'that' — never to add new knowledge.\n"
    "7. CRITICAL: The notes below are the ONLY source of truth. "
    "If the notes discuss topic X but the question is about topic Y, say you could not find it — "
    "do NOT answer topic Y from your training data.\n"
)

_GENERAL_SYSTEM = (
    "You are a knowledgeable tutor. A student asked a question that is NOT covered in their study notes.\n\n"
    "Your task:\n"
    "1. Give a clear, accurate, and concise general overview of the topic.\n"
    "2. Use bullet points where helpful.\n"
    "3. Keep it brief — 3 to 6 key points maximum.\n"
    "4. If you are not fully certain about a specific detail, say so honestly.\n"
    "5. Do NOT refer to any notes or documents — this is general knowledge only.\n"
)


# ── Message builders ───────────────────────────────────────────────────────────

def _notes_messages(
    question: str, chunks: list[str], history: list[dict]
) -> list[dict]:
    # No truncation — chunks are already capped at 500 chars by chunk_service
    context = "\n\n---\n\n".join(chunks)
    history_text = (
        "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history)
        or "None"
    )
    return [
        {"role": "system", "content": _NOTES_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Conversation History:\n{history_text}\n\n"
                f"[NOTES START]\n{context}\n[NOTES END]\n\n"
                f"Question: {question}"
            ),
        },
    ]


def _general_messages(question: str) -> list[dict]:
    return [
        {"role": "system", "content": _GENERAL_SYSTEM},
        {"role": "user", "content": f"Give a brief general overview of: {question}"},
    ]


# ── Non-streaming ──────────────────────────────────────────────────────────────

def generate_answer(
    question: str, retrieved_chunks: list[str], chat_history: list[dict]
) -> str:
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=_notes_messages(question, retrieved_chunks, chat_history),
    )
    return resp.choices[0].message.content


def generate_general_overview(question: str) -> str:
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=_general_messages(question),
    )
    return resp.choices[0].message.content


# ── Streaming generators ───────────────────────────────────────────────────────

def stream_answer(
    question: str, retrieved_chunks: list[str], chat_history: list[dict]
):
    """Sync generator — yields string tokens for a notes-grounded answer."""
    stream = _client.chat.completions.create(
        model=MODEL,
        messages=_notes_messages(question, retrieved_chunks, chat_history),
        stream=True,
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            yield token


def stream_general_overview(question: str):
    """Sync generator — yields string tokens for a general knowledge overview."""
    stream = _client.chat.completions.create(
        model=MODEL,
        messages=_general_messages(question),
        stream=True,
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            yield token


# ── Confidence scoring ─────────────────────────────────────────────────────────

def compute_confidence(distances: list[float]) -> float:
    """
    Map ChromaDB L2 distances to a 0–100 confidence score.
    Since we now only pass chunks with distance <= 0.8,
    scores will be more meaningful (0.8 → 60%, 0.0 → 100%).
    """
    if not distances:
        return 0.0
    avg = sum(distances) / len(distances)
    return round(max(0.0, 1.0 - avg / 2.0) * 100, 1)