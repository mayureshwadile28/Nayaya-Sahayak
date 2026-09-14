"""ChromaDB vector store for document chunks and statute corpus.

Embedded mode — no external server required.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


class VectorStoreService:
    """ChromaDB-based vector store for RAG retrieval."""

    def __init__(self) -> None:
        """Initialize ChromaDB client in embedded mode."""
        chroma_dir = settings.base_dir / "chroma_data"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        self.statutes_collection: Any = None
        self.documents_collection: Any = None

    def initialize(self) -> None:
        """Initialize collections and load statute corpus."""
        logger.info("Initializing ChromaDB vector store...")

        self.statutes_collection = self.client.get_or_create_collection(
            name="statutes",
            metadata={"description": "Legal statute excerpts for RAG retrieval"},
        )

        self.documents_collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "User document chunks for session-based RAG"},
        )

        # Load statute data
        self._load_statute_corpus()

        logger.info("ChromaDB vector store ready.")

    def _load_statute_corpus(self) -> None:
        """Load verified statute excerpts into the statutes collection."""
        import json

        statutes_dir = settings.data_dir / "statutes"
        if not statutes_dir.exists():
            logger.warning("Statutes directory not found: %s", statutes_dir)
            return

        documents: list[str] = []
        metadatas: list[dict[str, str]] = []
        ids: list[str] = []

        for statute_file in statutes_dir.glob("*.json"):
            try:
                data = json.loads(statute_file.read_text(encoding="utf-8"))
                entries = data if isinstance(data, list) else [data]

                for i, entry in enumerate(entries):
                    text = entry.get("text", "")
                    if not text:
                        continue

                    doc_id = f"{statute_file.stem}_{i}"
                    act = entry.get("act", "Unknown Act")
                    section = entry.get("section", "")
                    doc_type = entry.get("document_type", "general")

                    documents.append(text)
                    metadatas.append({
                        "act": act,
                        "section": section,
                        "document_type": doc_type,
                        "source": f"{act} — {section}" if section else act,
                        "verified": str(entry.get("verified", False)),
                    })
                    ids.append(doc_id)
            except Exception as e:
                logger.error("Failed to load statute file %s: %s", statute_file, e)

        if documents:
            try:
                existing = self.statutes_collection.get(ids=ids)
                if existing and len(existing["ids"]) == len(ids):
                    logger.info("Statute excerpts already exist in vector store. Skipping embedding.")
                    return
            except Exception:
                pass

            # Clear existing and re-add just to be safe if count mismatch
            try:
                existing_all = self.statutes_collection.get()
                if existing_all and existing_all.get("ids"):
                    self.statutes_collection.delete(ids=existing_all["ids"])
            except Exception:
                pass

            self.statutes_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info("Loaded %d statute excerpts into vector store.", len(documents))
        else:
            logger.warning("No statute excerpts found to load.")

    def add_document_chunks(self, session_id: str, text: str) -> None:
        """Chunk and add a document to the documents collection.

        Args:
            session_id: Session identifier for filtering.
            text: Full document text.
        """
        chunks = self._chunk_text(text)

        if not chunks:
            return

        documents = [c["text"] for c in chunks]
        metadatas = [{"session_id": session_id, "chunk_index": str(c["index"])} for c in chunks]
        ids = [f"{session_id}_chunk_{c['index']}" for c in chunks]

        self.documents_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info("Added %d document chunks for session %s", len(chunks), session_id[:8])

    def search_statutes(
        self,
        query: str,
        document_type: str = "general",
        n_results: int = 5,
    ) -> list[dict[str, str]]:
        """Search statute corpus for relevant excerpts.

        Args:
            query: Search query.
            document_type: Filter by document type.
            n_results: Number of results to return.

        Returns:
            List of matching statute excerpts with metadata.
        """
        if not self.statutes_collection:
            return []

        try:
            results = self.statutes_collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"document_type": {"$in": [document_type, "general"]}},
            )

            return self._format_results(results)
        except Exception as e:
            logger.error("Statute search failed: %s", e)
            # Try without filter
            try:
                results = self.statutes_collection.query(
                    query_texts=[query],
                    n_results=n_results,
                )
                return self._format_results(results)
            except Exception:
                return []

    def search_document(
        self,
        query: str,
        session_id: str,
        n_results: int = 5,
    ) -> list[dict[str, str]]:
        """Search document chunks for a specific session.

        Args:
            query: Search query.
            session_id: Session to search within.
            n_results: Number of results.

        Returns:
            List of matching document chunks.
        """
        if not self.documents_collection:
            return []

        try:
            results = self.documents_collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"session_id": session_id},
            )
            return self._format_results(results)
        except Exception as e:
            logger.error("Document search failed: %s", e)
            return []

    def _chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into overlapping chunks for vector indexing."""
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

    def _format_results(self, results: dict) -> list[dict[str, str]]:
        """Format ChromaDB query results into a clean list of dicts."""
        formatted: list[dict[str, str]] = []

        if not results or not results.get("documents"):
            return formatted

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []

        for i, doc_text in enumerate(documents):
            entry: dict[str, str] = {"text": doc_text}
            if i < len(metadatas) and metadatas[i]:
                entry.update({k: str(v) for k, v in metadatas[i].items()})
            formatted.append(entry)

        return formatted

    def clear_session(self, session_id: str) -> None:
        """Remove all document chunks for a session."""
        if not self.documents_collection:
            return

        try:
            results = self.documents_collection.get(
                where={"session_id": session_id},
            )
            if results["ids"]:
                self.documents_collection.delete(ids=results["ids"])
                logger.info("Cleared %d chunks for session %s", len(results["ids"]), session_id[:8])
        except Exception as e:
            logger.warning("Failed to clear session %s: %s", session_id[:8], e)
