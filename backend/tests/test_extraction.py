"""Tests for deterministic legal NLP extraction — no network calls."""

import pytest
from app.models.schemas import DocumentType, RiskSeverity
from app.services.extraction_service import ExtractionService


class TestDocumentTypeDetection:
    """Tests for document type classification."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ExtractionService()
        self.service.load_models()

    def test_detect_rental(self, sample_rental_text):
        result = self.service.detect_document_type(sample_rental_text)
        assert result == DocumentType.RENTAL

    def test_detect_employment(self, sample_employment_text):
        result = self.service.detect_document_type(sample_employment_text)
        assert result == DocumentType.EMPLOYMENT

    def test_detect_consumer(self, sample_consumer_text):
        result = self.service.detect_document_type(sample_consumer_text)
        assert result == DocumentType.CONSUMER

    def test_detect_unknown(self):
        result = self.service.detect_document_type("This is a random text with no legal terms.")
        assert result == DocumentType.UNKNOWN


class TestRentalExtraction:
    """Tests for rental agreement clause extraction."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ExtractionService()
        self.service.load_models()

    def test_extract_rental_clauses(self, sample_rental_text):
        result = self.service.extract(sample_rental_text, DocumentType.RENTAL)
        categories = [c.category for c in result.clauses]

        # Should detect excessive security deposit (6 months)
        assert "security_deposit" in categories

        # Should detect long lock-in (18 months)
        assert "lock_in_period" in categories

        # Should detect unilateral eviction
        assert "eviction" in categories

    def test_high_deposit_flagged(self, sample_rental_text):
        result = self.service.extract(sample_rental_text, DocumentType.RENTAL)
        deposit_flags = [c for c in result.clauses if c.category == "security_deposit"]
        assert len(deposit_flags) > 0
        assert deposit_flags[0].severity == RiskSeverity.HIGH

    def test_eviction_clause_high_risk(self, sample_rental_text):
        result = self.service.extract(sample_rental_text, DocumentType.RENTAL)
        eviction_flags = [c for c in result.clauses if c.category == "eviction"]
        assert len(eviction_flags) > 0
        assert eviction_flags[0].severity == RiskSeverity.HIGH

    def test_extract_amounts(self, sample_rental_text):
        result = self.service.extract(sample_rental_text, DocumentType.RENTAL)
        assert len(result.amounts) > 0

    def test_deposit_forfeiture_flagged(self, sample_rental_text):
        result = self.service.extract(sample_rental_text, DocumentType.RENTAL)
        forfeiture_flags = [c for c in result.clauses if c.category == "deposit_forfeiture"]
        assert len(forfeiture_flags) > 0
        assert forfeiture_flags[0].severity == RiskSeverity.HIGH


class TestEmploymentExtraction:
    """Tests for employment agreement extraction."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ExtractionService()
        self.service.load_models()

    def test_extract_non_compete(self, sample_employment_text):
        result = self.service.extract(sample_employment_text, DocumentType.EMPLOYMENT)
        categories = [c.category for c in result.clauses]
        assert "non_compete" in categories

    def test_non_compete_high_risk(self, sample_employment_text):
        result = self.service.extract(sample_employment_text, DocumentType.EMPLOYMENT)
        nc_flags = [c for c in result.clauses if c.category == "non_compete"]
        assert len(nc_flags) > 0
        assert nc_flags[0].severity == RiskSeverity.HIGH

    def test_termination_flagged(self, sample_employment_text):
        result = self.service.extract(sample_employment_text, DocumentType.EMPLOYMENT)
        term_flags = [c for c in result.clauses if c.category == "termination"]
        assert len(term_flags) > 0

    def test_probation_flagged(self, sample_employment_text):
        result = self.service.extract(sample_employment_text, DocumentType.EMPLOYMENT)
        prob_flags = [c for c in result.clauses if c.category == "probation"]
        assert len(prob_flags) > 0
        # 9 months probation should be high risk
        assert prob_flags[0].severity == RiskSeverity.HIGH

    def test_ip_assignment_flagged(self, sample_employment_text):
        result = self.service.extract(sample_employment_text, DocumentType.EMPLOYMENT)
        ip_flags = [c for c in result.clauses if c.category == "ip_assignment"]
        assert len(ip_flags) > 0


class TestConsumerExtraction:
    """Tests for consumer dispute extraction."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ExtractionService()
        self.service.load_models()

    def test_no_refund_flagged(self, sample_consumer_text):
        result = self.service.extract(sample_consumer_text, DocumentType.CONSUMER)
        categories = [c.category for c in result.clauses]
        assert "no_refund" in categories

    def test_no_refund_high_risk(self, sample_consumer_text):
        result = self.service.extract(sample_consumer_text, DocumentType.CONSUMER)
        refund_flags = [c for c in result.clauses if c.category == "no_refund"]
        assert len(refund_flags) > 0
        assert refund_flags[0].severity == RiskSeverity.HIGH

    def test_jurisdiction_flagged(self, sample_consumer_text):
        result = self.service.extract(sample_consumer_text, DocumentType.CONSUMER)
        categories = [c.category for c in result.clauses]
        assert "jurisdiction" in categories

    def test_warranty_void_flagged(self, sample_consumer_text):
        result = self.service.extract(sample_consumer_text, DocumentType.CONSUMER)
        categories = [c.category for c in result.clauses]
        assert "warranty_void" in categories


class TestKeyTermExtraction:
    """Tests for key term extraction."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = ExtractionService()
        self.service.load_models()

    def test_rental_key_terms(self, sample_rental_text):
        result = self.service.extract(sample_rental_text, DocumentType.RENTAL)
        assert "monthly_rent" in result.key_terms or len(result.amounts) > 0

    def test_severity_always_has_text_label(self, sample_rental_text):
        """Verify that severity is always a valid enum value (text label, not color)."""
        result = self.service.extract(sample_rental_text, DocumentType.RENTAL)
        for clause in result.clauses:
            assert clause.severity in (RiskSeverity.HIGH, RiskSeverity.MEDIUM, RiskSeverity.LOW)
            assert isinstance(clause.severity.value, str)
