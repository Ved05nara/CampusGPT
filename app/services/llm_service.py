import os
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)


def _get_response_text(response):
    if hasattr(response, "text"):
        return response.text
    if isinstance(response, str):
        return response
    if hasattr(response, "result"):
        return getattr(response, "result")
    return str(response)


def generate_answer(
    question,
    retrieved_chunks,
    chat_history
):

    context = "\n\n".join(
        retrieved_chunks
    )

    history_text = ""

    for message in chat_history:
        history_text += (
            f"{message['role']}: "
            f"{message['content']}\n"
        )

    prompt = f"""
You are an expert college study assistant.

Rules:
1. Answer only from the provided context.
2. Explain concepts clearly.
3. Use bullet points when useful.
4. If examples are present in the context, include them.
5. If the user asks for examples, search the provided context carefully before saying the information is unavailable.
6. Use conversation history to understand follow-up questions.
7. If the answer is not present in the context, say:
   "I could not find that information in the uploaded notes."

Conversation History:
{history_text}

Context:
{context}

Question:
{question}
"""

    if hasattr(model, "generate_content"):
        response = model.generate_content(prompt)
        return _get_response_text(response)

    if hasattr(model, "generate_text"):
        response = model.generate_text(prompt)
        return _get_response_text(response)

    if hasattr(genai, "generate_text"):
        response = genai.generate_text(
            model="gemini-2.5-flash",
            prompt=prompt
        )
        return _get_response_text(response)

    if hasattr(model, "generate"):
        response = model.generate(prompt)
        return _get_response_text(response)

    raise RuntimeError(
        "No supported generation method is available on the Gemini model."
    )