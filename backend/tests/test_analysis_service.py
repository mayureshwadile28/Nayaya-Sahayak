"""Unit tests for AnalysisService (pipeline, merging, Gemini fallback, clarifying questions)."""

from unittest.mock import MagicMock, patch

from app.models.schemas import DocumentType, RiskSeverity
from app.services.analysis_service import AnalysisService
from app.services.extraction_service import ExtractionService


class TestAnalysisService:
    """Test analysis pipeline, merging logic, and fallback behaviors."""

    def test_analyze_with_gemini_success(self) -> None:
        """analyze() should merge deterministic extraction with Gemini output."""
        extraction_service = ExtractionService()
        sample_lease = (
            "RENTAL AGREEMENT\n"
            "The tenant shall pay a monthly rent of Rs. 20,000. "
            "The security deposit shall be Rs. 200,000. "
            "The landlord may evict the tenant at any time without notice."
        )

        mock_gemini = MagicMock()
        mock_gemini.generate_with_document.return_value = {
            "summary": "This is a rental agreement with high risk terms for the tenant.",
            "risk_flags": [
                {
                    "clause_text": "The landlord may evict the tenant at any time without notice.",
                    "severity": "high",
                    "reason": "Immediate eviction without notice violates standard tenancy laws.",
                    "category": "Eviction",
                }
            ],
            "additional_key_terms": [
                {"term": "Rent", "definition": "Rs. 20,000 per month"}
            ],
        }

        with patch("app.services.analysis_service.get_gemini_service", return_value=mock_gemini):
            service = AnalysisService(extraction_service)
            result = service.analyze(sample_lease, DocumentType.RENTAL)

            assert result.document_type == DocumentType.RENTAL
            assert "high risk terms" in result.summary
            assert len(result.risk_flags) > 0
            has_high_risk = any(rf.severity == RiskSeverity.HIGH for rf in result.risk_flags)
            assert has_high_risk is True


    def test_analyze_fallback_when_gemini_fails(self) -> None:
        """When Gemini fails, analyze() should gracefully fall back to deterministic summary."""
        extraction_service = ExtractionService()
        sample_agreement = (
            "EMPLOYMENT AGREEMENT\n"
            "The employee shall not work for any competitor for 5 years after termination. "
            "Probation period is 12 months."
        )

        mock_gemini = MagicMock()
        mock_gemini.generate_with_document.side_effect = Exception("Gemini service unreachable")

        with patch("app.services.analysis_service.get_gemini_service", return_value=mock_gemini):
            service = AnalysisService(extraction_service)
            result = service.analyze(sample_agreement, DocumentType.EMPLOYMENT)

            # Should not crash and should produce fallback summary
            assert result.document_type == DocumentType.EMPLOYMENT
            assert isinstance(result.summary, str)
            assert len(result.summary) > 0
            assert len(result.risk_flags) > 0

    def test_generate_clarifying_questions(self) -> None:
        """generate_clarifying_questions should return relevant questions based on text."""
        extraction_service = ExtractionService()
        mock_gemini = MagicMock()
        mock_gemini.generate_with_document.return_value = {
            "questions": [
                "Which state is this rental property located in?",
                "Was a written lease agreement signed by both parties?",
            ]
        }

        with patch("app.services.analysis_service.get_gemini_service", return_value=mock_gemini):
            service = AnalysisService(extraction_service)
            questions = service.generate_clarifying_questions(
                "My landlord took 6 months deposit.",
                DocumentType.RENTAL,
            )

            assert len(questions) == 2
            assert "rental property" in questions[0]
