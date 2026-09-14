"""PII redaction using Microsoft Presidio. Runs BEFORE any persistence or logging."""

import logging
from typing import ClassVar

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)


class RedactionService:
    """Redacts PII from text using Microsoft Presidio.

    Configured for Indian PII patterns (Aadhaar, PAN, phone, email, names).
    Must be called before any document text is logged or persisted.
    """

    # Entity types to detect and redact
    ENTITIES: ClassVar[list[str]] = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "LOCATION",
        "DATE_TIME",
        "IN_AADHAAR",  # Indian Aadhaar number
        "IN_PAN",      # Indian PAN number
        "CREDIT_CARD",
        "IBAN_CODE",
        "IP_ADDRESS",
    ]

    def __init__(self) -> None:
        """Initialize Presidio analyzer and anonymizer engines."""
        logger.info("Initializing Presidio redaction service...")

        # Configure NLP engine with spaCy
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        })
        nlp_engine = provider.create_engine()

        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        self.anonymizer = AnonymizerEngine()

        # Register Indian-specific recognizers
        self._register_indian_recognizers()

        logger.info("Presidio redaction service ready.")

    def _register_indian_recognizers(self) -> None:
        """Register custom recognizers for Indian PII patterns."""
        from presidio_analyzer import Pattern, PatternRecognizer

        # Aadhaar number: 12 digits, often formatted as XXXX XXXX XXXX
        aadhaar_recognizer = PatternRecognizer(
            supported_entity="IN_AADHAAR",
            name="Indian Aadhaar Recognizer",
            patterns=[
                Pattern(
                    name="aadhaar_pattern",
                    regex=r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b",
                    score=0.85,
                ),
            ],
            supported_language="en",
        )
        self.analyzer.registry.add_recognizer(aadhaar_recognizer)

        # PAN number: ABCDE1234F format
        pan_recognizer = PatternRecognizer(
            supported_entity="IN_PAN",
            name="Indian PAN Recognizer",
            patterns=[
                Pattern(
                    name="pan_pattern",
                    regex=r"\b[A-Z]{5}\d{4}[A-Z]\b",
                    score=0.9,
                ),
            ],
            supported_language="en",
        )
        self.analyzer.registry.add_recognizer(pan_recognizer)

    def redact(self, text: str, language: str = "en") -> str:
        """Redact PII from text. Returns redacted text.

        Args:
            text: The input text potentially containing PII.
            language: Language code for analysis.

        Returns:
            Text with PII replaced by placeholder tags like <PERSON>, <EMAIL_ADDRESS>, etc.
        """
        if not text or not text.strip():
            return text

        # Analyze for PII entities
        results: list[RecognizerResult] = self.analyzer.analyze(
            text=text,
            language=language,
            entities=self.ENTITIES,
        )

        if not results:
            return text

        # Anonymize with entity-type placeholders
        operators = {
            "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
            "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
            "IN_AADHAAR": OperatorConfig("replace", {"new_value": "<AADHAAR>"}),
            "IN_PAN": OperatorConfig("replace", {"new_value": "<PAN>"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<CREDIT_CARD>"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
        }

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )

        logger.debug("Redacted %d PII entities from text.", len(results))
        return anonymized.text

    def analyze_pii(self, text: str, language: str = "en") -> list[dict[str, str | float]]:
        """Analyze text for PII without redacting. Returns detected entities.

        Useful for reporting what was found without modifying text.
        """
        if not text or not text.strip():
            return []

        results = self.analyzer.analyze(
            text=text,
            language=language,
            entities=self.ENTITIES,
        )

        return [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": r.score,
            }
            for r in results
        ]
