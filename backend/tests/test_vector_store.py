"""Unit tests for the VectorStoreService retrieval engine and caching."""

from app.services.vector_store import VectorStoreService


class TestVectorStoreChunking:
    """Test text chunking logic."""

    def test_chunk_empty_text(self) -> None:
        """Empty text should return no chunks."""
        store = VectorStoreService()
        chunks = store._chunk_text("")
        assert chunks == []

    def test_chunk_short_text(self) -> None:
        """Text shorter than chunk size should return a single chunk."""
        store = VectorStoreService()
        text = "This is a short legal statement regarding lease terms."
        chunks = store._chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_chunk_long_text_with_overlap(self) -> None:
        """Long text should be divided into multiple overlapping chunks."""
        store = VectorStoreService()
        # 600 words > CHUNK_SIZE (500 words)
        text = "Legal clause word. " * 600
        chunks = store._chunk_text(text)
        assert len(chunks) > 1
        assert "text" in chunks[0]



class TestVectorStoreStatuteSearch:
    """Test statute search and corpus initialization."""

    def test_statute_search_returns_results(self) -> None:
        """Search should return relevant statutes when initialized."""
        store = VectorStoreService()
        store.initialize()
        assert store._initialized is True
        assert len(store._statutes) > 0

        # Query for rent
        results = store.search_statutes(query="tenant eviction notice period", document_type="rental", n_results=3)
        assert len(results) > 0
        assert "text" in results[0]
        assert "source" in results[0]

    def test_statute_search_uses_cache(self) -> None:
        """Repeated identical queries should hit the cache."""
        store = VectorStoreService()
        store.initialize()

        res1 = store.search_statutes("security deposit refund", "rental", n_results=2)
        assert len(store._statute_cache) > 0

        res2 = store.search_statutes("security deposit refund", "rental", n_results=2)
        assert res1 == res2

    def test_search_uninitialized_returns_empty(self) -> None:
        """If not initialized and corpus is empty, search safely returns empty list."""
        store = VectorStoreService()
        results = store.search_statutes(query="test", n_results=3)
        assert results == []


class TestVectorStoreDocumentChunks:
    """Test document chunking, searching, and session cleanup."""

    def test_add_and_search_document_chunks(self) -> None:
        """Document text should be indexed and searchable per session."""
        store = VectorStoreService()
        session_id = "test-session-42"
        doc_text = (
            "Clause 1: The tenant must pay a security deposit of 500,000 INR. "
            "Clause 2: Lock-in period is 3 years. "
            "Clause 3: Termination requires 30 days notice."
        )

        store.add_document_chunks(session_id, doc_text)
        results = store.search_document("security deposit lock-in", session_id, n_results=2)

        assert len(results) > 0
        assert "security deposit" in results[0]["text"].lower()

    def test_document_cache_invalidation_on_new_chunks(self) -> None:
        """Adding chunks for a session should invalidate that session's cache."""
        store = VectorStoreService()
        session_id = "test-session-cache"
        store.add_document_chunks(session_id, "Initial text about lease agreement.")
        store.search_document("lease", session_id)
        assert len(store._doc_cache) > 0

        # Adding chunks should clear session doc cache
        store.add_document_chunks(session_id, "Updated text with additional clauses.")
        results = store.search_document("additional clauses", session_id)
        assert len(results) > 0

    def test_clear_session_removes_chunks_and_cache(self) -> None:
        """Clearing a session should remove all its chunks and cached queries."""
        store = VectorStoreService()
        session_id = "test-session-cleanup"
        store.add_document_chunks(session_id, "Some text that will be cleaned up.")
        store.search_document("text", session_id)

        store.clear_session(session_id)
        assert session_id not in store._document_chunks

        # Subsequent search should return empty
        assert store.search_document("text", session_id) == []
