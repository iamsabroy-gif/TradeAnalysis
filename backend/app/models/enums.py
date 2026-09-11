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


class PdfClass(str, Enum):
    NATIVE_TEXT = "NATIVE_TEXT"
    HYBRID = "HYBRID"
    SCANNED_IMAGE_ONLY = "SCANNED_IMAGE_ONLY"


class RetrievalTier(str, Enum):
    """
    Rev 3 — Phase1-Algorithms-v3.md §0. Distinguishes "this field is populated"
    from "this field came from the primary source §8.4 requires".
    """

    PRIMARY = "PRIMARY"
    FALLBACK = "FALLBACK"
    UNAVAILABLE = "UNAVAILABLE"


class IndustrySector(str, Enum):
    """
    Rev 4 — Phase1-Algorithms-v3.md §0 / Phase1-Rules-v2.md §8.4-E.
    Sector tiers feeding Check 1's revenue-normalized legal-fee-anomaly test.
    """

    TIER1_FINANCIAL_SERVICES = "TIER1_FINANCIAL_SERVICES"
    TIER2_PHARMA_HEALTHCARE_IT = "TIER2_PHARMA_HEALTHCARE_IT"
    TIER3_REGULATED_GOVT_TELECOM_ENERGY = "TIER3_REGULATED_GOVT_TELECOM_ENERGY"
    TIER4_MANUFACTURING_INDUSTRIALS = "TIER4_MANUFACTURING_INDUSTRIALS"
    TIER5_RETAIL_FMCG_CONSUMER = "TIER5_RETAIL_FMCG_CONSUMER"
    TIER_OTHER_UNCLASSIFIED = "TIER_OTHER_UNCLASSIFIED"


class WorkingCapitalCycleTier(str, Enum):
    """
    Rev 5 — Phase1-Algorithms-v3.md §0 / Phase1-Rules-v2.md §8.4-G.
    A separate classification axis from IndustrySector: legal-spend intensity
    (Check 1) and working-capital-cycle length (Check 5) classify the same
    company differently — never conflate the two enums.
    """

    LONG_CYCLE_PROJECT_ACCOUNTING = "LONG_CYCLE_PROJECT_ACCOUNTING"
    MODERATE_CYCLE = "MODERATE_CYCLE"
    SHORT_CYCLE_ASSET_LIGHT = "SHORT_CYCLE_ASSET_LIGHT"
    LENDING_INSTITUTION_NA = "LENDING_INSTITUTION_NA"
    TIER_OTHER_UNCLASSIFIED = "TIER_OTHER_UNCLASSIFIED"
