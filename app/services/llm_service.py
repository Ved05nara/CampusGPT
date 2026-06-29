from ollama import chat


def generate_answer(
    question: str,
    retrieved_chunks: list[str],
    chat_history: list[dict],
) -> str:
    """
    Generate an answer from the LLM using retrieved context and conversation history.
    Strictly grounded — will only answer from the provided notes context.

    Args:
        question: The user's current question.
        retrieved_chunks: Relevant document chunks retrieved from ChromaDB.
        chat_history: List of previous messages as {"role": ..., "content": ...} dicts.

    Returns:
        The LLM's answer as a string.
    """
    # Increased from 300 to 800 chars for richer context
    context = "\n\n".join(chunk[:800] for chunk in retrieved_chunks)

    # Build structured conversation history for the system prompt
    history_lines = [
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in chat_history
    ]
    history_text = "\n".join(history_lines) if history_lines else "None"

    system_prompt = (
        "You are a study assistant that answers questions EXCLUSIVELY from the student notes provided.\n\n"
        "STRICT RULES — follow ALL of these without any exception:\n"
        "1. Answer ONLY using text found inside the [NOTES START] / [NOTES END] block.\n"
        "2. Do NOT use your training knowledge, general knowledge, or anything outside the notes block.\n"
        "3. If the answer is NOT present in the notes, respond with EXACTLY this sentence and nothing else:\n"
        '   "I could not find that information in the uploaded notes."\n'
        "4. Never guess, infer beyond the notes, or say phrases like \'generally\', \'typically\', or \'in most cases\'.\n"
        "5. When the notes do contain the answer: be clear, use bullet points where helpful, and quote the notes.\n"
        "6. Use conversation history only to resolve pronouns like \'it\' or \'that\' — never to add new knowledge.\n"
    )

    user_message = (
        f"Conversation History:\n{history_text}\n\n"
        f"[NOTES START]\n{context}\n[NOTES END]\n\n"
        f"Question: {question}"
    )

    response = chat(
        model="qwen2.5:1.5b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return response["message"]["content"]


def compute_confidence(distances: list[float]) -> float:
    """
    Compute a confidence score (0–100) from ChromaDB L2 distances.

    ChromaDB L2 distances are in [0, ~4]. A distance of 0 means perfect match.
    We map this to a confidence percentage where lower distance = higher confidence.

    Args:
        distances: List of L2 distances from the top-k retrieved chunks.

    Returns:
        Confidence score as a float in [0, 100].
    """
    if not distances:
        return 0.0
    avg_distance = sum(distances) / len(distances)
    # Normalise: assume max meaningful L2 distance is 2.0
    confidence = max(0.0, 1.0 - avg_distance / 2.0) * 100
    return round(confidence, 1)