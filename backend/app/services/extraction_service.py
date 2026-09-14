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


class ExtractionService:
    """Deterministic clause and entity extraction using spaCy and regex.

    Models are loaded once at startup via load_models().
    """

    # --- Document type detection patterns ---
    TYPE_PATTERNS: ClassVar[dict[DocumentType, list[str]]] = {
        DocumentType.RENTAL: [
            r"rent\s*agreement",
            r"lease\s*(agreement|deed)",
            r"tenancy\s*agreement",
            r"landlord.*tenant",
            r"security\s*deposit",
            r"lock[\s-]*in\s*period",
            r"monthly\s*rent",
            r"premises\s*(situated|located)",
            r"lessor.*lessee",
        ],
        DocumentType.EMPLOYMENT: [
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
        ],
        DocumentType.CONSUMER: [
            r"consumer\s*(complaint|dispute|notice|forum)",
            r"defective\s*product",
            r"refund\s*(denied|rejection|claim)",
            r"service\s*deficiency",
            r"warranty\s*claim",
            r"e[\s-]*commerce",
            r"legal\s*notice",
            r"compensation\s*claim",
            r"consumer\s*protection\s*act",
        ],
    }

    # --- Clause patterns per document type with risk assessment ---
    RENTAL_CLAUSE_PATTERNS: ClassVar[list[dict]] = [
        {
            "pattern": r"security\s*deposit.{0,200}?(\d+\s*months?|\d[\d,]*)",
            "category": "security_deposit",
            "check": lambda m: _check_deposit_amount(m),
        },
        {
            "pattern": r"lock[\s-]*in\s*period[^.]*?(\d+\s*(?:months?|years?))",
            "category": "lock_in_period",
            "check": lambda m: _check_lock_in(m),
        },
        {
            "pattern": r"notice\s*period[^.]*?(\d+\s*(?:days?|months?))",
            "category": "notice_period",
            "check": lambda m: _check_notice_period(m),
        },
        {
            "pattern": r"(eviction|vacate|terminate)[^.]{0,200}(immediately|without\s*notice|at\s*(?:sole\s*)?discretion)",
            "category": "eviction",
            "severity": RiskSeverity.HIGH,
            "reason": "Contains a clause allowing eviction without proper notice — may conflict with Rent Control Act provisions",
        },
        {
            "pattern": r"maintenance[^.]*?(tenant|lessee)\s*(shall|will|is\s*responsible)",
            "category": "maintenance",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Maintenance responsibility assigned to tenant — verify which repairs are structural vs. routine",
        },
        {
            "pattern": r"rent\s*(?:shall\s*)?(?:be\s*)?(?:increased|escalat|revis)[^.]*?(\d+\s*%|\d+\s*percent)",
            "category": "rent_escalation",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Rent escalation clause found — check if the increase percentage is within state-regulated limits",
        },
        {
            "pattern": r"(forfeiture|forfeit)[^.]*?deposit",
            "category": "deposit_forfeiture",
            "severity": RiskSeverity.HIGH,
            "reason": "Deposit forfeiture clause — landlord may withhold deposit under broad conditions",
        },
    ]

    EMPLOYMENT_CLAUSE_PATTERNS: ClassVar[list[dict]] = [
        {
            "pattern": r"non[\s-]*compete[^.]*?(\d+\s*(?:months?|years?))",
            "category": "non_compete",
            "severity": RiskSeverity.HIGH,
            "reason": "Non-compete clause — Indian courts generally do not enforce post-employment non-compete (Section 27, Indian Contract Act)",
            "legal_reference": "Section 27, Indian Contract Act, 1872",
        },
        {
            "pattern": r"termination[^.]*?(without\s*(?:cause|reason)|at[\s-]*will|immediate(?:ly)?)",
            "category": "termination",
            "severity": RiskSeverity.HIGH,
            "reason": "Termination without cause clause — check if notice period and severance provisions are adequate",
        },
        {
            "pattern": r"probation[^.]*?(\d+\s*(?:months?|days?))",
            "category": "probation",
            "check": lambda m: _check_probation(m),
        },
        {
            "pattern": r"intellectual\s*property[^.]*?(assign|transfer|belong)[^.]*?(company|employer|organization)",
            "category": "ip_assignment",
            "severity": RiskSeverity.MEDIUM,
            "reason": "IP assignment clause — all work product may belong to employer, including potentially personal projects",
        },
        {
            "pattern": r"notice\s*period[^.]*?(\d+\s*(?:days?|months?))",
            "category": "notice_period",
            "check": lambda m: _check_employment_notice(m),
        },
        {
            "pattern": r"(salary|compensation|payment)[^.]*?delay|delayed\s*(?:salary|payment|compensation)",
            "category": "payment_delay",
            "severity": RiskSeverity.HIGH,
            "reason": "Payment delay provisions — wages must be paid on time per Payment of Wages Act",
            "legal_reference": "Payment of Wages Act, 1936",
        },
        {
            "pattern": r"(garden\s*leave|gardening\s*leave)",
            "category": "garden_leave",
            "severity": RiskSeverity.LOW,
            "reason": "Garden leave clause present — employer may keep you on payroll but not working during notice",
        },
    ]

    CONSUMER_CLAUSE_PATTERNS: ClassVar[list[dict]] = [
        {
            "pattern": r"(no\s*refund|non[\s-]*refundable|refund\s*(?:will\s*)?not\s*(?:be\s*)?(?:given|provided|applicable))",
            "category": "no_refund",
            "severity": RiskSeverity.HIGH,
            "reason": "No-refund clause — may violate Consumer Protection Act, 2019 provisions on deficiency of service",
            "legal_reference": "Consumer Protection Act, 2019 — Section 2(6)",
        },
        {
            "pattern": r"(warranty|guarantee).{0,50}?(void|null|invalid).{0,200}?(unauthorized|third[\s-]*party|modification)",
            "category": "warranty_void",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Broad warranty voiding conditions — check if they unfairly restrict consumer rights",
        },
        {
            "pattern": r"jurisdiction[^.]*?(only|exclusive|sole)[^.]*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "category": "jurisdiction",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Exclusive jurisdiction clause — consumers have the right to file in their local district forum",
            "legal_reference": "Consumer Protection Act, 2019 — Section 34",
        },
        {
            "pattern": r"(arbitration\s*clause|binding\s*arbitration|dispute.*arbitrat)",
            "category": "arbitration",
            "severity": RiskSeverity.MEDIUM,
            "reason": "Mandatory arbitration clause — may limit access to consumer forums",
        },
        {
            "pattern": r"(defect|deficient|deficiency)[^.]{0,200}(report|notify|inform)[^.]*?(\d+\s*(?:days?|hours?))",
            "category": "defect_reporting_window",
            "check": lambda m: _check_defect_window(m),
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
        """Detect the document type from text content using regex patterns."""
        text_lower = text.lower()
        scores: dict[DocumentType, int] = {dt: 0 for dt in DocumentType}

        for doc_type, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
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

        # Extract amounts via regex (Indian currency patterns)
        inr_pattern = r"(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d{1,2})?"
        for match in re.finditer(inr_pattern, text):
            amount_text = match.group().strip()
            if amount_text not in seen_amounts:
                result.amounts.append(amount_text)
                seen_amounts.add(amount_text)

        # Extract clauses based on document type
        clause_patterns = self._get_clause_patterns(document_type)
        for pattern_def in clause_patterns:
            for match in re.finditer(pattern_def["pattern"], text, re.IGNORECASE | re.DOTALL):
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
        text.lower()

        if document_type == DocumentType.RENTAL:
            # Monthly rent amount
            rent_match = re.search(
                r"(?:monthly\s*rent|rent\s*(?:of|amount))[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+)",
                text, re.IGNORECASE,
            )
            if rent_match:
                terms["monthly_rent"] = rent_match.group(1).strip()

            # Security deposit
            deposit_match = re.search(
                r"security\s*deposit[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+|\d+\s*months?)",
                text, re.IGNORECASE,
            )
            if deposit_match:
                terms["security_deposit"] = deposit_match.group(1).strip()

            # Lock-in period
            lockin_match = re.search(
                r"lock[\s-]*in\s*period[^.]*?(\d+\s*(?:months?|years?))",
                text, re.IGNORECASE,
            )
            if lockin_match:
                terms["lock_in_period"] = lockin_match.group(1).strip()

        elif document_type == DocumentType.EMPLOYMENT:
            # CTC/Salary
            ctc_match = re.search(
                r"(?:CTC|salary|compensation|package)[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+(?:\s*(?:per\s*(?:annum|month)|p\.?a\.?|p\.?m\.?))?)",
                text, re.IGNORECASE,
            )
            if ctc_match:
                terms["compensation"] = ctc_match.group(1).strip()

            # Probation
            prob_match = re.search(
                r"probation[^.]*?(\d+\s*(?:months?|days?))",
                text, re.IGNORECASE,
            )
            if prob_match:
                terms["probation_period"] = prob_match.group(1).strip()

        elif document_type == DocumentType.CONSUMER:
            # Product/Service name
            product_match = re.search(
                r"(?:product|item|service|goods)[^.]*?[\"']([^\"']+)[\"']",
                text, re.IGNORECASE,
            )
            if product_match:
                terms["product_service"] = product_match.group(1).strip()

            # Amount claimed
            claim_match = re.search(
                r"(?:claim|compensation|refund)[^.]*?((?:Rs\.?|INR|₹)\s*[\d,]+)",
                text, re.IGNORECASE,
            )
            if claim_match:
                terms["claim_amount"] = claim_match.group(1).strip()

        return terms


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
        elif months > 2:
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
    elif total_months > 6:
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
