"""Integration tests for API endpoints with Gemini calls mocked."""

import pytest
from unittest.mock import patch, MagicMock
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
        from app.services.gemini_service import GeminiService
        from pydantic import BaseModel, Field

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
        from app.services.gemini_service import GeminiService
        from pydantic import BaseModel, Field

        class TestSchema(BaseModel):
            value: str = Field(description="Test")

        service = GeminiService()
        mock_response = MagicMock()
        mock_response.text = "This is not JSON at all"

        with patch.object(service.client.models, 'generate_content', return_value=mock_response):
            with pytest.raises(ValueError, match="parse"):
                service.generate(prompt="Test", response_schema=TestSchema)

    def test_generate_extracts_json_from_markdown(self):
        from app.services.gemini_service import GeminiService
        from pydantic import BaseModel, Field

        class TestSchema(BaseModel):
            answer: str = Field(description="Answer")

        service = GeminiService()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"answer": "hello"}\n```'

        with patch.object(service.client.models, 'generate_content', return_value=mock_response):
            result = service.generate(prompt="Test", response_schema=TestSchema)
            assert result["answer"] == "hello"
