"""RAG service: In-memory vector retrieval + Gemini grounded Q&A."""

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.services.gemini_service import get_gemini_service
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class RAGCitation(BaseModel):
    """A citation source for a RAG answer."""

    source: str = Field(description="Source name (document or statute)")
    text: str = Field(description="The relevant excerpt")


class RAGResponse(BaseModel):
    """Schema for Gemini RAG response."""

    answer: str = Field(description="The grounded answer to the user's question")
    citations: list[RAGCitation] = Field(
        description="Sources the answer is grounded in"
    )


RAG_SYSTEM_PROMPT = """You are a legal information assistant for Nyaya Sahayak.
You help ordinary people in India understand legal documents and their rights.

CRITICAL RULES:
1. You provide INFORMATION only, never legal advice. Never tell someone what to do.
2. Use simple, clear language. Avoid legal jargon; if you must use a legal term, explain it.
3. Always end substantive answers with a reminder to consult a legal professional.
4. Never invent statute references or section numbers."""


class RAGService:
    """Retrieval-Augmented Generation for document Q&A."""

    def __init__(self, vector_store: VectorStoreService) -> None:
        """Initialize with the vector store."""
        self.vector_store = vector_store

    def ask(
        self,
        question: str,
        document_text: str,
        document_type: str,
        session_id: str,
        language: str = "en",
        chat_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Answer a question grounded in document and statute context.

        Args:
            question: User's question.
            document_text: The full document text.
            document_type: Type of document for filtering statutes.
            session_id: Session ID for document-specific chunks.
            chat_history: Previous chat messages for context.

        Returns:
            Dict with answer and citations.
        """
        # Retrieve relevant statute chunks
        statute_chunks = self.vector_store.search_statutes(
            query=question,
            document_type=document_type,
            n_results=5,
        )

        # Retrieve relevant document chunks
        doc_chunks = self.vector_store.search_document(
            query=question,
            session_id=session_id,
            n_results=5,
        )

        # Build context
        context_parts: list[str] = []

        if doc_chunks:
            context_parts.append("DOCUMENT EXCERPTS:")
            for i, chunk in enumerate(doc_chunks, 1):
                context_parts.append(f"- {chunk['text']}")
            context_parts.append("")

        if statute_chunks:
            context_parts.append("RELEVANT STATUTE EXCERPTS:")
            for i, chunk in enumerate(statute_chunks, 1):
                source = chunk.get("source", "Statute")
                context_parts.append(f"[Statute-{i}: {source}] {chunk['text']}")
            context_parts.append("")

        context = "\n".join(context_parts)

        # Build prompt with chat history
        history_text = ""
        if chat_history:
            history_parts = []
            for msg in chat_history[-6:]:  # Last 6 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_parts.append(f"{role.upper()}: {content}")
            history_text = "\n".join(history_parts) + "\n\n"

        lang_instruction = ""
        if language == "hi":
            lang_instruction = "\nCRITICAL: You MUST write the answer entirely in Hindi."

        prompt = (
            f"INITIAL SITUATION/DOCUMENT:\n{context}\n\n"
            f"CHAT HISTORY:\n{history_text}"
            f"USER QUESTION/UPDATE: {question}\n\n"
            "You are Nyaya Sahayak, an interactive legal information assistant.\n"
            "1. Use the INITIAL SITUATION and CHAT HISTORY to understand the user's situation.\n"
            "2. If the user provides new information or corrections in the chat, ACCEPT and INCORPORATE them into your understanding. Do not reject new facts.\n"
            "3. If critical information is missing to provide a helpful answer, proactively ask 1-2 clarifying questions to gather accurate data.\n"
            "4. Refer to the context naturally as 'your situation' or 'your document' (do not use '[Doc-1]').\n"
            "5. Provide legal INFORMATION, not legal advice.\n"
            "Use markdown bolding (**text**) to highlight important parts of your answer."
            f"{lang_instruction}"
        )

        try:
            gemini = get_gemini_service()
            result = gemini.generate(
                prompt=prompt,
                system_instruction=RAG_SYSTEM_PROMPT,
                response_schema=RAGResponse,
                temperature=0.3,
            )

            return {
                "answer": result.get("answer", "I couldn't generate an answer."),
                "citations": [
                    {"source": c.get("source", ""), "text": c.get("text", "")}
                    for c in result.get("citations", [])
                ],
            }
        except Exception as e:
            logger.error("RAG query failed: %s", e)
            return {
                "answer": (
                    "I'm sorry, I couldn't process your question right now. "
                    "Please try again, or consult a legal professional for assistance."
                ),
                "citations": [],
            }
