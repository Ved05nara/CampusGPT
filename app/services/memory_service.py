"""
Session-based conversation history store.

Each session is identified by a session_id string.
History is stored in-memory and is suitable for single-process / local use.
For multi-process production use, replace with Redis or a database-backed store.
"""

from typing import TypedDict


class Message(TypedDict):
    role: str
    content: str


MAX_HISTORY_TURNS = 50  # Keep last N user+assistant pairs to bound context size

# session_id -> list of messages
_sessions: dict[str, list[Message]] = {}


def _get_session(session_id: str) -> list[Message]:
    """Return (creating if needed) the message list for a session."""
    if session_id not in _sessions:
        _sessions[session_id] = []
    return _sessions[session_id]


def add_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the session history, pruning oldest pairs if over limit."""
    history = _get_session(session_id)
    history.append({"role": role, "content": content})

    # Each "turn" = 2 messages (user + assistant)
    max_messages = MAX_HISTORY_TURNS * 2
    if len(history) > max_messages:
        del history[: len(history) - max_messages]


def get_history(session_id: str) -> list[Message]:
    """Return a copy of the conversation history for the given session."""
    return list(_get_session(session_id))


def clear_history(session_id: str) -> None:
    """Clear the conversation history for the given session."""
    if session_id in _sessions:
        _sessions[session_id].clear()


def list_sessions() -> list[str]:
    """Return all active session IDs."""
    return list(_sessions.keys())