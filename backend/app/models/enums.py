"""
Domain enums for Phase 1 Gatekeeper.
Strictly maps to Phase1-Algorithms.md §0 and Phase1-Rules.md §2-§3.
"""

from enum import Enum


class CompanyType(str, Enum):
    PRIVATE_PROMOTER = "PRIVATE_PROMOTER"
    GOVT_PSU = "GOVT_PSU"
    PROFESSIONALLY_MANAGED = "PROFESSIONALLY_MANAGED"


class ReportingBasis(str, Enum):
    CONSOLIDATED = "CONSOLIDATED"
    STANDALONE = "STANDALONE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MANUAL = "MANUAL"
    DERIVED = "DERIVED"


class ExtractionMethod(str, Enum):
    NATIVE_TEXT = "NATIVE_TEXT"
    TABLE_PARSE = "TABLE_PARSE"
    OCR = "OCR"
    MANUAL = "MANUAL"
    DERIVED = "DERIVED"
    HTML_SCRAPE = "HTML_SCRAPE"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class Verdict(str, Enum):
    REJECT = "REJECT"
    CLEARED_TO_PHASE_2 = "CLEARED_TO_PHASE_2"
    HOLD_INCONCLUSIVE = "HOLD_INCONCLUSIVE"


class UserRole(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class AuditOpinion(str, Enum):
    CLEAN = "CLEAN"
    QUALIFIED = "QUALIFIED"
    ADVERSE = "ADVERSE"
    DISCLAIMER = "DISCLAIMER"


class RegulatoryNature(str, Enum):
    FRAUD = "FRAUD"
    SIPHONING = "SIPHONING"
    MANIPULATION = "MANIPULATION"
    ACCOUNTING_IRREGULARITY = "ACCOUNTING_IRREGULARITY"
    ROUTINE_PROCEDURAL = "ROUTINE_PROCEDURAL"
    NONE = "NONE"
