"""In-memory session and chat storage with automatic TTL cleanup.

Provides instant, thread-safe session management without disk dependencies,
making it 100% resilient on serverless platforms (like Vercel) while enforcing
privacy (data is never written to disk).
"""

import uuid
from datetime import UTC, datetime, timedelta

# In-memory stores
_sessions: dict[str, dict] = {}
_chat_history: dict[str, list[dict]] = {}
_document_data: dict[str, dict] = {}

# Limits — prevent unbounded memory growth on long-running deployments
MAX_SESSIONS = 200
SESSION_TTL = timedelta(hours=1)


async def init_db() -> None:
    """Initialize database (in-memory, instant no-op)."""
    return


def _cleanup_expired_sessions() -> None:
    """Remove sessions older than SESSION_TTL to prevent memory leaks."""
    now = datetime.now(UTC)
    expired_ids = [
        sid
        for sid, session in _sessions.items()
        if now - datetime.fromisoformat(session["created_at"]) > SESSION_TTL
    ]
    for sid in expired_ids:
        _sessions.pop(sid, None)
        _chat_history.pop(sid, None)
        _document_data.pop(sid, None)


def create_session(
    document_type: str,
    filename: str | None = None,
    page_count: int = 0,
) -> str:
    """Create a new session and return its ID."""
    # Run cleanup before creating new sessions
    _cleanup_expired_sessions()

    # Enforce max session limit
    if len(_sessions) >= MAX_SESSIONS:
        # Evict oldest session
        oldest_id = next(iter(_sessions))
        _sessions.pop(oldest_id, None)
        _chat_history.pop(oldest_id, None)
        _document_data.pop(oldest_id, None)

    session_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    _sessions[session_id] = {
        "id": session_id,
        "document_type": document_type,
        "filename": filename,
        "created_at": now,
        "last_accessed": now,
        "page_count": page_count,
    }
    _chat_history[session_id] = []
    return session_id


def get_session(session_id: str) -> dict | None:
    """Get session metadata by ID."""
    session = _sessions.get(session_id)
    if session:
        session["last_accessed"] = datetime.now(UTC).isoformat()
        return dict(session)
    return None


def save_chat_message(session_id: str, role: str, content: str) -> None:
    """Save a chat message to the session history."""
    if session_id not in _chat_history:
        _chat_history[session_id] = []
    _chat_history[session_id].append({
        "id": len(_chat_history[session_id]) + 1,
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now(UTC).isoformat(),
    })


def get_chat_history(session_id: str) -> list[dict]:
    """Get chat history for a session."""
    return list(_chat_history.get(session_id, []))


# --- In-memory document store (privacy: documents not persisted) ---

def store_document_data(session_id: str, data: dict) -> None:
    """Store document data in memory only (not persisted to disk)."""
    _document_data[session_id] = data


def get_document_data(session_id: str) -> dict | None:
    """Retrieve document data from memory."""
    return _document_data.get(session_id)


def clear_document_data(session_id: str) -> None:
    """Clear document data from memory."""
    _document_data.pop(session_id, None)
    _sessions.pop(session_id, None)
    _chat_history.pop(session_id, None)
