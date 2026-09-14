"""Service dependencies and singletons with resilient fallback for serverless."""

from fastapi import Request

from app.services.document_service import DocumentService
from app.services.extraction_service import ExtractionService
from app.services.redaction_service import RedactionService
from app.services.vector_store import VectorStoreService

_extraction_service: ExtractionService | None = None
_redaction_service: RedactionService | None = None
_vector_store: VectorStoreService | None = None
_document_service: DocumentService | None = None


def get_extraction_service(request: Request | None = None) -> ExtractionService:
    """Get the ExtractionService instance from app state or lazy singleton."""
    global _extraction_service  # noqa: PLW0603
    if request and hasattr(request.app.state, "extraction_service"):
        service = request.app.state.extraction_service
        if service is not None:
            return service

    if _extraction_service is None:
        _extraction_service = ExtractionService()

    if request:
        request.app.state.extraction_service = _extraction_service

    return _extraction_service


def get_redaction_service(request: Request | None = None) -> RedactionService:
    """Get the RedactionService instance from app state or lazy singleton."""
    global _redaction_service  # noqa: PLW0603
    if request and hasattr(request.app.state, "redaction_service"):
        service = request.app.state.redaction_service
        if service is not None:
            return service

    if _redaction_service is None:
        _redaction_service = RedactionService()

    if request:
        request.app.state.redaction_service = _redaction_service

    return _redaction_service


def get_vector_store(request: Request | None = None) -> VectorStoreService:
    """Get the VectorStoreService instance from app state or lazy singleton."""
    global _vector_store  # noqa: PLW0603
    if request and hasattr(request.app.state, "vector_store"):
        service = request.app.state.vector_store
        if service is not None:
            return service

    if _vector_store is None:
        _vector_store = VectorStoreService()
        _vector_store.initialize()

    if request:
        request.app.state.vector_store = _vector_store

    return _vector_store


def get_document_service(request: Request | None = None) -> DocumentService:
    """Get the DocumentService instance from app state or lazy singleton."""
    global _document_service  # noqa: PLW0603
    if request and hasattr(request.app.state, "document_service"):
        service = request.app.state.document_service
        if service is not None:
            return service

    if _document_service is None:
        _document_service = DocumentService()

    if request:
        request.app.state.document_service = _document_service

    return _document_service

