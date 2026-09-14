"""Export routes: generate and download lawyer-prep brief."""

import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.database import get_document_data, get_session, get_chat_history
from app.models.schemas import (
    AnalysisResponse,
    DocumentType,
    ExportRequest,
    ExportResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["export"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/documents/{document_id}/export", response_model=ExportResponse)
@limiter.limit("5/minute")
async def export_brief(
    request: Request,
    document_id: str,
    body: ExportRequest | None = None,
) -> ExportResponse:
    """Generate a downloadable lawyer-prep brief.

    Creates a one-page summary with:
    - What the document says
    - What's unusual about it
    - Questions to bring to a lawyer or legal aid clinic
    """
    if body is None:
        body = ExportRequest()

    # Verify session
    session = get_session(document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_data = get_document_data(document_id)
    if not doc_data:
        raise HTTPException(status_code=404, detail="Document data not available.")

    # Run analysis first to get structured data
    extraction_service = request.app.state.extraction_service
    analysis_service = AnalysisService(extraction_service)

    doc_type_str = doc_data.get("original_type", "unknown")
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.UNKNOWN

    analysis = analysis_service.analyze(
        doc_data["text"], 
        doc_type, 
        language=body.language.value
    )
    analysis.document_id = document_id

    # Generate brief
    chat_history = get_chat_history(document_id)
    export_service = ExportService()
    brief_content = export_service.generate_brief(
        document_text=doc_data["text"],
        analysis=analysis,
        language=body.language.value,
        chat_history=chat_history,
    )

    filename = f"nyaya_sahayak_brief_{document_id[:8]}.md"

    return ExportResponse(
        document_id=document_id,
        filename=filename,
        content=brief_content,
        format=body.format,
    )
