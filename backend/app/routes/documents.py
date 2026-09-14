"""Document routes: upload, analyze, and ask endpoints.

No business logic here — delegates to services.
"""

import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.database import (
    create_session,
    get_chat_history,
    get_document_data,
    get_session,
    save_chat_message,
    store_document_data,
)
from app.models.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    AskRequest,
    AskResponse,
    ChatRequest,
    ClarifyRequest,
    ClarifyResponse,
    DocumentUploadResponse,
    SituationRequest,
)
from app.services.analysis_service import AnalysisService
from app.services.dependencies import (
    get_extraction_service,
    get_redaction_service,
    get_vector_store,
)
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/documents", response_model=DocumentUploadResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    """Upload a document for analysis.

    Accepts PDF, DOCX, and image files (JPG, PNG).
    File is validated, text is extracted, PII is redacted,
    and the document is prepared for analysis.
    """
    doc_service = DocumentService()

    # Read file content
    content = await file.read()
    filename = file.filename or "document"

    # Validate file
    try:
        doc_service.validate_file(
            filename=filename,
            file_size=len(content),
            content_type=file.content_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Save temp file and extract text
    try:
        temp_path = doc_service.save_temp_file(content, filename)
        text, page_count = doc_service.extract_text(temp_path, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    finally:
        # Clean up temp file
        if "temp_path" in locals():
            doc_service.cleanup_temp_file(temp_path)

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the document. The file may be empty or corrupted.",
        )

    # Run PII redaction BEFORE any persistence
    redaction_service = get_redaction_service(request)
    redacted_text = redaction_service.redact(text)

    # Detect document type
    extraction_service = get_extraction_service(request)
    doc_type = extraction_service.detect_document_type(redacted_text)

    # Create session
    session_id = create_session(
        document_type=doc_type.value,
        filename=filename,
        page_count=page_count,
    )

    # Store document data in memory (not persisted to disk)
    store_document_data(session_id, {
        "text": redacted_text,
        "original_type": doc_type.value,
        "filename": filename,
        "page_count": page_count,
    })

    # Add document chunks to vector store
    vector_store = get_vector_store(request)
    vector_store.add_document_chunks(session_id, redacted_text)

    return DocumentUploadResponse(
        document_id=session_id,
        detected_type=doc_type,
        filename=filename,
        page_count=page_count,
    )


@router.post("/documents/describe", response_model=DocumentUploadResponse)
@limiter.limit("10/minute")
async def describe_situation(
    request: Request,
    body: SituationRequest,
) -> DocumentUploadResponse:
    """Describe a legal situation without uploading a document.

    The description is treated as the document text for analysis.
    """
    # Run PII redaction on the description
    redaction_service = get_redaction_service(request)
    redacted_text = redaction_service.redact(body.description)

    # Detect situation type
    extraction_service = get_extraction_service(request)
    doc_type = extraction_service.detect_document_type(redacted_text)

    # Create session
    session_id = create_session(
        document_type=doc_type.value,
        filename=None,
    )

    # Store in memory
    store_document_data(session_id, {
        "text": redacted_text,
        "original_type": doc_type.value,
        "filename": None,
        "page_count": 0,
    })

    # Add to vector store
    vector_store = get_vector_store(request)
    vector_store.add_document_chunks(session_id, redacted_text)

    return DocumentUploadResponse(
        document_id=session_id,
        detected_type=doc_type,
        message="Situation described and processed successfully",
    )


@router.post("/documents/{document_id}/clarify", response_model=ClarifyResponse)
@limiter.limit("5/minute")
async def clarify_document(
    request: Request,
    document_id: str,
    body: ClarifyRequest | None = None,
) -> ClarifyResponse:
    """Generate clarifying questions based on the document/situation text."""
    session = get_session(document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_data = get_document_data(document_id)
    if not doc_data:
        raise HTTPException(status_code=404, detail="Document data not available.")

    extraction_service = get_extraction_service(request)
    analysis_service = AnalysisService(extraction_service)

    from app.models.schemas import DocumentType
    doc_type_str = doc_data.get("original_type", "unknown")
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.UNKNOWN

    questions = analysis_service.generate_clarifying_questions(
        doc_data["text"],
        doc_type,
        language=body.language.value if body else "en",
    )

    return ClarifyResponse(questions=questions)


@router.post("/documents/{document_id}/chat", response_model=dict)
async def add_chat_message(
    request: Request,
    document_id: str,
    body: ChatRequest,
) -> dict[str, str]:
    """Save a user message directly to the chat history."""
    session = get_session(document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document not found.")

    save_chat_message(document_id, "user", body.message)
    return {"status": "ok"}


@router.post("/documents/{document_id}/analyze", response_model=AnalysisResponse)
@limiter.limit("5/minute")
async def analyze_document(
    request: Request,
    document_id: str,
    body: AnalyzeRequest | None = None,
) -> AnalysisResponse:
    """Analyze a previously uploaded document.

    Runs legal enrichment (NLP extraction) plus Gemini AI analysis.
    Returns structured summary and risk flags.
    """
    # Verify session exists
    session = get_session(document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document not found. It may have expired.")

    # Get document data
    doc_data = get_document_data(document_id)
    if not doc_data:
        raise HTTPException(
            status_code=404,
            detail="Document data not available. Documents are not persisted beyond the session.",
        )

    # Run analysis
    extraction_service = get_extraction_service(request)
    analysis_service = AnalysisService(extraction_service)

    from app.models.schemas import DocumentType

    doc_type_str = doc_data.get("original_type", "unknown")
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.UNKNOWN

    chat_history = get_chat_history(document_id)

    result = analysis_service.analyze(
        doc_data["text"],
        doc_type,
        language=body.language.value if body else "en",
        chat_history=chat_history
    )
    result.document_id = document_id

    return result


@router.post("/documents/{document_id}/ask", response_model=AskResponse)
@limiter.limit("15/minute")
async def ask_question(
    request: Request,
    document_id: str,
    body: AskRequest,
) -> AskResponse:
    """Ask a question about a previously analyzed document.

    Uses RAG: retrieves relevant chunks from the document and statute corpus,
    then generates a grounded answer with citations.
    """
    # Verify session
    session = get_session(document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_data = get_document_data(document_id)
    if not doc_data:
        raise HTTPException(status_code=404, detail="Document data not available.")

    # Get chat history
    chat_history = get_chat_history(document_id)

    # Run RAG query
    vector_store = get_vector_store(request)
    rag_service = RAGService(vector_store)

    result = rag_service.ask(
        question=body.question,
        document_text=doc_data["text"],
        document_type=doc_data.get("original_type", "unknown"),
        session_id=document_id,
        language=body.language.value,
        chat_history=chat_history,
    )

    # Save to chat history
    save_chat_message(document_id, "user", body.question)
    save_chat_message(document_id, "assistant", result["answer"])

    return AskResponse(
        answer=result["answer"],
        citations=result.get("citations", []),
    )
