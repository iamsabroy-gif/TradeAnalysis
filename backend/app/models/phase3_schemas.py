"""
Data contracts and schemas for Phase 3 Gatekeeper (Valuation & Story Confirmation).
Strictly maps to Docs/Rules/Phase3-Rules.md and Docs/Rules/Phase3-Algorithms.md.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.models.enums import (
    Phase3Verdict,
    ReturnProbability,
    StoryContradictionType,
    ValuationStatus,
)


class ValuationMetricItem(BaseModel):
    """Comparison item for a single valuation metric (P/E, EV/EBITDA)."""
    metric_name: str
    current: float
    peer_avg: float
    hist_5y_avg: float
    status: ValuationStatus
    notes: Optional[str] = None


class ValuationAnalysis(BaseModel):
    """Aggregate valuation gap analysis (Phase3-Algorithms.md §2 Step 2)."""
    pe_comparison: ValuationMetricItem
    ev_ebitda_comparison: Optional[ValuationMetricItem] = None
    overall_status: ValuationStatus
    explanation: str


class ReturnPathAnalysis(BaseModel):
    """Calculation of required earnings growth to achieve 20% CAGR (Phase3-Algorithms.md §2 Step 3)."""
    target_cagr_pct: float = 20.0
    horizon_years: int = 3
    dividend_yield_pct: float = 0.0
    annualized_pe_rerating_pct: float = 0.0
    required_eps_growth_pct: float
    historical_eps_growth_pct: float
    probability: ReturnProbability
    formula_used: str
    verdict_statement: str


class StoryContradictionItem(BaseModel):
    """Evaluation result for one of the Four Great Contradictions (Phase3-Algorithms.md §2 Step 4)."""
    contradiction_type: StoryContradictionType
    title: str
    section_source: str
    triggered: bool
    detail: str


class StoryScanAnalysis(BaseModel):
    """Aggregate scan result of management story and narrative confirmation."""
    contradictions: List[StoryContradictionItem]
    has_fatal_contradiction: bool
    summary: str


class CompanyPhase3Input(BaseModel):
    """
    Inputs required for Phase 3 valuation and narrative confirmation screen.
    Operationalises Section E, Section I, and narrative sections B, C, D, H, J.
    """
    ticker: str
    company_name: Optional[str] = None
    current_price: float
    market_cap_cr: Optional[float] = None

    # Section E: Valuation Inputs
    current_pe: float
    peer_avg_pe: float
    hist_5y_avg_pe: float
    current_ev_ebitda: Optional[float] = None
    peer_avg_ev_ebitda: Optional[float] = None
    hist_5y_avg_ev_ebitda: Optional[float] = None

    # Section I: Return Path Inputs
    hist_eps_growth_5y_pct: float
    dividend_yield_pct: float = 0.0
    target_cagr_pct: float = 20.0
    horizon_years: int = 3
    expected_pe_change_annualized_pct: float = 0.0

    # Section B & C: Expansion vs Capex (Contradiction 1)
    section_c_high_growth_guidance: bool = False
    section_c_guidance_detail: Optional[str] = None
    section_b_capex_spent_cr: Optional[float] = None
    section_b_maintenance_capex_cr: Optional[float] = None

    # Section G & H: Moat vs Vendor Risk (Contradiction 2)
    section_g_claimed_high_moat: bool = False
    section_h_single_source_dependency_pct: Optional[float] = None
    section_h_outsourcing_pct: Optional[float] = None

    # Section J: Guidance Track Record (Contradiction 3)
    section_j_guidance_missed_consecutive_years: int = 0

    # Section D & C: Tone Shift vs Guidance (Contradiction 4)
    section_d_management_tone_defensive: bool = False
    section_d_margin_falling: bool = False


class Phase3Result(BaseModel):
    """Full execution output of Phase 3 Gatekeeper."""
    result_id: str
    ticker: str
    company_name: Optional[str] = None
    phase2_result_id: Optional[str] = None
    verdict: Phase3Verdict
    valuation: ValuationAnalysis
    return_path: ReturnPathAnalysis
    story_scan: StoryScanAnalysis
    why_verdict: str
    layman_explanation: str
    created_at: str
