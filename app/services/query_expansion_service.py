"""
Query expansion service.

Uses the LLM (Groq) to generate 2 alternative phrasings of the user's question,
improving BM25 and vector recall by covering different terminology used in the notes.

Falls back to the original query only on any error, so retrieval always proceeds.
"""

import logging
import os

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
_MODEL = "llama-3.3-70b-versatile"

_EXPANSION_SYSTEM = (
    "You are a search query expansion assistant helping a student find information in their notes. "
    "Given a question, generate exactly 2 alternative search queries that cover the same topic "
    "using different keywords, synonyms, or phrasing that might appear in study notes. "
    "Return ONLY the 2 queries, one per line. No numbering, no explanations, no extra text."
)


def expand_query(question: str) -> list[str]:
    """
    Generate 2 alternative search phrasings for the given question.

    Returns:
        [original_question, expansion_1, expansion_2]
        Falls back to [original_question] on any error.
    """
    try:
        resp = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _EXPANSION_SYSTEM},
                {"role": "user", "content": question},
            ],
            max_tokens=80,
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or ""
        expansions = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        result = [question] + expansions[:2]
        logger.debug("Query expanded: %r → %r", question, result[1:])
        return result

    except Exception as exc:
        logger.warning("Query expansion failed (%s) — using original query only.", exc)
        return [question]
