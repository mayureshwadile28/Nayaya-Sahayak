"""SQLite database for session metadata only. Documents are NOT persisted beyond the session."""

import sqlite3
import uuid
from datetime import datetime

from app.config import settings


def get_db_path():
    """Get the active SQLite DB path (writable location)."""
    return settings.db_path


# In-memory session store for document data (not persisted to disk)
_sessions: dict[str, dict] = {}
_db_initialized: bool = False


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create database tables if they do not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            document_type TEXT,
            filename TEXT,
            created_at TEXT NOT NULL,
            last_accessed TEXT NOT NULL,
            page_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()


def get_db_connection() -> sqlite3.Connection:
    """Get a SQLite connection for session metadata."""
    global _db_initialized  # noqa: PLW0603
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass  # WAL mode may fail on certain read-only/tmp mount configurations

    if not _db_initialized:
        _init_schema(conn)
        _db_initialized = True

    return conn


async def init_db() -> None:
    """Initialize the database schema."""
    conn = get_db_connection()
    try:
        _init_schema(conn)
    finally:
        conn.close()


def create_session(
    document_type: str,
    filename: str | None = None,
    page_count: int = 0,
) -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO sessions (id, document_type, filename, created_at, last_accessed, page_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, document_type, filename, now, now, page_count),
        )
        conn.commit()
    finally:
        conn.close()

    return session_id


def get_session(session_id: str) -> dict | None:
    """Get session metadata by ID."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row:
            # Update last accessed
            conn.execute(
                "UPDATE sessions SET last_accessed = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()
            return dict(row)
        return None
    finally:
        conn.close()


def save_chat_message(session_id: str, role: str, content: str) -> None:
    """Save a chat message to the session history."""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO chat_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_chat_history(session_id: str) -> list[dict]:
    """Get chat history for a session."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT role, content, timestamp FROM chat_history WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# --- In-memory document store (privacy: documents not persisted) ---

def store_document_data(session_id: str, data: dict) -> None:
    """Store document data in memory only (not persisted to disk)."""
    _sessions[session_id] = data


def get_document_data(session_id: str) -> dict | None:
    """Retrieve document data from memory."""
    return _sessions.get(session_id)


def clear_document_data(session_id: str) -> None:
    """Clear document data from memory."""
    _sessions.pop(session_id, None)
