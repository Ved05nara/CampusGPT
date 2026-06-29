"""
In-memory conversation history store.

Note: This is a single shared store suitable for single-user / local development.
For multi-user production use, replace with a per-session store keyed by session ID
(e.g. a dict mapping session_id -> list, or a database-backed solution).
"""

from typing import TypedDict


class Message(TypedDict):
    role: str
    content: str


_conversation_history: list[Message] = []

MAX_HISTORY_TURNS = 3  # Keep last N user+assistant pairs to bound context size


def add_message(role: str, content: str) -> None:
    """Append a message to conversation history, pruning if over the limit."""
    _conversation_history.append({"role": role, "content": content})

    # Each "turn" is 2 messages (user + assistant); prune oldest pairs
    max_messages = MAX_HISTORY_TURNS * 2
    if len(_conversation_history) > max_messages:
        del _conversation_history[: len(_conversation_history) - max_messages]


def get_history() -> list[Message]:
    """Return a copy of the current conversation history."""
    return list(_conversation_history)


def clear_history() -> None:
    """Clear the entire conversation history."""
    _conversation_history.clear()