"""Pydantic models for request/response schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# --- Enums ---

class DocumentType(str, Enum):
    """Supported document/situation types."""

    RENTAL = "rental"
    EMPLOYMENT = "employment"
    CONSUMER = "consumer"
    UNKNOWN = "unknown"


class RiskSeverity(str, Enum):
    """Risk severity levels — always displayed with text label, never color alone."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Language(str, Enum):
    """Supported UI languages."""

    EN = "en"
    HI = "hi"


# --- Request Models ---

class SituationRequest(BaseModel):
    """Request for describing a legal situation without a document."""

    description: str = Field(..., min_length=20, max_length=5000)
    language: Language = Language.EN


class AnalyzeRequest(BaseModel):
    """Request for analyzing a document."""

    language: Language = Language.EN


class AskRequest(BaseModel):
    """Request for asking a question about an analyzed document."""

    question: str = Field(..., min_length=5, max_length=1000)
    language: Language = Language.EN


class RightsQuery(BaseModel):
    """Query parameters for rights and next steps."""

    doc_type: DocumentType
    state: str = Field(..., min_length=2, max_length=100)


class ClarifyRequest(BaseModel):
    """Request for asking clarifying questions before analysis."""

    language: Language = Language.EN


class ChatRequest(BaseModel):
    """Request for saving user answers/messages without AI response."""

    message: str = Field(..., min_length=1, max_length=5000)


class ExportRequest(BaseModel):
    """Request for generating a lawyer-prep export."""

    language: Language = Language.EN
    format: str = Field(default="markdown", pattern="^(markdown|pdf)$")


# --- Response Models ---

class RiskFlag(BaseModel):
    """A single risk flag identified in the document."""

    clause_text: str = Field(..., description="The relevant clause or text excerpt")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    reason: str = Field(..., description="One-line explanation of why this is flagged")
    category: str = Field(..., description="Category (e.g., 'security_deposit', 'non_compete')")
    legal_reference: str | None = Field(
        None, description="Relevant statute section, if applicable"
    )


class DocumentUploadResponse(BaseModel):
    """Response after successful document upload."""

    document_id: str
    detected_type: DocumentType
    filename: str | None = None
    page_count: int | None = None
    message: str = "Document uploaded and processed successfully"


class ClarifyResponse(BaseModel):
    """Response containing clarifying questions from the AI."""

    questions: list[str] = Field(default_factory=list, description="List of questions to ask the user")


class AnalysisResponse(BaseModel):
    """Response from document analysis."""

    document_id: str
    document_type: DocumentType
    summary: str = Field(..., description="Plain-language summary of the document")
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    key_terms: dict[str, str] = Field(
        default_factory=dict, description="Key terms extracted (e.g., deposit amount, notice period)"
    )
    parties: list[str] = Field(default_factory=list, description="Parties identified in the document")
    dates: list[str] = Field(default_factory=list, description="Important dates found")
    amounts: list[str] = Field(default_factory=list, description="Monetary amounts found")


class AskResponse(BaseModel):
    """Response from document Q&A."""

    answer: str
    citations: list[dict[str, str]] = Field(
        default_factory=list,
        description="Sources the answer is grounded in (document chunks, statute excerpts)",
    )
    disclaimer: str = (
        "This information is for educational purposes only and does not constitute legal advice. "
        "Please consult a qualified legal professional for advice specific to your situation."
    )


class LegalAidInfo(BaseModel):
    """Legal aid eligibility and contact information."""

    eligible_categories: list[str] = Field(
        default_factory=list, description="Categories eligible for free legal aid under NALSA"
    )
    forum: str = Field(..., description="Appropriate legal forum for this matter")
    forum_description: str = Field(..., description="Plain-language description of the forum")
    contact_info: dict[str, str] = Field(
        default_factory=dict, description="Contact details for the relevant authority"
    )
    online_portal: str | None = Field(None, description="URL for online filing, if available")
    filing_process: str = Field(
        default="", description="Plain-language steps to file a complaint/case"
    )


class RightsResponse(BaseModel):
    """Response with rights checklist and legal aid information."""

    document_type: DocumentType
    state: str
    rights: list[str] = Field(default_factory=list, description="Plain-language rights checklist")
    legal_aid: LegalAidInfo
    disclaimer: str = (
        "This information is for educational purposes only. Contact details and eligibility "
        "criteria should be verified with the respective authorities before relying on them."
    )


class ExportResponse(BaseModel):
    """Response for the lawyer-prep brief export."""

    document_id: str
    filename: str
    content: str = Field(..., description="The generated brief content")
    format: str


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    citations: list[dict[str, str]] | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str | None = None
    status_code: int = 400
