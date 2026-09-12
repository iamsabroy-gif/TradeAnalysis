"""
Canonical Test Fixtures for Phase 3 Gatekeeper Engine.
Provides ready-to-test inputs representing all five decision matrix verdict branches.
"""

from backend.app.models.phase3_schemas import CompanyPhase3Input


def make_high_conviction_buy_input(ticker: str = "TCS") -> CompanyPhase3Input:
    """
    Case 1: BUY - HIGH CONVICTION
    Fair Valuation (P/E 18x <= Hist 22x & Peer 24x) +
    Probable Return Path (Req Growth 18.5% <= Hist 18.0% + 2%) +
    No Story Contradictions.
    """
    return CompanyPhase3Input(
        ticker=ticker,
        company_name="Tata Consultancy Services Ltd",
        current_price=3850.0,
        market_cap_cr=1400000.0,
        current_pe=18.0,
        peer_avg_pe=24.0,
        hist_5y_avg_pe=22.0,
        current_ev_ebitda=13.0,
        peer_avg_ev_ebitda=17.0,
        hist_5y_avg_ev_ebitda=15.5,
        hist_eps_growth_5y_pct=18.0,
        dividend_yield_pct=1.5,
        target_cagr_pct=20.0,
        horizon_years=3,
        expected_pe_change_annualized_pct=0.0,
        section_c_high_growth_guidance=True,
        section_b_capex_spent_cr=5000.0,
        section_b_maintenance_capex_cr=1800.0,
        section_g_claimed_high_moat=True,
        section_h_single_source_dependency_pct=15.0,
        section_h_outsourcing_pct=20.0,
        section_j_guidance_missed_consecutive_years=0,
        section_d_management_tone_defensive=False,
        section_d_margin_falling=False,
    )


def make_speculative_buy_input(ticker: str = "TITAN") -> CompanyPhase3Input:
    """
    Case 2: BUY - SPECULATIVE
    Expensive Valuation (P/E 55x > Hist 45x & Peer 42x) +
    Aggressive / Probable Return Path (High historic compounder at 22% CAGR) +
    No Story Contradictions.
    """
    return CompanyPhase3Input(
        ticker=ticker,
        company_name="Titan Company Ltd",
        current_price=3200.0,
        market_cap_cr=284000.0,
        current_pe=55.0,
        peer_avg_pe=42.0,
        hist_5y_avg_pe=45.0,
        current_ev_ebitda=35.0,
        peer_avg_ev_ebitda=28.0,
        hist_5y_avg_ev_ebitda=30.0,
        hist_eps_growth_5y_pct=22.0,
        dividend_yield_pct=0.8,
        target_cagr_pct=20.0,
        horizon_years=3,
        expected_pe_change_annualized_pct=0.0,
        section_c_high_growth_guidance=True,
        section_b_capex_spent_cr=800.0,
        section_b_maintenance_capex_cr=300.0,
        section_g_claimed_high_moat=True,
        section_h_single_source_dependency_pct=25.0,
        section_h_outsourcing_pct=30.0,
        section_j_guidance_missed_consecutive_years=1,
        section_d_management_tone_defensive=False,
        section_d_margin_falling=False,
    )


def make_fair_value_hold_input(ticker: str = "HINDUNILVR") -> CompanyPhase3Input:
    """
    Case 3: HOLD - FAIR VALUE
    Fair Valuation (P/E 48x <= Hist 52x & Peer 50x) +
    Aggressive Return Path (Req Growth 18.5% is > Hist 14% + 2% but <= 1.5x) +
    No Story Contradictions.
    """
    return CompanyPhase3Input(
        ticker=ticker,
        company_name="Hindustan Unilever Ltd",
        current_price=2450.0,
        market_cap_cr=575000.0,
        current_pe=48.0,
        peer_avg_pe=50.0,
        hist_5y_avg_pe=52.0,
        current_ev_ebitda=32.0,
        peer_avg_ev_ebitda=34.0,
        hist_5y_avg_ev_ebitda=35.0,
        hist_eps_growth_5y_pct=14.0,
        dividend_yield_pct=1.5,
        target_cagr_pct=20.0,
        horizon_years=3,
        expected_pe_change_annualized_pct=0.0,
        section_c_high_growth_guidance=False,
        section_b_capex_spent_cr=1200.0,
        section_b_maintenance_capex_cr=800.0,
        section_g_claimed_high_moat=True,
        section_h_single_source_dependency_pct=10.0,
        section_h_outsourcing_pct=25.0,
        section_j_guidance_missed_consecutive_years=0,
        section_d_management_tone_defensive=False,
        section_d_margin_falling=False,
    )


def make_overvalued_avoid_input(ticker: str = "DMART") -> CompanyPhase3Input:
    """
    Case 4: AVOID - OVERVALUED (The Quality Trap)
    Extreme Premium Valuation +
    Miraculous Return Path (Hist 10.0%, Req 19.5% > 1.5x Hist).
    """
    return CompanyPhase3Input(
        ticker=ticker,
        company_name="Avenue Supermarts Ltd",
        current_price=4100.0,
        market_cap_cr=266000.0,
        current_pe=85.0,
        peer_avg_pe=45.0,
        hist_5y_avg_pe=70.0,
        current_ev_ebitda=52.0,
        peer_avg_ev_ebitda=28.0,
        hist_5y_avg_ev_ebitda=42.0,
        hist_eps_growth_5y_pct=10.0,
        dividend_yield_pct=0.1,
        target_cagr_pct=20.0,
        horizon_years=3,
        expected_pe_change_annualized_pct=0.0,
        section_c_high_growth_guidance=True,
        section_b_capex_spent_cr=2500.0,
        section_b_maintenance_capex_cr=600.0,
        section_g_claimed_high_moat=True,
        section_h_single_source_dependency_pct=12.0,
        section_h_outsourcing_pct=10.0,
        section_j_guidance_missed_consecutive_years=0,
        section_d_management_tone_defensive=False,
        section_d_margin_falling=False,
    )


def make_story_contradiction_avoid_input(ticker: str = "PROMISES_CORP") -> CompanyPhase3Input:
    """
    Case 5: AVOID - STORY CONTRADICTION (The Story Trap)
    Cheap/Fair valuation on paper, BUT
    Management has missed guidance for 3 straight years and capex is stalled.
    """
    return CompanyPhase3Input(
        ticker=ticker,
        company_name="Promises & Excuses Corporation",
        current_price=120.0,
        market_cap_cr=1500.0,
        current_pe=12.0,
        peer_avg_pe=18.0,
        hist_5y_avg_pe=16.0,
        current_ev_ebitda=7.0,
        peer_avg_ev_ebitda=11.0,
        hist_5y_avg_ev_ebitda=10.0,
        hist_eps_growth_5y_pct=16.0,
        dividend_yield_pct=2.0,
        target_cagr_pct=20.0,
        horizon_years=3,
        expected_pe_change_annualized_pct=0.0,
        section_c_high_growth_guidance=True,
        section_b_capex_spent_cr=20.0,
        section_b_maintenance_capex_cr=25.0,  # Contradiction 1: Capex <= Maint
        section_g_claimed_high_moat=True,
        section_h_single_source_dependency_pct=65.0,  # Contradiction 2: > 50%
        section_h_outsourcing_pct=30.0,
        section_j_guidance_missed_consecutive_years=3,  # Contradiction 3: >= 3
        section_d_management_tone_defensive=True,  # Contradiction 4: Defensive tone while guiding high
        section_d_margin_falling=True,
    )
