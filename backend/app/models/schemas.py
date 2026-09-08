"""
Pydantic data schemas for Phase 1 Gatekeeper.
Strictly maps to Phase1-Algorithms.md §0 and Phase1-Rules.md §7.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .enums import (
    AuditOpinion,
    CheckStatus,
    CompanyType,
    Confidence,
    ExtractionMethod,
    RegulatoryNature,
    ReportingBasis,
    UserRole,
    Verdict,
)


class FieldProvenance(BaseModel):
    field_name: str
    source: str
    period: str
    basis: ReportingBasis = ReportingBasis.NOT_APPLICABLE
    page: Optional[int] = None
    url: Optional[str] = None
    confidence: Confidence = Confidence.HIGH
    extraction_method: Optional[ExtractionMethod] = None
    raw_snippet: Optional[str] = None
    extracted_at: Optional[str] = None
    document_id: Optional[str] = None


class RegulatoryActionInput(BaseModel):
    active_or_past_5y: Optional[bool] = None
    nature: Optional[RegulatoryNature] = None


class CompanyInput(BaseModel):
    ticker: str
    as_of_date: str
    company_type: Optional[CompanyType] = None
    data_basis: Optional[ReportingBasis] = None

    # Check 1 — Auditor & Regulator
    auditor_resigned_mid_tenure_last_3y: Optional[bool] = None
    audit_opinion: Optional[AuditOpinion] = None
    regulatory_action: RegulatoryActionInput = Field(default_factory=RegulatoryActionInput)
    legal_fees: Optional[float] = None
    audit_fees: Optional[float] = None
    legal_fees_prior_year: Optional[float] = None

    # Check 2 — Promoter Pledge
    govt_shareholding_pct: Optional[float] = None
    promoter_holding_pct_of_company: Optional[float] = None
    pledged_pct_of_promoter_holding: Optional[float] = None
    pledged_pct_history_last_4q: Optional[List[float]] = None
    pledged_pct_of_total_shares: Optional[float] = None

    # Check 3 — Related Party Transactions
    rpt_sales_plus_purchases: Optional[float] = None
    revenue: Optional[float] = None
    unusual_affiliate_dealings: Optional[bool] = None

    # Check 4 — Contingent Liabilities
    contingent_liabilities: Optional[float] = None
    net_worth: Optional[float] = None

    # Check 5 — Cash Conversion (5 fiscal years, oldest -> newest)
    cfo_last_5y: Optional[List[float]] = None
    pat_last_5y: Optional[List[float]] = None

    # Check 6 — Executive Stability
    cfo_changes_last_3y: Optional[int] = None
    restatement_of_past_accounts: Optional[bool] = None

    # Track record length
    years_of_track_record_available: Optional[int] = None

    # Field-level provenance map
    provenance: Dict[str, FieldProvenance] = Field(default_factory=dict)


class CheckResult(BaseModel):
    check_id: int
    status: CheckStatus
    finding: str
    reason_code: str
    missing_data: Optional[str] = None
    fields_used: List[str] = Field(default_factory=list)
    citation: Optional[str] = None
    basis: ReportingBasis = ReportingBasis.NOT_APPLICABLE


class Phase1Result(BaseModel):
    result_id: str
    ticker: str
    as_of_date: str
    company_type: CompanyType
    data_basis: Optional[ReportingBasis] = None
    checks: List[CheckResult]
    verdict: Verdict
    failing_checks: List[int] = Field(default_factory=list)
    inconclusive_checks: List[int] = Field(default_factory=list)
    revision: int = 1
    supersedes: Optional[str] = None
    input_digest: str
    generated_at: str
    citation_gaps: List[str] = Field(default_factory=list)


# User and review queue schemas (Phase 0 / DB models)
class UserSchema(BaseModel):
    id: str
    email: str
    display_name: str
    role: UserRole
    created_at: str
    disabled_at: Optional[str] = None


class ReviewQueueItem(BaseModel):
    id: str
    company_id: str
    ticker: str
    check_id: int
    field_name: str
    best_guess_value: Optional[Any] = None
    period: Optional[str] = None
    basis: Optional[ReportingBasis] = None
    raw_snippet: Optional[str] = None
    source_page: Optional[int] = None
    source_url: Optional[str] = None
    reason: str
    status: str = "PENDING"  # PENDING, RESOLVED, DISMISSED
    resolved_value: Optional[Any] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
