"""
Phase A — Test Suite for all 18 Fixtures in Phase1-Algorithms.md §11.
Strictly validates Decision Engine against all prescribed scenarios and edge cases.
"""

from datetime import date
import pytest

from backend.app.engine.orchestrator import run_phase1
from backend.app.fixtures import make_clean_company_input
from backend.app.models.enums import (
    AuditOpinion,
    CheckStatus,
    Confidence,
    RegulatoryNature,
    ReportingBasis,
    Verdict,
)
from backend.app.models.schemas import (
    CompanyInput,
    FieldProvenance,
    RegulatoryActionInput,
)


# ---------------------------------------------------------------------------
# Fixture 1: Happy path
# ---------------------------------------------------------------------------
def test_fixture_1_happy_path():
    inp = make_clean_company_input()
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert len(res.failing_checks) == 0
    assert len(res.inconclusive_checks) == 0
    for c in res.checks:
        assert c.status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Fixture 2: Audit opinion = QUALIFIED, everything else clean
# ---------------------------------------------------------------------------
def test_fixture_2_audit_opinion_qualified():
    inp = make_clean_company_input()
    inp.audit_opinion = AuditOpinion.QUALIFIED
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 1 in res.failing_checks
    assert res.checks[0].status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Fixture 3: Pledge 34%, rising trend
# ---------------------------------------------------------------------------
def test_fixture_3_pledge_34_rising():
    inp = make_clean_company_input()
    inp.pledged_pct_of_promoter_holding = 34.0
    inp.pledged_pct_history_last_4q = [25.0, 28.0, 30.0, 34.0]
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 2 in res.failing_checks
    assert res.checks[1].status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Fixture 4: Govt shareholding 55%, promoter pledge fields all null
# ---------------------------------------------------------------------------
def test_fixture_4_govt_psu_auto_pass():
    inp = make_clean_company_input()
    inp.govt_shareholding_pct = 55.0
    inp.promoter_holding_pct_of_company = None
    inp.pledged_pct_of_promoter_holding = None
    inp.pledged_pct_history_last_4q = None
    inp.pledged_pct_of_total_shares = None
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[1].status == CheckStatus.PASS
    assert res.checks[1].reason_code == "GOVT_PSU_EXEMPT"


# ---------------------------------------------------------------------------
# Fixture 5: Promoter holding 1% of company, pledge 30% of promoter holding,
# 0.3% of total shares (corrected in Algo rev 2)
# ---------------------------------------------------------------------------
def test_fixture_5_low_base_pass():
    inp = make_clean_company_input()
    inp.promoter_holding_pct_of_company = 1.0
    inp.pledged_pct_of_promoter_holding = 30.0
    inp.pledged_pct_of_total_shares = 0.3
    inp.pledged_pct_history_last_4q = [30.0, 30.0, 30.0, 30.0]
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[1].status == CheckStatus.PASS
    assert res.checks[1].reason_code == "LOW_BASE_PLEDGE_SAFE"


# ---------------------------------------------------------------------------
# Fixture 6: Company listed 2 years, no disqualifying events, Check 1/6
# ---------------------------------------------------------------------------
def test_fixture_6_short_track_record():
    inp = make_clean_company_input()
    inp.years_of_track_record_available = 2
    res = run_phase1(inp)
    assert res.verdict == Verdict.HOLD_INCONCLUSIVE
    assert 1 in res.inconclusive_checks
    assert 6 in res.inconclusive_checks


# ---------------------------------------------------------------------------
# Fixture 7: Company listed 1 year but had a qualified audit opinion that year
# ---------------------------------------------------------------------------
def test_fixture_7_short_history_with_disqualifying_event():
    inp = make_clean_company_input()
    inp.years_of_track_record_available = 1
    inp.audit_opinion = AuditOpinion.QUALIFIED
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 1 in res.failing_checks


# ---------------------------------------------------------------------------
# Fixture 8: CFO/PAT ratio 0.79 cumulative, 2 negative-CFO years
# ---------------------------------------------------------------------------
def test_fixture_8_cfo_pat_ratio_under_80pct():
    inp = make_clean_company_input()
    inp.cfo_last_5y = [-10.0, -20.0, 100.0, 100.0, 100.0]  # sum = 270
    inp.pat_last_5y = [50.0, 50.0, 80.0, 80.0, 81.77]  # sum = 341.77 -> ratio = 0.79
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 5 in res.failing_checks


# ---------------------------------------------------------------------------
# Fixture 9: Missing net_worth entirely
# ---------------------------------------------------------------------------
def test_fixture_9_missing_net_worth():
    inp = make_clean_company_input()
    inp.net_worth = None
    res = run_phase1(inp)
    assert res.verdict == Verdict.HOLD_INCONCLUSIVE
    assert 4 in res.inconclusive_checks


# ---------------------------------------------------------------------------
# Fixture 10: Net worth = -500 (negative)
# ---------------------------------------------------------------------------
def test_fixture_10_negative_net_worth():
    inp = make_clean_company_input()
    inp.net_worth = -500.0
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 4 in res.failing_checks


# ---------------------------------------------------------------------------
# Fixture 11: Legal fees 6x audit fees, opinion clean, no other issues
# ---------------------------------------------------------------------------
def test_fixture_11_legal_fees_exceed_5x():
    inp = make_clean_company_input()
    inp.legal_fees = 60.0
    inp.audit_fees = 10.0
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 1 in res.failing_checks


# ---------------------------------------------------------------------------
# Fixture 12: years_of_track_record_available = null, everything else clean
# ---------------------------------------------------------------------------
def test_fixture_12_track_record_null():
    inp = make_clean_company_input()
    inp.years_of_track_record_available = None
    res = run_phase1(inp)
    assert res.verdict == Verdict.HOLD_INCONCLUSIVE
    assert 1 in res.inconclusive_checks
    assert 6 in res.inconclusive_checks


# ---------------------------------------------------------------------------
# Fixture 13: audit_fees = 0, opinion clean (regression guard)
# ---------------------------------------------------------------------------
def test_fixture_13_audit_fees_zero_regression():
    inp = make_clean_company_input()
    inp.audit_fees = 0.0
    res = run_phase1(inp)
    # Zero audit fees is missing data / uncomputable, MUST NOT produce a FAIL
    assert res.verdict == Verdict.HOLD_INCONCLUSIVE
    assert 1 in res.inconclusive_checks
    assert 1 not in res.failing_checks


# ---------------------------------------------------------------------------
# Fixture 14: RPT note CONSOLIDATED, revenue STANDALONE
# ---------------------------------------------------------------------------
def test_fixture_14_basis_mismatch():
    inp = make_clean_company_input()
    inp.provenance["revenue"] = FieldProvenance(
        field_name="revenue",
        source="Standalone Financials",
        period="FY24",
        basis=ReportingBasis.STANDALONE,
        confidence=Confidence.HIGH,
    )
    res = run_phase1(inp)
    assert res.verdict == Verdict.HOLD_INCONCLUSIVE
    assert 3 in res.inconclusive_checks
    assert "mixed reporting basis" in res.checks[2].missing_data


# ---------------------------------------------------------------------------
# Fixture 15: contingent_liabilities period FY24, net_worth period FY23
# ---------------------------------------------------------------------------
def test_fixture_15_period_mismatch():
    inp = make_clean_company_input()
    inp.provenance["net_worth"] = FieldProvenance(
        field_name="net_worth",
        source="AR FY23 Balance Sheet",
        period="FY23",
        basis=ReportingBasis.CONSOLIDATED,
        confidence=Confidence.HIGH,
    )
    res = run_phase1(inp)
    assert res.verdict == Verdict.HOLD_INCONCLUSIVE
    assert 4 in res.inconclusive_checks
    assert "span different periods" in res.checks[3].missing_data


# ---------------------------------------------------------------------------
# Fixture 16: Promoter holding 3%, pledge 40%, pledged_pct_of_total_shares not reported
# Derived 1.2% > 0.5% -> REJECT
# ---------------------------------------------------------------------------
def test_fixture_16_derived_pledge_total_shares_fail():
    inp = make_clean_company_input()
    inp.promoter_holding_pct_of_company = 3.0
    inp.pledged_pct_of_promoter_holding = 40.0
    inp.pledged_pct_of_total_shares = None
    inp.pledged_pct_history_last_4q = [40.0, 40.0, 40.0, 40.0]
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 2 in res.failing_checks


# ---------------------------------------------------------------------------
# Fixture 17: Pledge 34% with no provenance entry for pledged_pct_of_promoter_holding
# ---------------------------------------------------------------------------
def test_fixture_17_citation_gaps_visible():
    inp = make_clean_company_input()
    inp.pledged_pct_of_promoter_holding = 34.0
    inp.pledged_pct_history_last_4q = [30.0, 31.0, 32.0, 34.0]
    del inp.provenance["pledged_pct_of_promoter_holding"]
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 2 in res.failing_checks
    # Sourcing gap is captured in citation_gaps
    assert "pledged_pct_of_promoter_holding" in res.citation_gaps


# ---------------------------------------------------------------------------
# Fixture 18: Fixture 9 re-run after net_worth is supplied by manual review
# ---------------------------------------------------------------------------
def test_fixture_18_result_versioning():
    # Initial run with missing net worth (Fixture 9)
    inp9 = make_clean_company_input()
    inp9.net_worth = None
    res1 = run_phase1(inp9)
    assert res1.verdict == Verdict.HOLD_INCONCLUSIVE
    assert res1.revision == 1
    assert res1.supersedes is None

    # Manual review supplies net worth
    inp18 = inp9.model_copy(deep=True)
    inp18.net_worth = 1000.0
    inp18.provenance["net_worth"] = FieldProvenance(
        field_name="net_worth",
        source="Manual Review Resolution p. 112",
        period="FY24",
        basis=ReportingBasis.CONSOLIDATED,
        confidence=Confidence.MANUAL,
    )

    res2 = run_phase1(inp18, prior=res1)
    assert res2.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res2.revision == 2
    assert res2.supersedes == res1.result_id
    assert res2.result_id != res1.result_id
