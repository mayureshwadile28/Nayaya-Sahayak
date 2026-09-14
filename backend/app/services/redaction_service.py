"""PII redaction using high-performance regex + spaCy NER.

Redacts sensitive Indian PII (Aadhaar, PAN, phone, email, names, cards)
before any document text is logged or processed.
"""

import logging
import re
from typing import ClassVar

logger = logging.getLogger(__name__)


class RedactionService:
    """Redacts PII from text using regex patterns and spaCy NER.

    Configured for Indian PII patterns (Aadhaar, PAN, phone, email, names).
    Must be called before any document text is logged or persisted.
    """

    ENTITIES: ClassVar[list[str]] = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "LOCATION",
        "DATE_TIME",
        "IN_AADHAAR",
        "IN_PAN",
        "CREDIT_CARD",
        "IBAN_CODE",
        "IP_ADDRESS",
    ]

    PATTERNS: ClassVar[list[tuple[str, str, re.Pattern, float]]] = [
        (
            "IN_AADHAAR",
            "<AADHAAR>",
            re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"),
            0.85,
        ),
        (
            "IN_PAN",
            "<PAN>",
            re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
            0.90,
        ),
        (
            "EMAIL_ADDRESS",
            "<EMAIL>",
            re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
            0.95,
        ),
        (
            "PHONE_NUMBER",
            "<PHONE>",
            re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b|\b[6-9]\d{9}\b"),
            0.85,
        ),
        (
            "CREDIT_CARD",
            "<CREDIT_CARD>",
            re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b"),
            0.85,
        ),
    ]

    def __init__(self, nlp=None) -> None:
        """Initialize fast redaction service with optional shared spaCy NLP model."""
        self.nlp = nlp

    def _get_nlp(self):
        """Get or lazily load spaCy model."""
        if self.nlp is None:
            try:
                import spacy
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.warning("spaCy model load failed for RedactionService: %s", e)
        return self.nlp

    def redact(self, text: str, language: str = "en") -> str:
        """Redact PII from text. Returns redacted text.

        Args:
            text: The input text potentially containing PII.
            language: Language code for analysis.

        Returns:
            Text with PII replaced by placeholder tags like <PERSON>, <EMAIL>, etc.
        """
        if not text or not text.strip():
            return text

        redacted = text

        # 1. Redact regex patterns
        for _, tag, pattern, _ in self.PATTERNS:
            redacted = pattern.sub(tag, redacted)

        # 2. Redact Person names using spaCy NER
        nlp = self._get_nlp()
        if nlp is not None:
            try:
                doc = nlp(redacted[:50000])
                persons = [
                    ent.text.strip()
                    for ent in doc.ents
                    if ent.label_ == "PERSON" and len(ent.text.strip()) > 2
                ]
                persons = sorted(set(persons), key=len, reverse=True)
                if persons:
                    name_pattern = re.compile(r"\b(?:" + "|".join(map(re.escape, persons)) + r")\b")
                    redacted = name_pattern.sub("<PERSON>", redacted)
            except Exception as e:
                logger.warning("NER redaction error: %s", e)

        return redacted

    def analyze_pii(self, text: str, language: str = "en") -> list[dict[str, str | float]]:
        """Analyze text for PII without redacting. Returns detected entities."""
        if not text or not text.strip():
            return []

        entities: list[dict[str, str | float]] = []

        # Find regex matches
        for entity_type, _, pattern, score in self.PATTERNS:
            for match in pattern.finditer(text):
                entities.append({
                    "entity_type": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                    "score": score,
                })

        # Find NER matches
        nlp = self._get_nlp()
        if nlp is not None:
            try:
                doc = nlp(text[:50000])
                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        entities.append({
                            "entity_type": "PERSON",
                            "start": ent.start_char,
                            "end": ent.end_char,
                            "score": 0.85,
                        })
                    elif ent.label_ in ("GPE", "LOC"):
                        entities.append({
                            "entity_type": "LOCATION",
                            "start": ent.start_char,
                            "end": ent.end_char,
                            "score": 0.80,
                        })
            except Exception:
                pass

        entities.sort(key=lambda x: x["start"])
        return entities
