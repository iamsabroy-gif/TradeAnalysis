"""
Automated test suite for Phase 2 Gatekeeper Engine (The Business Quality Check).
Validates the 5 canonical test cases, decision rule hierarchy, trend modifiers,
renderers, and API endpoints.
"""

import pytest
from starlette.testclient import TestClient

from backend.app.api.main import app
from backend.app.engine.phase2 import (
    Phase2GatekeeperError,
    make_cash_hoarder_company_input,
    make_deteriorating_company_input,
    make_red_flag_company_input,
    make_saas_company_input,
    make_utility_company_input,
    run_phase2,
)
from backend.app.models.enums import (
    CheckStatus as Phase1CheckStatus,
    CompanyType,
    Confidence,
    Phase2CheckStatus,
    Phase2Sector,
    Phase2Verdict,
    ReportingBasis,
    Verdict as Phase1Verdict,
)
from backend.app.models.phase2_schemas import (
    CompanyPhase2Input,
    CompetitivePositionInput,
    DebtRefinancingInput,
    GuaranteesOffBalanceSheetInput,
    LoansGivenInput,
    MoatInput,
    SegmentItem,
)
from backend.app.models.schemas import Phase1Result
from backend.app.rendering.phase2 import (
    render_phase2_analyst_table,
    render_phase2_investor_report,
)


def _make_dummy_phase1_result(verdict: Phase1Verdict) -> Phase1Result:
    return Phase1Result(
        result_id="dummy-p1-id",
        ticker="TEST",
        company_type=CompanyType.PRIVATE_PROMOTER,
        as_of_date="2024-03-31",
        data_basis=ReportingBasis.CONSOLIDATED,
        checks=[],
        verdict=verdict,
        failing_checks=[] if verdict != Phase1Verdict.REJECT else [1],
        inconclusive_checks=[] if verdict != Phase1Verdict.HOLD_INCONCLUSIVE else [2],
        revision=1,
        input_digest="abc",
        generated_at="2024-03-31T00:00:00Z",
    )


def test_case_1_saas_company_cleared():
    """Case 1: The SaaS Case clears all Asset-Light thresholds -> CLEARED TO PHASE 3."""
    inp = make_saas_company_input()
    res = run_phase2(inp)

    assert len(res.checks) == 12
    assert res.fails_count == 0
    assert res.concerns_count == 0
    assert res.inconclusive_count == 0
    assert res.verdict == Phase2Verdict.CLEARED_TO_PHASE_3
    assert "CLEARED TO PHASE 3" in res.verdict_summary


def test_case_2_utility_company_regulated_clears():
    """Case 2: The Utility Case passes Regulated/Infra thresholds when >=70% regulated."""
    inp = make_utility_company_input()
    res = run_phase2(inp)

    assert res.sector == Phase2Sector.REGULATED_INFRA
    assert res.fails_count == 0
    assert res.verdict == Phase2Verdict.CLEARED_TO_PHASE_3


def test_case_2_utility_company_unregulated_falls_back_and_fails():
    """Utility case with <70% regulated contracts falls back to Standard and fails leverage."""
    inp = make_utility_company_input()
    inp.regulated_contract_revenue_pct = 40.0  # Fails 70% proof
    res = run_phase2(inp)

    assert res.sector == Phase2Sector.STANDARD
    # Under standard, 3.3x Net debt/EBITDA > 3.0x fail ceiling -> Check 10 FAILS
    c10 = next(c for c in res.checks if c.check_id == "check10_leverage_quantum")
    assert c10.status == Phase2CheckStatus.FAIL
    assert res.verdict == Phase2Verdict.REJECT_AT_PHASE_2


def test_case_3_red_flag_covenant_breach_fails():
    """Case 3: Red flag covenant breach triggers immediate FAIL on Check 13 -> REJECT."""
    inp = make_red_flag_company_input()
    res = run_phase2(inp)

    c13 = next(c for c in res.checks if c.check_id == "check13_cost_rating_covenants")
    assert c13.status == Phase2CheckStatus.FAIL
    assert res.fails_count >= 1
    assert res.verdict == Phase2Verdict.REJECT_AT_PHASE_2


def test_case_4_cash_hoarder_tightened_limit_fails():
    """Case 4: Net-cash company with loans = 18.2% of net worth breaches tightened 15% limit."""
    inp = make_cash_hoarder_company_input()
    res = run_phase2(inp)

    c14 = next(c for c in res.checks if c.check_id == "check14_loans_given")
    assert c14.status == Phase2CheckStatus.FAIL
    assert "tightened to 15% for net-cash" in c14.finding
    assert res.verdict == Phase2Verdict.REJECT_AT_PHASE_2


def test_case_5_deterioration_trend_modifier_downgrades():
    """Case 5: Leverage in pass zone but rising 3 consecutive years downgrades to CONCERN."""
    inp = make_deteriorating_company_input()
    res = run_phase2(inp)

    c10 = next(c for c in res.checks if c.check_id == "check10_leverage_quantum")
    assert c10.trend_modifier_applied is True
    assert c10.status == Phase2CheckStatus.CONCERN
    assert res.concerns_count == 1
    assert res.verdict == Phase2Verdict.HOLD_WATCH_LIST


def test_decision_rule_three_concerns_rejects():
    """Decision Rule: >= 3 Concerns triggers REJECT AT PHASE 2."""
    inp = make_saas_company_input()
    # Trigger 3 concerns:
    # 1. Short-term debt % > 15% on Check 12
    inp.financials[-1].gross_debt = 50.0
    inp.debt_refinancing.short_term_borrowings = 15.0 # 30% ST debt
    # 2. Guarantees 30% of net worth on Check 15
    inp.guarantees.total_guarantees = 66.0 # 30% of net worth 220
    # 3. Market share flat/down while industry expanding on Check 18
    inp.competition.market_share_history = {"FY22": 20.0, "FY23": 19.5, "FY24": 19.0}

    res = run_phase2(inp)
    assert res.fails_count == 0
    assert res.concerns_count >= 3
    assert res.verdict == Phase2Verdict.REJECT_AT_PHASE_2


def test_decision_rule_inconclusive_holds():
    """Decision Rule: < 3 Concerns but >= 1 Inconclusive triggers HOLD — INCONCLUSIVE."""
    inp = make_saas_company_input()
    # Check 18 inconclusive if market share data missing
    inp.competition.market_share_data_available = False

    res = run_phase2(inp)
    assert res.fails_count == 0
    assert res.inconclusive_count >= 1
    assert res.verdict == Phase2Verdict.HOLD_INCONCLUSIVE


def test_phase1_gatekeeper_entry_enforcement():
    """Stock with Phase 1 REJECT is blocked from Phase 2 evaluation."""
    inp = make_saas_company_input()
    p1_reject = _make_dummy_phase1_result(Phase1Verdict.REJECT)

    with pytest.raises(Phase2GatekeeperError) as exc:
        run_phase2(inp, phase1_result=p1_reject)
    assert "Entry condition failed" in str(exc.value)

    p1_cleared = _make_dummy_phase1_result(Phase1Verdict.CLEARED_TO_PHASE_2)
    res = run_phase2(inp, phase1_result=p1_cleared)
    assert res.phase1_cleared is True
    assert res.phase1_result_id == "dummy-p1-id"


def test_renderers_output():
    """Verifies analyst table and investor report formatting."""
    inp = make_saas_company_input()
    res = run_phase2(inp)

    # Analyst table
    analyst_table = render_phase2_analyst_table(res)
    assert "# Phase 2 — CloudScale Software Ltd (SAASTECH)" in analyst_table
    assert "## VERDICT: CLEARED_TO_PHASE_3" in analyst_table
    assert "### Group A — What it earns" in analyst_table
    assert "### Group B — What it owes" in analyst_table
    assert "### Group C — How it collects" in analyst_table
    assert "### Group D — Why it lasts" in analyst_table
    assert "## PESTLE context" in analyst_table

    # Investor report
    investor_report = render_phase2_investor_report(res)
    assert "Good business — now check if the price is fair" in investor_report
    assert "₹100" in investor_report
    assert "SEBI-registered" in investor_report
    assert "Important Regulatory Disclaimer" in investor_report


def test_api_phase2_endpoints():
    """Tests the Phase 2 API endpoints using TestClient."""
    client = TestClient(app)

    # 1. Fetch fixture
    r_fix = client.get("/api/phase2/fixtures/saas")
    assert r_fix.status_code == 200
    data = r_fix.json()
    assert data["ticker"] == "SAASTECH"

    # 2. Evaluate
    payload = {"company_input": data}
    r_eval = client.post("/api/phase2/evaluate", json=payload)
    assert r_eval.status_code == 200
    body = r_eval.json()
    result_id = body["result"]["result_id"]
    assert body["result"]["verdict"] == "CLEARED_TO_PHASE_3"
    assert "analyst_table" in body
    assert "investor_report" in body

    # 3. Retrieve stored result
    r_res = client.get(f"/api/phase2/results/{result_id}")
    assert r_res.status_code == 200
    assert r_res.json()["result"]["ticker"] == "SAASTECH"

    # 4. Retrieve formatted report
    r_rep = client.get(f"/api/phase2/results/{result_id}/report?format=investor")
    assert r_rep.status_code == 200
    assert "Important Regulatory Disclaimer" in r_rep.text
