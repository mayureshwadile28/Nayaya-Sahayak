"""Export routes: generate and download lawyer-prep brief."""

import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from collections import OrderedDict

from app.models.database import get_chat_history, get_document_data, get_session
from app.models.schemas import (
    DocumentType,
    ExportRequest,
    ExportResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.dependencies import get_extraction_service
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["export"])
limiter = Limiter(key_func=get_remote_address)

# Cache for generated briefs: (document_id, language) -> brief_content
_brief_cache: OrderedDict[tuple[str, str], str] = OrderedDict()
_MAX_BRIEF_CACHE_SIZE = 64


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

    cache_key = (document_id, body.language.value)
    if cache_key in _brief_cache:
        logger.info("Serving cached export brief for %s (%s)", document_id, body.language.value)
        _brief_cache.move_to_end(cache_key)
        filename = f"nyaya_sahayak_brief_{document_id[:8]}.md"
        return ExportResponse(
            document_id=document_id,
            filename=filename,
            content=_brief_cache[cache_key],
            format=body.format,
        )

    # Run analysis first to get structured data
    extraction_service = get_extraction_service(request)
    analysis_service = AnalysisService(extraction_service)

    doc_type_str = doc_data.get("original_type", "unknown")
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.UNKNOWN

    analysis = analysis_service.analyze(
        doc_data["text"],
        doc_type,
        language=body.language.value,
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

    # Cache brief
    if len(_brief_cache) >= _MAX_BRIEF_CACHE_SIZE:
        _brief_cache.popitem(last=False)
    _brief_cache[cache_key] = brief_content

    filename = f"nyaya_sahayak_brief_{document_id[:8]}.md"

    return ExportResponse(
        document_id=document_id,
        filename=filename,
        content=brief_content,
        format=body.format,
    )

