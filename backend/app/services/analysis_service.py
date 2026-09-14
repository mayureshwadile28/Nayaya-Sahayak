"""Analysis service: combines deterministic extraction with Gemini enrichment."""

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.models.schemas import (
    AnalysisResponse,
    DocumentType,
    RiskFlag,
    RiskSeverity,
)
from app.services.extraction_service import ExtractionResult, ExtractionService
from app.services.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)


# --- Pydantic schemas for Gemini structured output ---

class GeminiRiskFlag(BaseModel):
    """Schema for a single risk flag from Gemini."""

    clause_text: str = Field(description="The relevant clause excerpt")
    severity: str = Field(description="Risk level: high, medium, or low")
    reason: str = Field(description="One-line reason this is flagged")
    category: str = Field(description="Category of the risk")


class KeyTerm(BaseModel):
    """Schema for an additional key term."""

    term: str = Field(description="The name of the key term")
    definition: str = Field(description="The definition or value of the term")


class GeminiAnalysisResponse(BaseModel):
    """Schema enforced on Gemini's analysis response."""

    summary: str = Field(description="Plain-language summary of the document in 3-5 sentences")
    risk_flags: list[GeminiRiskFlag] = Field(
        description="List of risk flags identified in the document"
    )
    additional_key_terms: list[KeyTerm] = Field(
        default_factory=list,
        description="Any additional key terms not already extracted",
    )


ANALYSIS_SYSTEM_PROMPT = """You are a legal document analysis assistant for Nyaya Sahayak.
Your role is to help ordinary people in India understand legal documents in plain language.

CRITICAL RULES:
1. You provide INFORMATION only, never legal advice. Never tell someone what decision to make.
2. Never invent legal text, statute references, or section numbers you are not certain about.
3. Write in simple, clear language that a non-lawyer can understand.
4. When flagging risks, explain WHY something is unusual or concerning.
5. Always recommend consulting a qualified legal professional for specific advice.
6. Focus only on the three verticals: rental agreements, employment/gig-work agreements, and consumer disputes.

For your analysis, provide:
- A plain-language summary (3-5 sentences)
- Risk flags with severity (high/medium/low) and clear reasoning
- Any additional key terms found in the document"""


class AnalysisService:
    """Combines deterministic NLP extraction with Gemini AI enrichment."""

    def __init__(self, extraction_service: ExtractionService) -> None:
        """Initialize with the extraction service."""
        self.extraction_service = extraction_service

    def analyze(
        self,
        text: str,
        document_type: DocumentType | None = None,
        language: str = "en",
        chat_history: list[dict[str, str]] | None = None,
    ) -> AnalysisResponse:
        """Run full analysis: deterministic extraction + Gemini enrichment.

        Args:
            text: The document text (already redacted).
            document_type: Known document type, or None for auto-detection.
            language: Target language for the analysis (e.g. "en", "hi").
            chat_history: Optional chat history containing user clarifications.

        Returns:
            Complete analysis response.
        """
        # Step 1: Deterministic extraction
        extraction = self.extraction_service.extract(text, document_type)
        detected_type = extraction.document_type

        # Step 2: Gemini enrichment
        gemini_result = self._run_gemini_analysis(text, detected_type, language, chat_history)

        # Step 3: Merge results
        return self._merge_results(extraction, gemini_result, detected_type)

    def _run_gemini_analysis(
        self,
        text: str,
        document_type: DocumentType,
        language: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any] | None:
        """Run Gemini analysis with strict JSON schema."""
        try:
            gemini = get_gemini_service()

            type_context = {
                DocumentType.RENTAL: "This is a rental/lease agreement.",
                DocumentType.EMPLOYMENT: "This is an employment or gig-work agreement.",
                DocumentType.CONSUMER: "This is related to a consumer dispute or complaint.",
                DocumentType.UNKNOWN: "The document type is unknown.",
            }

            lang_instruction = ""
            if language == "hi":
                lang_instruction = "\nCRITICAL: You MUST write the ENTIRE response (summary, risk flags, reasons, key terms) in Hindi. Do not use English."

            history_text = ""
            if chat_history:
                history_text = "\n".join(
                    f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history
                )
                history_text = f"\n\nUSER CLARIFICATIONS (incorporate these facts into your analysis!):\n{history_text}\n"

            prompt = (
                f"Document type: {type_context.get(document_type, 'Unknown')}\n\n"
                f"Analyze this document/situation{history_text} and provide:\n"
                "1. A plain-language summary (3-5 sentences anyone can understand)\n"
                "2. Risk flags — clauses or terms that are unusual, one-sided, or potentially "
                "concerning for the weaker party (tenant/employee/consumer)\n"
                "3. Any additional key terms you can identify\n\n"
                "Use markdown bolding (**text**) to highlight the most important parts of the summary and risk reasons.\n"
                f"Remember: provide INFORMATION only, never legal advice.{lang_instruction}"
            )

            result = gemini.generate_with_document(
                prompt=prompt,
                document_text=text,
                system_instruction=ANALYSIS_SYSTEM_PROMPT,
                response_schema=GeminiAnalysisResponse,
                temperature=0.2,
            )
            return result
        except Exception as e:
            logger.error("Gemini analysis failed (falling back to extraction only): %s", e)
            return None

    def generate_clarifying_questions(
        self,
        text: str,
        document_type: DocumentType | None = None,
        language: str = "en",
    ) -> list[str]:
        """Generate 0-3 clarifying questions based on the document text."""
        try:
            gemini = get_gemini_service()

            type_context = {
                DocumentType.RENTAL: "rental/lease agreement",
                DocumentType.EMPLOYMENT: "employment or gig-work agreement",
                DocumentType.CONSUMER: "consumer dispute or complaint",
                DocumentType.UNKNOWN: "unknown document type",
            }
            dt = document_type or DocumentType.UNKNOWN

            lang_instruction = ""
            if language == "hi":
                lang_instruction = "\nCRITICAL: You MUST write the questions in Hindi."

            prompt = (
                f"Document type: {type_context.get(dt, 'Unknown')}\n\n"
                "Read the document/situation. Are there any critical missing facts "
                "needed to give a good legal information summary (e.g., dates, amounts, "
                "specific defects, warranty status)?\n"
                "If yes, provide up to 3 short, polite clarifying questions.\n"
                "If the document is already very detailed, return an empty list.\n"
                f"{lang_instruction}"
            )

            class ClarifyingQuestionsResponse(BaseModel):
                questions: list[str] = Field(description="List of 0-3 clarifying questions. Empty if none are needed.")

            result = gemini.generate_with_document(
                prompt=prompt,
                document_text=text,
                system_instruction="You are a legal fact-gatherer. Ask only essential questions.",
                response_schema=ClarifyingQuestionsResponse,
                temperature=0.2,
            )
            return result.get("questions", [])
        except Exception as e:
            logger.error("Failed to generate clarifying questions: %s", e)
            return []

    def _merge_results(
        self,
        extraction: ExtractionResult,
        gemini_result: dict[str, Any] | None,
        document_type: DocumentType,
    ) -> AnalysisResponse:
        """Merge deterministic extraction with Gemini enrichment."""
        # Start with extraction results
        risk_flags: list[RiskFlag] = []
        seen_categories: set[str] = set()

        # Add deterministic extraction flags first (these are reliable)
        for clause in extraction.clauses:
            flag = RiskFlag(
                clause_text=clause.text,
                severity=clause.severity,
                reason=clause.reason,
                category=clause.category,
                legal_reference=clause.legal_reference,
            )
            risk_flags.append(flag)
            seen_categories.add(clause.category)

        # Default summary
        summary = self._generate_fallback_summary(extraction, document_type)
        key_terms = dict(extraction.key_terms)

        # Merge Gemini results if available
        if gemini_result:
            summary = gemini_result.get("summary", summary)

            # Add Gemini risk flags that aren't duplicates of extraction flags
            for gflag in gemini_result.get("risk_flags", []):
                category = gflag.get("category", "general")
                if category not in seen_categories:
                    severity_str = gflag.get("severity", "low").lower()
                    try:
                        severity = RiskSeverity(severity_str)
                    except ValueError:
                        severity = RiskSeverity.LOW

                    risk_flags.append(
                        RiskFlag(
                            clause_text=gflag.get("clause_text", ""),
                            severity=severity,
                            reason=gflag.get("reason", "Flagged by AI analysis"),
                            category=category,
                        )
                    )
                    seen_categories.add(category)

            # Merge additional key terms
            for kt in gemini_result.get("additional_key_terms", []):
                k = kt.get("term")
                v = kt.get("definition")
                if k and k not in key_terms:
                    key_terms[k] = v

        # Sort risk flags by severity (High first)
        severity_order = {RiskSeverity.HIGH: 0, RiskSeverity.MEDIUM: 1, RiskSeverity.LOW: 2}
        risk_flags.sort(key=lambda f: severity_order.get(f.severity, 3))

        return AnalysisResponse(
            document_id="",  # Set by route handler
            document_type=document_type,
            summary=summary,
            risk_flags=risk_flags,
            key_terms=key_terms,
            parties=extraction.parties,
            dates=extraction.dates,
            amounts=extraction.amounts,
        )

    def _generate_fallback_summary(
        self,
        extraction: ExtractionResult,
        document_type: DocumentType,
    ) -> str:
        """Generate a basic summary when Gemini is unavailable."""
        type_names = {
            DocumentType.RENTAL: "rental agreement",
            DocumentType.EMPLOYMENT: "employment agreement",
            DocumentType.CONSUMER: "consumer-related document",
            DocumentType.UNKNOWN: "document",
        }
        doc_name = type_names.get(document_type, "document")

        parts = [f"This appears to be a {doc_name}."]

        if extraction.parties:
            parts.append(f"Parties involved: {', '.join(extraction.parties[:4])}.")
        if extraction.amounts:
            parts.append(f"Key amounts mentioned: {', '.join(extraction.amounts[:3])}.")
        if extraction.clauses:
            high_count = sum(1 for c in extraction.clauses if c.severity == RiskSeverity.HIGH)
            if high_count:
                parts.append(f"{high_count} high-risk clause(s) identified that require attention.")

        return " ".join(parts)
