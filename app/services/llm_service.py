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


def generate_answer(question, retrieved_chunks):

    context = "\n\n".join(retrieved_chunks)

    prompt = f"""
You are a helpful college study assistant.

Use ONLY the information provided in the context below.

If the answer is not present in the context, say:
"I could not find that information in the uploaded notes."

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

    response = model.generate_content(prompt)

    return response.text