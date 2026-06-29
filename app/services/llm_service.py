from ollama import chat

def generate_answer(
    question: str,
    retrieved_chunks: list[str],
    chat_history: list[dict],
) -> str:
    """
    Generate an answer from the LLM using retrieved context and conversation history.

    Args:
        question: The user's current question.
        retrieved_chunks: Relevant document chunks retrieved from ChromaDB.
        chat_history: List of previous messages as {"role": ..., "content": ...} dicts.

    Returns:
        The LLM's answer as a string.
    """
    context = "\n\n".join(chunk[:300] for chunk in retrieved_chunks)

    # Build structured conversation history for the system prompt
    history_lines = [
        f"{msg['role'].capitalize()}: {msg['content']}"
        for msg in chat_history
    ]
    history_text = "\n".join(history_lines) if history_lines else "None"

    system_prompt = (
        "You are an expert college study assistant.\n\n"
        "Rules:\n"
        "1. Answer only from the provided context.\n"
        "2. Explain concepts clearly.\n"
        "3. Use bullet points when useful.\n"
        "4. If examples are present in the context, include them.\n"
        "5. If the user asks for examples, search the provided context carefully "
        "before saying the information is unavailable.\n"
        "6. Use conversation history to understand follow-up questions.\n"
        "7. If the answer is not present in the context, say exactly: "
        '"I could not find that information in the uploaded notes."'
    )

    user_message = (
        f"Conversation History:\n{history_text}\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}"
    )

    response = chat(
        model="qwen2.5:3b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    return response["message"]["content"]