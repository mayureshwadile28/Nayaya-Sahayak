"""Deterministic legal NLP extraction using spaCy + regex patterns.

Extracts clauses, parties, dates, amounts, and classifies risk per document type.
This replaces/supplements LexNLP with equivalent functionality that works on Python 3.13.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import ClassVar

import spacy
from spacy.language import Language as SpacyLanguage

from app.models.schemas import DocumentType, RiskSeverity

logger = logging.getLogger(__name__)


@dataclass
class ExtractedClause:
    """A clause extracted from a document with its risk assessment."""

    text: str
    category: str
    severity: RiskSeverity
    reason: str
    legal_reference: str | None = None


@dataclass
class ExtractionResult:
    """Complete extraction result from document analysis."""

    document_type: DocumentType = DocumentType.UNKNOWN
    parties: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    amounts: list[str] = field(default_factory=list)
    clauses: list[ExtractedClause] = field(default_factory=list)
    key_terms: dict[str, str] = field(default_factory=dict)


# --- Helper functions for dynamic clause checking ---

def _check_deposit_amount(match: re.Match) -> tuple[RiskSeverity, str]:
    """Check if security deposit amount seems excessive."""
    text = match.group(0).lower()
    months_match = re.search(r"(\d+)\s*months?", text)
    if months_match:
        months = int(months_match.group(1))
        if months > 3:
            return (
                RiskSeverity.HIGH,
                f"Security deposit of {months} months is unusually high — most state Rent Control Acts cap it at 1-3 months",
            )
        if months > 2:
            return (
                RiskSeverity.MEDIUM,
                f"Security deposit of {months} months — check your state's Rent Control Act for applicable caps",
            )
    return (
        RiskSeverity.LOW,
        "Security deposit clause present — amount appears within common range",
    )


def _check_lock_in(match: re.Match) -> tuple[RiskSeverity, str]:
    """Check if lock-in period is unreasonably long."""
    text = match.group(0).lower()
    months_match = re.search(r"(\d+)\s*months?", text)
    years_match = re.search(r"(\d+)\s*years?", text)

    total_months = 0
    if months_match:
        total_months = int(months_match.group(1))
    if years_match:
        total_months = int(years_match.group(1)) * 12

    if total_months > 12:
        return (
            RiskSeverity.HIGH,
            f"Lock-in period of {total_months} months is very long — you cannot terminate the agreement during this time",
        )
    if total_months > 6:
        return (
            RiskSeverity.MEDIUM,
            f"Lock-in period of {total_months} months — ensure you are comfortable with this commitment",
        )
    return (
        RiskSeverity.LOW,
        "Lock-in period is within common range",
    )


def _check_notice_period(match: re.Match) -> tuple[RiskSeverity, str]:
    """Check if rental notice period is adequate."""
    text = match.group(0).lower()
    days_match = re.search(r"(\d+)\s*days?", text)
    months_match = re.search(r"(\d+)\s*months?", text)

    if days_match:
        days = int(days_match.group(1))
        if days < 15:
            return (
                RiskSeverity.HIGH,
                f"Notice period of only {days} days is very short — may not provide adequate time to vacate",
            )
    if months_match:
        months = int(months_match.group(1))
        if months > 3:
            return (
                RiskSeverity.MEDIUM,
                f"Notice period of {months} months is lengthy — confirm you are comfortable with this requirement",
            )
    return (
        RiskSeverity.LOW,
        "Notice period clause present — appears within common range",
    )


def _check_probation(match: re.Match) -> tuple[RiskSeverity, str]:
    """Check if probation period is unusually long."""
    text = match.group(0).lower()
    months_match = re.search(r"(\d+)\s*months?", text)

    if months_match:
        months = int(months_match.group(1))
        if months > 6:
            return (
                RiskSeverity.HIGH,
                f"Probation period of {months} months is unusually long — standard is 3-6 months",
            )
    return (
        RiskSeverity.LOW,
        "Probation period appears within standard range",
    )


def _check_employment_notice(match: re.Match) -> tuple[RiskSeverity, str]:
    """Check employment notice period reasonableness."""
    text = match.group(0).lower()
    months_match = re.search(r"(\d+)\s*months?", text)
    days_match = re.search(r"(\d+)\s*days?", text)

    if months_match:
        months = int(months_match.group(1))
        if months > 3:
            return (
                RiskSeverity.HIGH,
                f"Notice period of {months} months is long — may significantly delay your ability to switch jobs",
            )
    if days_match:
        days = int(days_match.group(1))
        if days > 90:
            return (
                RiskSeverity.MEDIUM,
                f"Notice period of {days} days — check if this is reciprocal (same for employer)",
            )
    return (
        RiskSeverity.LOW,
        "Employment notice period is within common range",
    )


def _check_defect_window(match: re.Match) -> tuple[RiskSeverity, str]:
    """Check if defect reporting window is unreasonably short."""
    text = match.group(0).lower()
    days_match = re.search(r"(\d+)\s*days?", text)
    hours_match = re.search(r"(\d+)\s*hours?", text)

    if hours_match:
        hours = int(hours_match.group(1))
        if hours < 48:
            return (
                RiskSeverity.HIGH,
                f"Defect reporting window of only {hours} hours is very restrictive",
            )
    if days_match:
        days = int(days_match.group(1))
        if days < 3:
            return (
                RiskSeverity.HIGH,
                f"Defect reporting window of only {days} days is very short — may unfairly limit your ability to claim",
            )
    return (
        RiskSeverity.LOW,
        "Defect reporting window is present",
    )


# Precompiled currency pattern
_INR_PATTERN = re.compile(r"(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d{1,2})?")

# Precompiled key-term patterns for performance
_RENTAL_TERMS = {
    "monthly_rent": re.compile(r"(?:monthly\s*rent|rent\s*(?:of|amount))[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+)", re.IGNORECASE),
    "security_deposit": re.compile(r"security\s*deposit[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+|\d+\s*months?)", re.IGNORECASE),
    "lock_in_period": re.compile(r"lock[\s-]*in\s*period[^.]*?(\d+\s*(?:months?|years?))", re.IGNORECASE),
    "notice_period": re.compile(r"notice\s*period[^.]*?(\d+\s*(?:days?|months?))", re.IGNORECASE),
}

_EMPLOYMENT_TERMS = {
    "compensation": re.compile(r"(?:ctc|salary|compensation|remuneration)[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+(?:\s*(?:per\s*annum|p\.a\.|per\s*month|p\.m\.))?)", re.IGNORECASE),
    "probation": re.compile(r"probation\s*period[^.]*?(\d+\s*(?:months?|days?))", re.IGNORECASE),
    "notice_period": re.compile(r"notice\s*period[^.]*?(\d+\s*(?:days?|months?))", re.IGNORECASE),
    "non_compete_duration": re.compile(r"non[\s-]*compete[^.]*?(\d+\s*(?:months?|years?))", re.IGNORECASE),
}

_CONSUMER_TERMS = {
    "amount_claimed": re.compile(r"(?:claim|amount|refund|compensation)[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+)", re.IGNORECASE),
    "reporting_window": re.compile(r"(?:report|notify|inform)[^.]*?(\d+\s*(?:days?|hours?))", re.IGNORECASE),
}


class ExtractionService:
    """Deterministic clause and entity extraction using spaCy and regex.

    Models are loaded once at startup via load_models().
    Patterns are pre-compiled for maximum throughput.
    """

    # --- Document type detection patterns (pre-compiled for ultra-fast classification) ---
    TYPE_PATTERNS: ClassVar[dict[DocumentType, list[re.Pattern]]] = {
        DocumentType.RENTAL: [
            re.compile(p, re.IGNORECASE) for p in [
                r"rent\s*agreement",
                r"lease\s*(agreement|deed)",
                r"tenancy\s*agreement",
                r"landlord.*tenant",
                r"security\s*deposit",
                r"lock[\s-]*in\s*period",
                r"monthly\s*rent",
                r"premises\s*(situated|located)",
                r"lessor.*lessee",
            ]
        ],
        DocumentType.EMPLOYMENT: [
            re.compile(p, re.IGNORECASE) for p in [
                r"employment\s*(agreement|contract|letter)",
                r"offer\s*letter",
                r"appointment\s*letter",
                r"terms\s*of\s*employment",
                r"non[\s-]*compete",
                r"termination\s*clause",
                r"probation\s*period",
                r"compensation\s*(and\s*benefits|package)",
                r"gig[\s-]*work",
                r"platform\s*worker",
                r"independent\s*contractor",
            ]
        ],
        DocumentType.CONSUMER: [
            re.compile(p, re.IGNORECASE) for p in [
                r"consumer\s*(complaint|dispute|notice|forum)",
                r"defective\s*product",
                r"refund\s*(denied|rejection|claim)",
                r"service\s*deficiency",
                r"warranty\s*claim",
                r"e[\s-]*commerce",
                r"legal\s*notice",
                r"compensation\s*claim",
                r"consumer\s*protection\s*act",
            ]
        ],
    }

    # --- Clause patterns per document type with risk assessment (precompiled) ---
    RENTAL_CLAUSE_PATTERNS: ClassVar[list[dict]] = [
        {
            "pattern": re.compile(r"security\s*deposit.{0,200}?(\d+\s*months?|\d[\d,]*)", re.IGNORECASE | re.DOTALL),
            "category": "security_deposit",
            "check": _check_deposit_amount,
        },
        {
            "pattern": re.compile(r"lock[\s-]*in\s*period[^.]*?(\d+\s*(?:months?|years?))", re.IGNORECASE | re.DOTALL),
            "category": "lock_in_period",
            "check": _check_lock_in,
        },
        {
            "pattern": re.compile(r"notice\s*period[^.]*?(\d+\s*(?:days?|months?))", re.IGNORECASE | re.DOTALL),
            "category": "notice_period",
            "check": _check_notice_period,
        },
        {
            "pattern": re.compile(r"(eviction|vacate|terminate)[^.]{0,200}(immediately|without\s*notice|at\s*(?:sole\s*)?discretion)", re.IGNORECASE | re.DOTALL),
            "category": "eviction",
            "severity": RiskSeverity.HIGH,
            "reason": "Contains a clause allowing eviction without proper notice — may conflict with Rent Control Act provisions",
        },
        {
            "pattern": re.compile(r"maintenance[^.]*?(tenant|lessee)\s*(shall|will|is\s*responsible)", re.IGNORECASE | re.DOTALL),
            "category": "maintenance",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Maintenance responsibility assigned to tenant — verify which repairs are structural vs. routine",
        },
        {
            "pattern": re.compile(r"rent\s*(?:shall\s*)?(?:be\s*)?(?:increased|escalat|revis)[^.]*?(\d+\s*%|\d+\s*percent)", re.IGNORECASE | re.DOTALL),
            "category": "rent_escalation",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Rent escalation clause found — check if the increase percentage is within state-regulated limits",
        },
        {
            "pattern": re.compile(r"(forfeiture|forfeit)[^.]*?deposit", re.IGNORECASE | re.DOTALL),
            "category": "deposit_forfeiture",
            "severity": RiskSeverity.HIGH,
            "reason": "Deposit forfeiture clause — landlord may withhold deposit under broad conditions",
        },
    ]

    EMPLOYMENT_CLAUSE_PATTERNS: ClassVar[list[dict]] = [
        {
            "pattern": re.compile(r"non[\s-]*compete[^.]*?(\d+\s*(?:months?|years?))", re.IGNORECASE | re.DOTALL),
            "category": "non_compete",
            "severity": RiskSeverity.HIGH,
            "reason": "Non-compete clause — Indian courts generally do not enforce post-employment non-compete (Section 27, Indian Contract Act)",
            "legal_reference": "Section 27, Indian Contract Act, 1872",
        },
        {
            "pattern": re.compile(r"termination[^.]*?(without\s*(?:cause|reason)|at[\s-]*will|immediate(?:ly)?)", re.IGNORECASE | re.DOTALL),
            "category": "termination",
            "severity": RiskSeverity.HIGH,
            "reason": "Termination without cause clause — check if notice period and severance provisions are adequate",
        },
        {
            "pattern": re.compile(r"probation[^.]*?(\d+\s*(?:months?|days?))", re.IGNORECASE | re.DOTALL),
            "category": "probation",
            "check": _check_probation,
        },
        {
            "pattern": re.compile(r"intellectual\s*property|invention\s*assignment|work\s*(?:made\s*)?for\s*hire", re.IGNORECASE | re.DOTALL),
            "category": "ip_assignment",
            "severity": RiskSeverity.MEDIUM,
            "reason": "IP assignment clause — confirm it only covers work done during employment and within scope of duties",
        },
        {
            "pattern": re.compile(r"indemnity|indemnif", re.IGNORECASE | re.DOTALL),
            "category": "indemnity",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Employee indemnity clause — check if you are being made personally liable for employer losses",
        },
        {
            "pattern": re.compile(r"(?:employment|training)\s*bond|service\s*agreement[^.]*?(\d+\s*(?:months?|years?)|(?:Rs\.?|INR|₹)\s*[\d,]+)", re.IGNORECASE | re.DOTALL),
            "category": "employment_bond",
            "severity": RiskSeverity.HIGH,
            "reason": "Employment bond detected — bonds requiring payment to leave are generally restricted under Indian law",
            "legal_reference": "Section 27, Indian Contract Act, 1872",
        },
        {
            "pattern": re.compile(r"notice\s*period[^.]*?(\d+\s*(?:days?|months?))", re.IGNORECASE | re.DOTALL),
            "category": "notice_period",
            "check": _check_employment_notice,
        },
    ]

    CONSUMER_CLAUSE_PATTERNS: ClassVar[list[dict]] = [
        {
            "pattern": re.compile(r"no\s*refund|non[\s-]*refundable|all\s*sales\s*(?:are\s*)?final", re.IGNORECASE | re.DOTALL),
            "category": "no_refund",
            "severity": RiskSeverity.HIGH,
            "reason": "'No refund' clause may be an unfair trade practice under Consumer Protection Act 2019",
            "legal_reference": "Section 2(47), Consumer Protection Act, 2019",
        },
        {
            "pattern": re.compile(r"warranty\s*(?:is\s*)?void|void\s*if|as[\s-]*is\s*(?:basis|condition)", re.IGNORECASE | re.DOTALL),
            "category": "warranty_void",
            "severity": RiskSeverity.HIGH,
            "reason": "Warranty disclaimer clause — sellers cannot completely contract out of basic statutory warranty",
            "legal_reference": "Consumer Protection Act, 2019",
        },
        {
            "pattern": re.compile(r"(limitation\s*of\s*liability|maximum\s*liability)[^.]*?(?:exceed|limited\s*to)[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+|price\s*paid)", re.IGNORECASE | re.DOTALL),
            "category": "liability_limitation",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Liability limitation clause — caps damages to purchase price, which may be contested for defective products",
        },
        {
            "pattern": re.compile(r"jurisdiction[^.]*?(courts?\s*(?:at|in|of)\s*([A-Za-z\s]+))", re.IGNORECASE | re.DOTALL),
            "category": "jurisdiction",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Exclusive jurisdiction clause — consumers can generally file complaints where they reside under CPA 2019",
            "legal_reference": "Section 34, Consumer Protection Act, 2019",
        },
        {
            "pattern": re.compile(r"arbitrat(ion|or)|dispute\s*resolution[^.]*?arbitrat", re.IGNORECASE | re.DOTALL),
            "category": "arbitration",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Mandatory arbitration clause — may limit access to consumer forums",
        },
        {
            "pattern": re.compile(r"(defect|deficient|deficiency)[^.]{0,200}(report|notify|inform)[^.]*?(\d+\s*(?:days?|hours?))", re.IGNORECASE | re.DOTALL),
            "category": "defect_reporting_window",
            "check": _check_defect_window,
        },
    ]

    def __init__(self) -> None:
        """Initialize the extraction service (models loaded separately via load_models)."""
        self.nlp: SpacyLanguage | None = None

    def load_models(self) -> None:
        """Load spaCy model. Called once at startup."""
        logger.info("Loading spaCy model en_core_web_sm...")
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded.")
        except Exception as e:
            logger.warning("spaCy model en_core_web_sm could not be loaded: %s", e)
            self.nlp = None

    def detect_document_type(self, text: str) -> DocumentType:
        """Detect the document type from text content using precompiled regex patterns."""
        text_lower = text.lower()
        scores: dict[DocumentType, int] = dict.fromkeys(DocumentType, 0)

        for doc_type, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                matches = pattern.findall(text_lower)
                scores[doc_type] += len(matches)

        best_type = max(scores, key=lambda k: scores[k])
        if scores[best_type] == 0:
            return DocumentType.UNKNOWN

        return best_type

    def extract(self, text: str, document_type: DocumentType | None = None) -> ExtractionResult:
        """Run full extraction: entities, clauses, and risk flags.

        Args:
            text: The document text to analyze.
            document_type: If known, skip type detection.

        Returns:
            ExtractionResult with all extracted information.
        """
        if self.nlp is None:
            self.load_models()

        # Detect type if not provided
        if document_type is None:
            document_type = self.detect_document_type(text)

        result = ExtractionResult(document_type=document_type)

        seen_persons: set[str] = set()
        seen_dates: set[str] = set()
        seen_amounts: set[str] = set()

        # Extract entities via spaCy NER if available
        if self.nlp is not None:
            try:
                doc = self.nlp(text[:100000])  # Limit to avoid memory issues
                for ent in doc.ents:
                    if ent.label_ == "PERSON" and ent.text not in seen_persons:
                        result.parties.append(ent.text)
                        seen_persons.add(ent.text)
                    elif ent.label_ == "DATE" and ent.text not in seen_dates:
                        result.dates.append(ent.text)
                        seen_dates.add(ent.text)
                    elif ent.label_ == "MONEY" and ent.text not in seen_amounts:
                        result.amounts.append(ent.text)
                        seen_amounts.add(ent.text)
            except Exception as e:
                logger.warning("spaCy NER extraction failed: %s", e)

        # Extract amounts via precompiled regex (Indian currency patterns)
        for match in _INR_PATTERN.finditer(text):
            amount_text = match.group().strip()
            if amount_text not in seen_amounts:
                result.amounts.append(amount_text)
                seen_amounts.add(amount_text)

        # Extract clauses based on document type
        clause_patterns = self._get_clause_patterns(document_type)
        for pattern_def in clause_patterns:
            for match in pattern_def["pattern"].finditer(text):
                clause_text = match.group(0).strip()[:300]  # Cap length

                # If pattern has a dynamic check function, use it
                if "check" in pattern_def:
                    severity, reason = pattern_def["check"](match)
                else:
                    severity = pattern_def.get("severity", RiskSeverity.LOW)
                    reason = pattern_def.get("reason", "Clause flagged for review")

                clause = ExtractedClause(
                    text=clause_text,
                    category=pattern_def["category"],
                    severity=severity,
                    reason=reason,
                    legal_reference=pattern_def.get("legal_reference"),
                )
                result.clauses.append(clause)

        # Extract key terms
        result.key_terms = self._extract_key_terms(text, document_type)

        return result

    def _get_clause_patterns(self, document_type: DocumentType) -> list[dict]:
        """Get the clause patterns for a specific document type."""
        pattern_map = {
            DocumentType.RENTAL: self.RENTAL_CLAUSE_PATTERNS,
            DocumentType.EMPLOYMENT: self.EMPLOYMENT_CLAUSE_PATTERNS,
            DocumentType.CONSUMER: self.CONSUMER_CLAUSE_PATTERNS,
        }
        return pattern_map.get(document_type, [])

    def _extract_key_terms(self, text: str, document_type: DocumentType) -> dict[str, str]:
        """Extract key terms specific to the document type."""
        terms: dict[str, str] = {}

        if document_type == DocumentType.RENTAL:
            for term_name, pat in _RENTAL_TERMS.items():
                m = pat.search(text)
                if m:
                    terms[term_name] = m.group(1).strip()
        elif document_type == DocumentType.EMPLOYMENT:
            for term_name, pat in _EMPLOYMENT_TERMS.items():
                m = pat.search(text)
                if m:
                    terms[term_name] = m.group(1).strip()
        elif document_type == DocumentType.CONSUMER:
            for term_name, pat in _CONSUMER_TERMS.items():
                m = pat.search(text)
                if m:
                    terms[term_name] = m.group(1).strip()

        return terms
