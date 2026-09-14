"""Unit tests for RAGService retrieval and prompt grounding."""

from unittest.mock import MagicMock, patch

from app.services.rag_service import RAGService
from app.services.vector_store import VectorStoreService


class TestRAGService:
    """Test RAG retrieval, context building, and fallback behaviors."""

    def test_ask_successful_response(self) -> None:
        """ask() should return grounded answer and citations when Gemini succeeds."""
        mock_vector_store = MagicMock(spec=VectorStoreService)
        mock_vector_store.search_statutes.return_value = [
            {"source": "Delhi Rent Control Act 1958", "text": "Notice of 30 days is mandatory."}
        ]
        mock_vector_store.search_document.return_value = [
            {"text": "Tenant agrees to vacate on 24 hours notice."}
        ]

        mock_gemini = MagicMock()
        mock_gemini.generate.return_value = {
            "answer": "Under Delhi Rent Control Act, 24 hours notice is invalid. 30 days is required.",
            "citations": [{"source": "Delhi Rent Control Act 1958", "text": "Notice of 30 days is mandatory."}],
        }

        with patch("app.services.rag_service.get_gemini_service", return_value=mock_gemini):
            rag = RAGService(vector_store=mock_vector_store)
            result = rag.ask(
                question="Can landlord evict me in 24 hours?",
                document_text="Tenant agrees to vacate on 24 hours notice.",
                document_type="rental",
                session_id="session-1",
                language="en",
            )

            assert "24 hours notice is invalid" in result["answer"]
            assert len(result["citations"]) == 1
            assert result["citations"][0]["source"] == "Delhi Rent Control Act 1958"

    def test_ask_incorporates_chat_history(self) -> None:
        """Chat history should be included in prompt passed to Gemini."""
        mock_vector_store = MagicMock(spec=VectorStoreService)
        mock_vector_store.search_statutes.return_value = []
        mock_vector_store.search_document.return_value = []

        mock_gemini = MagicMock()
        mock_gemini.generate.return_value = {"answer": "Noted.", "citations": []}

        with patch("app.services.rag_service.get_gemini_service", return_value=mock_gemini):
            rag = RAGService(vector_store=mock_vector_store)
            chat_history = [
                {"role": "user", "content": "I live in Mumbai"},
                {"role": "assistant", "content": "Maharashtra Rent Control Act applies to Mumbai."},
            ]
            rag.ask(
                question="What is the deposit limit here?",
                document_text="",
                document_type="rental",
                session_id="session-2",
                chat_history=chat_history,
            )

            # Check prompt contained the previous conversation
            call_kwargs = mock_gemini.generate.call_args[1]
            assert "I live in Mumbai" in call_kwargs["prompt"]

    def test_ask_hindi_language_instruction(self) -> None:
        """When language='hi', prompt must include Hindi generation instruction."""
        mock_vector_store = MagicMock(spec=VectorStoreService)
        mock_vector_store.search_statutes.return_value = []
        mock_vector_store.search_document.return_value = []

        mock_gemini = MagicMock()
        mock_gemini.generate.return_value = {"answer": "नमस्ते", "citations": []}

        with patch("app.services.rag_service.get_gemini_service", return_value=mock_gemini):
            rag = RAGService(vector_store=mock_vector_store)
            rag.ask(
                question="किराया कानून क्या है?",
                document_text="",
                document_type="rental",
                session_id="session-3",
                language="hi",
            )

            call_kwargs = mock_gemini.generate.call_args[1]
            assert "Hindi" in call_kwargs["prompt"]

    def test_ask_gemini_failure_fallback(self) -> None:
        """When Gemini raises an exception, ask() should return a graceful fallback."""
        mock_vector_store = MagicMock(spec=VectorStoreService)
        mock_vector_store.search_statutes.return_value = []
        mock_vector_store.search_document.return_value = []

        mock_gemini = MagicMock()
        mock_gemini.generate.side_effect = RuntimeError("API quota exceeded")

        with patch("app.services.rag_service.get_gemini_service", return_value=mock_gemini):
            rag = RAGService(vector_store=mock_vector_store)
            result = rag.ask(
                question="Can you help me?",
                document_text="",
                document_type="rental",
                session_id="session-4",
            )

            assert "couldn't process your question" in result["answer"]
            assert result["citations"] == []
