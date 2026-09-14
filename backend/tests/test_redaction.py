"""Tests for PII redaction service — no network calls."""

import pytest


class TestRedactionService:
    """Tests for the Presidio-based PII redaction service."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.redaction_service import RedactionService
        self.service = RedactionService()

    def test_redact_email(self):
        text = "Contact me at john.doe@example.com for details."
        result = self.service.redact(text)
        assert "john.doe@example.com" not in result
        assert "<EMAIL>" in result

    def test_redact_phone(self):
        text = "Call me at 9876543210 or +91-98765-43210."
        result = self.service.redact(text)
        assert "9876543210" not in result

    def test_redact_aadhaar(self):
        text = "My Aadhaar number is 2345 6789 0123."
        result = self.service.redact(text)
        assert "2345 6789 0123" not in result
        assert "<AADHAAR>" in result

    def test_redact_pan(self):
        text = "PAN card number: ABCDE1234F for tax filing."
        result = self.service.redact(text)
        assert "ABCDE1234F" not in result
        assert "<PAN>" in result

    def test_redact_person_name(self):
        text = "This agreement is between Rajesh Kumar and Priya Sharma."
        result = self.service.redact(text)
        # Person names should be redacted
        assert "<PERSON>" in result

    def test_empty_text(self):
        assert self.service.redact("") == ""
        assert self.service.redact("   ") == "   "

    def test_no_pii(self):
        text = "The landlord agrees to paint the walls."
        result = self.service.redact(text)
        # Should remain mostly unchanged (no PII to redact)
        assert "paint the walls" in result

    def test_multiple_pii(self):
        text = (
            "Name: Amit Patel, Email: amit@test.com, "
            "PAN: FGHIJ5678K, Phone: 9988776655"
        )
        result = self.service.redact(text)
        assert "amit@test.com" not in result
        assert "FGHIJ5678K" not in result

    def test_analyze_returns_entities(self):
        text = "Contact: test@email.com, PAN: ABCDE1234F"
        entities = self.service.analyze_pii(text)
        assert len(entities) > 0
        entity_types = [e["entity_type"] for e in entities]
        assert "EMAIL_ADDRESS" in entity_types or "IN_PAN" in entity_types
