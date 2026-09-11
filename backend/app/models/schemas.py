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
    IndustrySector,
    RegulatoryNature,
    ReportingBasis,
    RetrievalTier,
    UserRole,
    Verdict,
    WorkingCapitalCycleTier,
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
    # Rev 3 — Phase1-Rules-v2.md §8.4-A: was this sourced from the named SEBI
    # registry (PRIMARY) or a generic web fallback (FALLBACK)?
    retrieval_tier: Optional[RetrievalTier] = None


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
    audit_fees: Optional[float] = None  # Rev 4: secondary/corroboration only
    legal_fees_prior_year: Optional[float] = None
    # Rev 4 — Rules §8.4-E: NSE/BSE sector tag feeding the fee-anomaly test.
    industry_sector: Optional[IndustrySector] = None
    # Rev 4 — true only if a disclosed one-off cause for a >2x YoY legal-fee
    # jump was found (Contingent Liabilities note, Board's Report, or news).
    legal_fee_surge_explained: Optional[bool] = None

    # Check 2 — Promoter Pledge
    govt_shareholding_pct: Optional[float] = None
    promoter_holding_pct_of_company: Optional[float] = None
    pledged_pct_of_promoter_holding: Optional[float] = None
    pledged_pct_history_last_4q: Optional[List[float]] = None
    # Rev 3 — Rules §8.4-B: was this an actual quarterly series (PRIMARY) or a
    # single latest-quarter figure + "no new pledge" filing (FALLBACK)?
    pledged_pct_history_retrieval_tier: Optional[RetrievalTier] = None
    pledged_pct_of_total_shares: Optional[float] = None

    # Check 3 — Related Party Transactions
    rpt_sales_plus_purchases: Optional[float] = None
    revenue: Optional[float] = None
    unusual_affiliate_dealings: Optional[bool] = None

    # Check 4 — Contingent Liabilities. Rev 5 — Rules §8.4-F: litigation-vs-
    # routine split replaces the flat total-over-net-worth ratio.
    net_worth: Optional[float] = None
    litigation_claims_exposure: Optional[float] = None
    routine_guarantee_exposure: Optional[float] = None
    # Retained only as the lump-total fallback when no Schedule III
    # sub-category breakdown could be extracted.
    contingent_liabilities: Optional[float] = None
    contingent_liabilities_breakdown_available: Optional[bool] = None

    # Check 5 — Cash Conversion (up to 5 fiscal years, oldest -> newest)
    cfo_last_5y: Optional[List[float]] = None
    pat_last_5y: Optional[List[float]] = None
    # Rev 5 — Rules §8.4-G: working-capital-cycle classification, a separate
    # axis from industry_sector above.
    working_capital_cycle_tier: Optional[WorkingCapitalCycleTier] = None
    # Rev 6 — Rules §8.4-H use-of-funds verification fields. Consumed only
    # when a disqualifying trigger actually fires.
    revenue_last_5y: Optional[List[float]] = None
    cumulative_working_capital_change_5y: Optional[float] = None
    liquid_cushion_first_year: Optional[float] = None
    liquid_cushion_last_year: Optional[float] = None
    # Rev 3 — true only if the §8.4-C completeness sub-step was actually
    # attempted before accepting a short CFO/PAT series.
    years_5y_series_gap_checked: Optional[bool] = None

    # Check 6 — Executive Stability
    cfo_changes_last_3y: Optional[int] = None
    restatement_of_past_accounts: Optional[bool] = None
    # Rev 3 — Rules §8.4-D: PRIMARY if sourced via targeted terms + Emphasis
    # of Matter review, FALLBACK if only a general keyword scan was done.
    restatement_search_retrieval_tier: Optional[RetrievalTier] = None
    # Rev 3 — true if a restatement-shaped mention was found and confirmed to
    # be an ESG/BRSR data restatement rather than a financial one.
    restatement_esg_only_excluded: Optional[bool] = None

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
    # Rev 3 — rolled up from the retrieval tiers of fields_used; HIGH if all
    # PRIMARY, MEDIUM if any FALLBACK.
    confidence: Confidence = Confidence.HIGH
    # Rev 6 — true only for a Check 5 PASS reached via the §8.4-H
    # use-of-funds override. Forces the renderer to produce the dedicated
    # warning paragraph from Rules §5d — never a silent PASS.
    has_mandatory_warning: bool = False


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
    # Rev 3 — check_ids where confidence != HIGH, regardless of PASS/FAIL.
    low_confidence_checks: List[int] = Field(default_factory=list)
    # Rev 6 — check_ids where has_mandatory_warning == true. Never affects
    # verdict; forces the renderer's dedicated warning paragraph.
    warning_checks: List[int] = Field(default_factory=list)
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
