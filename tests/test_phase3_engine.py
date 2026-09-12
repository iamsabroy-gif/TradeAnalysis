"""
Automated test suite for Phase 3 Gatekeeper Engine (Valuation & Story Confirmation).
Strictly maps to Docs/Rules/Phase3-Rules.md and Docs/Rules/Phase3-Algorithms.md.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.api.main import app
from backend.app.engine.phase3 import (
    Phase3GatekeeperError,
    calc_return_path,
    calc_valuation,
    make_fair_value_hold_input,
    make_high_conviction_buy_input,
    make_overvalued_avoid_input,
    make_speculative_buy_input,
    make_story_contradiction_avoid_input,
    run_phase3,
    scan_contradictions,
)
from backend.app.models.enums import (
    Phase2Sector,
    Phase2Verdict,
    Phase3Verdict,
    ReportingBasis,
    ReturnProbability,
    StoryContradictionType,
    ValuationStatus,
)
from backend.app.models.phase2_schemas import (
    CompanyPhase2Input,
    Phase2Result,
)
from backend.app.rendering.phase3 import (
    render_phase3_analyst_table,
    render_phase3_investor_report,
)


def _make_dummy_phase2_result(verdict: Phase2Verdict) -> Phase2Result:
    return Phase2Result(
        result_id="dummy-p2-id",
        ticker="TEST",
        company_name="Test Co",
        as_of_date="2024-03-31",
        data_basis=ReportingBasis.CONSOLIDATED,
        sector=Phase2Sector.STANDARD,
        verdict=verdict,
        verdict_summary=f"Verdict is {verdict.value}",
        checks=[],
        concerns_count=0,
        inconclusive_count=0,
        fails_count=0,
        passes_count=12,
        why_the_verdict=["Passed all required tests"],
        what_data_does_not_conclude=[],
        what_would_change_verdict=[],
        generated_at="2024-03-31T00:00:00Z",
    )


# ------------------------------------------------------------------------------
# 1. Valuation Gap Tests (Check A)
# ------------------------------------------------------------------------------

def test_calc_valuation_fair():
    inp = make_high_conviction_buy_input()
    inp.current_pe = 20.0
    inp.hist_5y_avg_pe = 22.0
    inp.peer_avg_pe = 25.0
    val = calc_valuation(inp)
    assert val.overall_status == ValuationStatus.FAIR
    assert val.pe_comparison.status == ValuationStatus.FAIR


def test_calc_valuation_expensive():
    inp = make_high_conviction_buy_input()
    inp.current_pe = 35.0
    inp.hist_5y_avg_pe = 22.0
    inp.peer_avg_pe = 25.0
    val = calc_valuation(inp)
    assert val.overall_status == ValuationStatus.EXPENSIVE
    assert val.pe_comparison.status == ValuationStatus.EXPENSIVE


def test_calc_valuation_concern_divergence():
    inp = make_high_conviction_buy_input()
    # Cheap vs peers (30.0), but expensive vs own history (18.0)
    inp.current_pe = 22.0
    inp.hist_5y_avg_pe = 18.0
    inp.peer_avg_pe = 30.0
    val = calc_valuation(inp)
    assert val.overall_status == ValuationStatus.CONCERN


# ------------------------------------------------------------------------------
# 2. Return Path Calculation Tests (Check B)
# ------------------------------------------------------------------------------

def test_calc_return_path_probable():
    inp = make_high_conviction_buy_input()
    # Target 20, Div Yield 1.5, PE Rerate 0.0 -> Req Growth = 18.5
    # Hist EPS Growth = 18.0 -> Probable ceiling = 18.0 + 2.0 = 20.0 >= 18.5
    ret = calc_return_path(inp)
    assert ret.probability == ReturnProbability.PROBABLE
    assert ret.required_eps_growth_pct == 18.5
    assert "reasonable" in ret.verdict_statement


def test_calc_return_path_aggressive():
    inp = make_fair_value_hold_input()
    # Target 20, Div Yield 1.5 -> Req Growth = 18.5
    # Hist EPS Growth = 14.0 -> Probable ceiling = 16.0 < 18.5 <= 1.5*14 (21.0)
    ret = calc_return_path(inp)
    assert ret.probability == ReturnProbability.AGGRESSIVE
    assert "stretched" in ret.verdict_statement


def test_calc_return_path_miraculous():
    inp = make_overvalued_avoid_input()
    # Target 20, Div Yield 0.1 -> Req Growth = 19.9
    # Hist EPS Growth = 10.0 -> Aggressive ceiling = 15.0 < 19.9
    ret = calc_return_path(inp)
    assert ret.probability == ReturnProbability.MIRACULOUS
    assert "fantasy" in ret.verdict_statement


def test_calc_return_path_extreme_pe_rerating():
    inp = make_high_conviction_buy_input()
    inp.expected_pe_change_annualized_pct = 25.0
    ret = calc_return_path(inp)
    assert ret.probability == ReturnProbability.MIRACULOUS


# ------------------------------------------------------------------------------
# 3. Story Contradiction Scan Tests (Check C)
# ------------------------------------------------------------------------------

def test_story_scan_no_contradictions():
    inp = make_high_conviction_buy_input()
    scan = scan_contradictions(inp)
    assert scan.has_fatal_contradiction is False
    assert len(scan.contradictions) == 4
    assert all(not c.triggered for c in scan.contradictions)


def test_story_scan_expansion_lie():
    inp = make_high_conviction_buy_input()
    inp.section_c_high_growth_guidance = True
    inp.section_b_capex_spent_cr = 100.0
    inp.section_b_maintenance_capex_cr = 120.0  # Capex spent <= Maintenance
    scan = scan_contradictions(inp)
    assert scan.has_fatal_contradiction is True
    c1 = next(c for c in scan.contradictions if c.contradiction_type == StoryContradictionType.EXPANSION_LIE)
    assert c1.triggered is True


def test_story_scan_vendor_risk():
    inp = make_high_conviction_buy_input()
    inp.section_g_claimed_high_moat = True
    inp.section_h_single_source_dependency_pct = 65.0  # > 50%
    scan = scan_contradictions(inp)
    assert scan.has_fatal_contradiction is True
    c2 = next(c for c in scan.contradictions if c.contradiction_type == StoryContradictionType.VENDOR_RISK)
    assert c2.triggered is True


def test_story_scan_guidance_gap():
    inp = make_high_conviction_buy_input()
    inp.section_j_guidance_missed_consecutive_years = 3
    scan = scan_contradictions(inp)
    assert scan.has_fatal_contradiction is True
    c3 = next(c for c in scan.contradictions if c.contradiction_type == StoryContradictionType.GUIDANCE_GAP)
    assert c3.triggered is True


def test_story_scan_tone_shift():
    inp = make_high_conviction_buy_input()
    inp.section_c_high_growth_guidance = True
    inp.section_d_management_tone_defensive = True
    inp.section_d_margin_falling = True
    scan = scan_contradictions(inp)
    assert scan.has_fatal_contradiction is True
    c4 = next(c for c in scan.contradictions if c.contradiction_type == StoryContradictionType.TONE_SHIFT)
    assert c4.triggered is True


# ------------------------------------------------------------------------------
# 4. Canonical Verdict Branches (Decision Matrix)
# ------------------------------------------------------------------------------

def test_verdict_high_conviction_buy():
    inp = make_high_conviction_buy_input()
    res = run_phase3(inp)
    assert res.verdict == Phase3Verdict.BUY_HIGH_CONVICTION
    assert "High Conviction Buy" in res.why_verdict


def test_verdict_speculative_buy():
    inp = make_speculative_buy_input()
    res = run_phase3(inp)
    assert res.verdict == Phase3Verdict.BUY_SPECULATIVE
    assert "Speculative Buy" in res.why_verdict


def test_verdict_fair_value_hold():
    inp = make_fair_value_hold_input()
    res = run_phase3(inp)
    assert res.verdict == Phase3Verdict.HOLD_FAIR_VALUE


def test_verdict_overvalued_avoid():
    inp = make_overvalued_avoid_input()
    res = run_phase3(inp)
    assert res.verdict == Phase3Verdict.AVOID_OVERVALUED


def test_verdict_story_contradiction_avoid():
    inp = make_story_contradiction_avoid_input()
    res = run_phase3(inp)
    assert res.verdict == Phase3Verdict.AVOID_STORY_CONTRADICTION


# ------------------------------------------------------------------------------
# 5. Entry Condition Prerequisite Enforcement
# ------------------------------------------------------------------------------

def test_entry_condition_rejected_phase2():
    p2_failed = _make_dummy_phase2_result(Phase2Verdict.REJECT_AT_PHASE_2)
    inp = make_high_conviction_buy_input()
    with pytest.raises(Phase3GatekeeperError, match="Entry condition failed"):
        run_phase3(inp, phase2_result=p2_failed)


def test_entry_condition_cleared_phase2():
    p2_cleared = _make_dummy_phase2_result(Phase2Verdict.CLEARED_TO_PHASE_3)
    inp = make_high_conviction_buy_input()
    res = run_phase3(inp, phase2_result=p2_cleared)
    assert res.phase2_result_id == "dummy-p2-id"
    assert res.verdict == Phase3Verdict.BUY_HIGH_CONVICTION


# ------------------------------------------------------------------------------
# 6. Presentation & Rendering Tests
# ------------------------------------------------------------------------------

def test_rendering_analyst_table():
    inp = make_high_conviction_buy_input()
    res = run_phase3(inp)
    table_md = render_phase3_analyst_table(res)
    assert "# Phase 3 —" in table_md
    assert "| P/E |" in table_md
    assert "The 20% Return Path:" in table_md
    assert "Why the Verdict" in table_md


def test_rendering_investor_report():
    inp = make_high_conviction_buy_input()
    res = run_phase3(inp)
    report_md = render_phase3_investor_report(res)
    assert "The Decision:" in report_md
    assert "The Price Tag" in report_md
    assert "flat" in report_md or "Apartment" in report_md or "neighborhood" in report_md
    assert "SEBI" in report_md


# ------------------------------------------------------------------------------
# 7. API Endpoints Tests
# ------------------------------------------------------------------------------

def test_api_phase3_evaluate_and_get():
    client = TestClient(app)
    inp = make_high_conviction_buy_input()
    resp = client.post("/api/phase3/evaluate", json={"company_input": inp.model_dump()})
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["verdict"] == Phase3Verdict.BUY_HIGH_CONVICTION.value
    assert "analyst_table" in data
    assert "investor_report" in data

    res_id = data["result"]["result_id"]
    get_resp = client.get(f"/api/phase3/results/{res_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["result"]["result_id"] == res_id

    report_resp = client.get(f"/api/phase3/results/{res_id}/report?format=investor")
    assert report_resp.status_code == 200
    assert "Investment Reality Check" in report_resp.text


def test_api_phase3_fixtures():
    client = TestClient(app)
    resp = client.get("/api/phase3/fixtures/high_conviction")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "TCS"
    assert data["current_pe"] == 18.0


def test_api_phase3_default_input():
    client = TestClient(app)
    resp = client.get("/api/phase3/default-input/INFY")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "INFY"
    assert "current_pe" in data
    assert "target_cagr_pct" in data
