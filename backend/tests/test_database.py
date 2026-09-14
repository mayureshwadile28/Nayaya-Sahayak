"""Unit tests for in-memory session database, chat history, and TTL cleanup."""

from datetime import UTC, datetime, timedelta
import pytest

from app.models.database import (
    _sessions,
    _cleanup_expired_sessions,
    clear_document_data,
    create_session,
    get_chat_history,
    get_document_data,
    get_session,
    init_db,
    save_chat_message,
    store_document_data,
)


class TestDatabaseSessions:
    """Test session lifecycle and limits."""

    @pytest.mark.asyncio
    async def test_init_db(self) -> None:
        """init_db should complete without error."""
        await init_db()

    def test_create_and_get_session(self) -> None:
        """Session should be created with correct metadata and retrievable."""
        sid = create_session(document_type="rental", filename="lease.pdf", page_count=3)
        assert sid is not None

        session = get_session(sid)
        assert session is not None
        assert session["document_type"] == "rental"
        assert session["filename"] == "lease.pdf"
        assert session["page_count"] == 3
        assert "created_at" in session

    def test_get_nonexistent_session(self) -> None:
        """Querying a non-existent session should return None."""
        assert get_session("non-existent-uuid-12345") is None

    def test_save_and_retrieve_chat_history(self) -> None:
        """Chat messages should be appended and retrieved in order."""
        sid = create_session("employment")
        save_chat_message(sid, "user", "Can I resign during probation?")
        save_chat_message(sid, "assistant", "Yes, subject to the notice period clause.")

        history = get_chat_history(sid)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Can I resign during probation?"
        assert history[1]["role"] == "assistant"
        assert "notice period" in history[1]["content"]

    def test_document_data_store_and_clear(self) -> None:
        """Document text and data should be stored in memory and cleared on command."""
        sid = create_session("consumer")
        data = {"text": "Non-refundable product clause", "original_type": "consumer"}

        store_document_data(sid, data)
        retrieved = get_document_data(sid)
        assert retrieved == data

        clear_document_data(sid)
        assert get_document_data(sid) is None
        assert get_session(sid) is None
        assert get_chat_history(sid) == []

    def test_expired_session_cleanup(self) -> None:
        """Sessions older than TTL should be expired and removed by cleanup."""
        sid = create_session("rental")
        # Manually backdate created_at to 2 hours ago
        two_hours_ago = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        _sessions[sid]["created_at"] = two_hours_ago

        _cleanup_expired_sessions()
        assert get_session(sid) is None
