"""Integration tests for API endpoints with Gemini calls mocked."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestRightsEndpoint:
    """Tests for the /api/rights endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi import FastAPI

        from app.routes.rights import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        self.client = TestClient(app)

    def test_rights_rental_delhi(self):
        response = self.client.get("/api/rights?doc_type=rental&state=Delhi")
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "rental"
        assert data["state"] == "Delhi"
        assert len(data["rights"]) > 0
        assert "legal_aid" in data
        assert "forum" in data["legal_aid"]

    def test_rights_employment(self):
        response = self.client.get("/api/rights?doc_type=employment&state=Maharashtra")
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "employment"
        assert len(data["rights"]) > 0

    def test_rights_consumer(self):
        response = self.client.get("/api/rights?doc_type=consumer&state=Karnataka")
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "consumer"
        assert "e_daakhil" in str(data["legal_aid"]["contact_info"]).lower() or \
               "edaakhil" in str(data["legal_aid"]).lower()

    def test_rights_missing_params(self):
        response = self.client.get("/api/rights")
        assert response.status_code == 422

    def test_rights_includes_disclaimer(self):
        response = self.client.get("/api/rights?doc_type=rental&state=Delhi")
        data = response.json()
        assert "disclaimer" in data
        assert len(data["disclaimer"]) > 0

    def test_rights_includes_nalsa_eligibility(self):
        response = self.client.get("/api/rights?doc_type=rental&state=Delhi")
        data = response.json()
        categories = data["legal_aid"]["eligible_categories"]
        assert len(categories) > 0
        # Should include known NALSA categories
        categories_text = " ".join(categories).lower()
        assert "scheduled" in categories_text or "women" in categories_text


class TestGeminiServiceMocked:
    """Tests for Gemini service with mocked API calls."""

    def test_generate_with_schema(self):
        from pydantic import BaseModel, Field

        from app.services.gemini_service import GeminiService

        class TestSchema(BaseModel):
            summary: str = Field(description="Test summary")
            score: int = Field(description="Test score")

        service = GeminiService()

        # Mock the client
        mock_response = MagicMock()
        mock_response.text = '{"summary": "Test document", "score": 85}'

        with patch.object(service.client.models, 'generate_content', return_value=mock_response):
            result = service.generate(
                prompt="Analyze this",
                response_schema=TestSchema,
            )
            assert result["summary"] == "Test document"
            assert result["score"] == 85

    def test_generate_handles_empty_response(self):
        from app.services.gemini_service import GeminiService

        service = GeminiService()
        mock_response = MagicMock()
        mock_response.text = ""

        with patch.object(service.client.models, 'generate_content', return_value=mock_response):
            with pytest.raises(ValueError, match="empty"):
                service.generate(prompt="Test")

    def test_generate_handles_invalid_json(self):
        from pydantic import BaseModel, Field

        from app.services.gemini_service import GeminiService

        class TestSchema(BaseModel):
            value: str = Field(description="Test")

        service = GeminiService()
        mock_response = MagicMock()
        mock_response.text = "This is not JSON at all"

        with patch.object(service.client.models, 'generate_content', return_value=mock_response):
            with pytest.raises(ValueError, match="parse"):
                service.generate(prompt="Test", response_schema=TestSchema)

    def test_generate_extracts_json_from_markdown(self):
        from pydantic import BaseModel, Field

        from app.services.gemini_service import GeminiService

        class TestSchema(BaseModel):
            answer: str = Field(description="Answer")

        service = GeminiService()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"answer": "hello"}\n```'

        with patch.object(service.client.models, 'generate_content', return_value=mock_response):
            result = service.generate(prompt="Test", response_schema=TestSchema)
            assert result["answer"] == "hello"


class TestEndpointsIntegration:
    """Integration tests for document flow and error handling."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.main import app

        self.client = TestClient(app)

    def test_describe_situation_creates_session(self):
        """Describing a situation should return a document session and detected type."""
        response = self.client.post(
            "/api/documents/describe",
            json={"description": "My landlord is demanding 10 months security deposit in Pune.", "language": "en"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["detected_type"] == "rental"

    def test_clarify_nonexistent_session_returns_404(self):
        """Querying clarify for a non-existent document must return 404."""
        response = self.client.post("/api/documents/non-existent-session-id/clarify")
        assert response.status_code == 404

    def test_analyze_nonexistent_session_returns_404(self):
        """Querying analyze for an unknown document must return 404."""
        response = self.client.post("/api/documents/unknown-session-id/analyze")
        assert response.status_code == 404

    def test_ask_nonexistent_session_returns_404(self):
        """Querying ask for an unknown document must return 404."""
        response = self.client.post(
            "/api/documents/unknown-session-id/ask",
            json={"question": "Can I get my deposit back?"},
        )
        assert response.status_code == 404

    def test_export_nonexistent_session_returns_404(self):
        """Querying export for an unknown document must return 404."""
        response = self.client.post("/api/documents/unknown-session-id/export")
        assert response.status_code == 404

    def test_describe_then_export_flow(self):
        """Describe situation followed by export should generate a brief."""
        desc_resp = self.client.post(
            "/api/documents/describe",
            json={"description": "Defective refrigerator purchased with no warranty service provided.", "language": "en"},
        )
        assert desc_resp.status_code == 200
        doc_id = desc_resp.json()["document_id"]

        with patch("app.services.export_service.get_gemini_service") as mock_gemini_getter:
            mock_gemini = MagicMock()
            mock_payload = {
                "summary": "Consumer complaint regarding defective appliance.",
                "risk_flags": [],
                "document_overview": "Consumer complaint regarding defective appliance.",
                "unusual_findings": ["Failure to provide warranty support."],
                "questions_for_lawyer": ["Can I file a case in District Consumer Forum?"],
            }
            mock_gemini.generate_with_document.return_value = mock_payload
            mock_gemini.generate.return_value = mock_payload
            mock_gemini_getter.return_value = mock_gemini

            with patch("app.services.analysis_service.get_gemini_service", return_value=mock_gemini):
                export_resp = self.client.post(f"/api/documents/{doc_id}/export")
                assert export_resp.status_code == 200
                export_data = export_resp.json()
                assert export_data["document_id"] == doc_id
                assert "Lawyer Preparation Brief" in export_data["content"]


