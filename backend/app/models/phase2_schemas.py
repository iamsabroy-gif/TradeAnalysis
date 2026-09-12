"""
Data contracts and schemas for Phase 2 Gatekeeper (Business Quality Check).
Strictly maps to Phase2-Rules.md §1-§4 and phase2implementation.md.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.models.enums import (
    Confidence,
    MoatType,
    Phase2CheckGroup,
    Phase2CheckStatus,
    Phase2Sector,
    Phase2Verdict,
    ReportingBasis,
)
from backend.app.models.schemas import FieldProvenance


class AnnualFinancials(BaseModel):
    """Annual financial statement line items for a single fiscal year."""
    period: str                         # e.g. "FY24"
    revenue: float
    ebitda: float
    ebit: float
    pat: float
    total_equity: float                 # Net worth
    gross_debt: float
    cash_and_equivalents: float
    gross_margin_pct: Optional[float] = None
    ebitda_margin_pct: Optional[float] = None
    net_margin_pct: Optional[float] = None
    roce_pct: Optional[float] = None
    roe_pct: Optional[float] = None
    finance_cost: Optional[float] = None
    cfo: Optional[float] = None         # Operating cash flow


class SegmentYearData(BaseModel):
    """Segment results for a single fiscal year."""
    period: str
    revenue: float
    segment_result: Optional[float] = None
    margin_pct: Optional[float] = None
    volume: Optional[float] = None
    realisation: Optional[float] = None


class SegmentItem(BaseModel):
    """Segment information across reporting years."""
    name: str
    history: List[SegmentYearData] = Field(default_factory=list)


class DebtRefinancingInput(BaseModel):
    """Maturity, short-term debt and liquidity data for Check 12."""
    short_term_borrowings: float = 0.0
    long_term_borrowings: float = 0.0
    principal_due_next_12m: float = 0.0
    undrawn_committed_lines: float = 0.0
    quarterly_operating_expenses: Optional[float] = None


class CreditAndCovenantInput(BaseModel):
    """Credit ratings, borrowing costs, and debt covenant data for Check 13."""
    credit_rating: Optional[str] = None         # e.g. "AAA", "AA", "BBB-", "D"
    rating_outlook: Optional[str] = "STABLE"    # "POSITIVE", "STABLE", "NEGATIVE"
    downgrades_last_3y_notches: int = 0
    covenant_breach_disclosed: bool = False
    covenant_waiver_obtained: bool = False
    average_borrowing_cost_pct: Optional[float] = None
    borrowing_cost_yoy_increase_bps: Optional[float] = None
    unrated_with_material_debt: bool = False
    substantially_all_assets_pledged: bool = False


class LoansGivenInput(BaseModel):
    """Inter-corporate loans/advances extended for Check 14."""
    total_loans_advances_to_entities: float = 0.0
    pct_of_net_worth: Optional[float] = None
    is_non_interest_bearing_material: bool = False
    has_provisions_or_writeoffs: bool = False
    growing_faster_than_revenue: bool = False


class GuaranteesOffBalanceSheetInput(BaseModel):
    """Corporate guarantees and off-balance-sheet commitments for Check 15."""
    total_guarantees: float = 0.0
    pct_of_net_worth: Optional[float] = None
    guarantees_for_non_subs_material: bool = False
    guarantee_invoked_or_paid: bool = False
    borrowed_from_group_undisclosed_terms: bool = False


class WorkingCapitalYearData(BaseModel):
    """Receivable, inventory, and payable days for Check 16."""
    period: str
    receivable_days: float
    inventory_days: float
    payable_days: float
    advances_to_vendors: Optional[float] = None


class MoatInput(BaseModel):
    """Stated moat details and pricing power for Check 17."""
    claimed_moat_type: MoatType = MoatType.NONE
    moat_description: Optional[str] = None
    realisation_rising_vs_inflation: Optional[bool] = None
    licence_subsidy_expiring_within_3y: bool = False


class CompetitivePositionInput(BaseModel):
    """Market share and peer comparisons for Check 18."""
    market_share_history: Dict[str, float] = Field(default_factory=dict)
    revenue_trailed_industry_3y: bool = False
    largest_competitor_growing_materially_faster: bool = False
    disruptive_entrant_or_substitute: bool = False
    market_share_data_available: bool = True


class PestleContext(BaseModel):
    """Macro and qualitative context per Section G (Q30) / §4."""
    political: Optional[str] = None
    economic: Optional[str] = None
    social: Optional[str] = None
    technological: Optional[str] = None
    legal: Optional[str] = None
    environmental: Optional[str] = None


class CompanyPhase2Input(BaseModel):
    """
    Standard input container for evaluating a company through Phase 2 Gatekeeper.
    """
    ticker: str
    company_name: Optional[str] = None
    as_of_date: str = "2024-03-31"
    data_basis: ReportingBasis = ReportingBasis.CONSOLIDATED
    sector: Phase2Sector = Phase2Sector.STANDARD
    regulated_contract_revenue_pct: Optional[float] = None
    is_cyclical: bool = False
    order_book_driven: bool = False

    # Financial and operational data
    financials: List[AnnualFinancials] = Field(default_factory=list) # Chronological (e.g. FY20 -> FY24)
    working_capital: List[WorkingCapitalYearData] = Field(default_factory=list)
    segments: List[SegmentItem] = Field(default_factory=list)
    debt_refinancing: DebtRefinancingInput = Field(default_factory=DebtRefinancingInput)
    credit_covenants: CreditAndCovenantInput = Field(default_factory=CreditAndCovenantInput)
    loans_given: LoansGivenInput = Field(default_factory=LoansGivenInput)
    guarantees: GuaranteesOffBalanceSheetInput = Field(default_factory=GuaranteesOffBalanceSheetInput)
    moat: MoatInput = Field(default_factory=MoatInput)
    competition: CompetitivePositionInput = Field(default_factory=CompetitivePositionInput)
    pestle: PestleContext = Field(default_factory=PestleContext)

    # Narrative explanation flags
    margin_driver_disclosed: bool = True
    margin_driver_explanation: Optional[str] = None

    # Traceability
    provenance: Dict[str, FieldProvenance] = Field(default_factory=dict)


class Phase2CheckResult(BaseModel):
    """Outcome of an individual Phase 2 quality check."""
    check_id: str
    q_number: str
    title: str
    group: Phase2CheckGroup
    status: Phase2CheckStatus
    raw_metric_value: Optional[float] = None
    threshold_applied: Optional[str] = None
    trend_modifier_applied: bool = False
    original_status: Optional[Phase2CheckStatus] = None
    finding: str
    source: str
    confidence: Confidence = Confidence.HIGH
    inconclusive_reason: Optional[str] = None
    what_would_clear: Optional[str] = None
    fields_used: List[str] = Field(default_factory=list)


class Phase2Result(BaseModel):
    """
    Master result object produced by the Phase 2 Decision Engine.
    """
    result_id: str
    ticker: str
    company_name: Optional[str] = None
    as_of_date: str
    data_basis: ReportingBasis
    sector: Phase2Sector
    phase1_result_id: Optional[str] = None
    phase1_cleared: bool = True
    checks: List[Phase2CheckResult]
    verdict: Phase2Verdict
    verdict_summary: str
    concerns_count: int
    inconclusive_count: int
    fails_count: int
    passes_count: int
    why_the_verdict: List[str]
    what_data_does_not_conclude: List[str]
    what_would_change_verdict: List[str]
    pestle_summary: Dict[str, str] = Field(default_factory=dict)
    generated_at: str
