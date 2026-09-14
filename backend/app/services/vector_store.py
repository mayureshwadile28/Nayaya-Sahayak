"""In-memory retrieval store for document chunks and statute corpus.

Ultra-fast pure-Python similarity matching without heavy ONNX neural net dependencies,
guaranteeing instant cold starts (<10ms) and full reliability on serverless environments.
"""

import json
import logging
import re
from collections import Counter
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


class VectorStoreService:
    """Fast in-memory retrieval store for RAG."""

    def __init__(self) -> None:
        """Initialize in-memory collections."""
        self._statutes: list[dict[str, Any]] = []
        self._document_chunks: dict[str, list[dict[str, Any]]] = {}
        self._initialized: bool = False

    def initialize(self) -> None:
        """Initialize collections and load statute corpus."""
        if self._initialized:
            return
        logger.info("Initializing in-memory retrieval store...")
        self._load_statute_corpus()
        self._initialized = True
        logger.info("In-memory retrieval store ready (%d statutes loaded).", len(self._statutes))

    def _load_statute_corpus(self) -> None:
        """Load verified statute excerpts from JSON files."""
        statutes_dir = settings.data_dir / "statutes"
        if not statutes_dir.exists():
            logger.warning("Statutes directory not found: %s", statutes_dir)
            return

        for statute_file in sorted(statutes_dir.glob("*.json")):
            try:
                data = json.loads(statute_file.read_text(encoding="utf-8"))
                entries = data if isinstance(data, list) else [data]

                for i, entry in enumerate(entries):
                    text = entry.get("text", "").strip()
                    if not text:
                        continue

                    doc_id = f"{statute_file.stem}_{i}"
                    act = entry.get("act", "Unknown Act")
                    section = entry.get("section", "")
                    doc_type = entry.get("document_type", "general")

                    self._statutes.append({
                        "id": doc_id,
                        "text": text,
                        "act": act,
                        "section": section,
                        "document_type": doc_type,
                        "source": f"{act} — {section}" if section else act,
                        "verified": str(entry.get("verified", False)),
                        "tokens": self._tokenize(text),
                    })
            except Exception as e:
                logger.error("Failed to load statute file %s: %s", statute_file, e)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words for keyword & relevance scoring."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def _compute_relevance(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        """Compute BM25-style term frequency relevance score between query and document."""
        if not query_tokens or not doc_tokens:
            return 0.0

        doc_counter = Counter(doc_tokens)
        doc_len = len(doc_tokens)
        score = 0.0

        for q in query_tokens:
            count = doc_counter.get(q, 0)
            if count > 0:
                tf = count / (count + 1.2 * (0.25 + 0.75 * (doc_len / 50.0)))
                score += tf

        return score

    def add_document_chunks(self, session_id: str, text: str) -> None:
        """Chunk and add a document to in-memory store."""
        chunks = self._chunk_text(text)
        if not chunks:
            return

        session_chunks = []
        for c in chunks:
            chunk_text = c["text"]
            session_chunks.append({
                "id": f"{session_id}_chunk_{c['index']}",
                "session_id": session_id,
                "chunk_index": str(c["index"]),
                "text": chunk_text,
                "tokens": self._tokenize(chunk_text),
            })

        self._document_chunks[session_id] = session_chunks
        logger.info("Added %d document chunks for session %s", len(chunks), session_id[:8])

    def search_statutes(
        self,
        query: str,
        document_type: str = "general",
        n_results: int = 5,
    ) -> list[dict[str, str]]:
        """Search statute corpus for relevant excerpts."""
        if not self._initialized:
            self.initialize()

        query_tokens = self._tokenize(query)
        scored: list[tuple[float, dict[str, Any]]] = []

        for item in self._statutes:
            item_type = item.get("document_type", "general")
            if document_type and item_type not in (document_type, "general"):
                continue

            score = self._compute_relevance(query_tokens, item["tokens"])
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_items = scored[:n_results]

        return [
            {
                "text": item["text"],
                "act": item["act"],
                "section": item["section"],
                "document_type": item["document_type"],
                "source": item["source"],
                "verified": item["verified"],
            }
            for _, item in top_items
        ]

    def search_document(
        self,
        query: str,
        session_id: str,
        n_results: int = 5,
    ) -> list[dict[str, str]]:
        """Search document chunks for a specific session."""
        chunks = self._document_chunks.get(session_id, [])
        if not chunks:
            return []

        query_tokens = self._tokenize(query)
        scored: list[tuple[float, dict[str, Any]]] = []

        for c in chunks:
            score = self._compute_relevance(query_tokens, c["tokens"])
            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_items = scored[:n_results]

        return [
            {
                "text": c["text"],
                "session_id": c["session_id"],
                "chunk_index": c["chunk_index"],
            }
            for _, c in top_items
        ]

    def _chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into overlapping chunks for indexing."""
        if not text:
            return []

        words = text.split()
        chunks: list[dict[str, Any]] = []

        i = 0
        chunk_index = 0
        while i < len(words):
            chunk_words = words[i : i + CHUNK_SIZE]
            chunk_text = " ".join(chunk_words)

            if chunk_text.strip():
                chunks.append({"text": chunk_text, "index": chunk_index})
                chunk_index += 1

            i += CHUNK_SIZE - CHUNK_OVERLAP

        return chunks

    def clear_session(self, session_id: str) -> None:
        """Remove all document chunks for a session."""
        self._document_chunks.pop(session_id, None)
