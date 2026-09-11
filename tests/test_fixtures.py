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
    IndustrySector,
    RegulatoryNature,
    ReportingBasis,
    RetrievalTier,
    Verdict,
    WorkingCapitalCycleTier,
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
# Fixture 8 (Rev 5/6): SHORT_CYCLE_ASSET_LIGHT, CFO/PAT ratio 0.79 (< 0.85
# tier floor), 2 negative-CFO years (< 3 trigger), no use-of-funds fields
# populated -> REJECT, verification could not be attempted.
# ---------------------------------------------------------------------------
def test_fixture_8_cfo_pat_ratio_under_tier_floor():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.SHORT_CYCLE_ASSET_LIGHT
    inp.cfo_last_5y = [-10.0, -20.0, 100.0, 100.0, 100.0]  # sum = 270
    inp.pat_last_5y = [50.0, 50.0, 80.0, 80.0, 81.77]  # sum = 341.77 -> ratio = 0.79
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 5 in res.failing_checks
    assert res.checks[4].reason_code == "CASH_CONVERSION_TRIGGER_UNVERIFIED"
    assert "could not be attempted" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 32 (Rev 5): MODERATE_CYCLE, same 0.79 ratio that fails fixture 8
# correctly PASSES here — proves the tiering, not just a global loosening.
# ---------------------------------------------------------------------------
def test_fixture_32_moderate_cycle_same_ratio_passes():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.MODERATE_CYCLE
    inp.cfo_last_5y = [-10.0, -20.0, 100.0, 100.0, 100.0]
    inp.pat_last_5y = [50.0, 50.0, 80.0, 80.0, 81.77]
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[4].status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Fixture 33 (Rev 5): LONG_CYCLE (EPC), ratio 0.68 (>= 0.65 tier floor),
# 3 negative-CFO years (< 4 trigger) -> PASS.
# ---------------------------------------------------------------------------
def test_fixture_33_long_cycle_epc_tolerance():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING
    inp.cfo_last_5y = [-10.0, -10.0, -10.0, 200.0, 200.0]
    inp.pat_last_5y = [100.0, 100.0, 100.0, 100.0, 100.0]  # ratio = 370/500 = 0.74
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[4].status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Fixture 34 (Rev 5): ratio 0.45 -> global 0.50 hard floor message fires
# ahead of the tier-specific message even though both would fail.
# ---------------------------------------------------------------------------
def test_fixture_34_hard_floor_message_routing():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.MODERATE_CYCLE
    inp.cfo_last_5y = [22.5, 22.5, 22.5, 22.5, 22.5]
    inp.pat_last_5y = [50.0, 50.0, 50.0, 50.0, 50.0]  # ratio = 0.45
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert "0.50 global hard floor" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 35 (Rev 5): lending institution -> INCONCLUSIVE regardless of data.
# ---------------------------------------------------------------------------
def test_fixture_35_lending_institution_not_applicable():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LENDING_INSTITUTION_NA
    res = run_phase1(inp)
    assert 5 in res.inconclusive_checks
    assert "lending institutions" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 36 (Rev 5): missing working_capital_cycle_tier -> INCONCLUSIVE,
# never silently treated as any specific tier.
# ---------------------------------------------------------------------------
def test_fixture_36_missing_wc_tier_guard():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = None
    res = run_phase1(inp)
    assert 5 in res.inconclusive_checks


# ---------------------------------------------------------------------------
# Fixture 37 (Rev 6, canonical GRSE case): LONG_CYCLE, ratio 0.055 (breaches
# both 0.50 hard floor and 0.65 tier floor), 3 of 5 years negative (below the
# tier's own 4yr trigger), revenue grows 4x, WC change covers 85% of the
# PAT-CFO gap, liquid cushion flat/declining -> PASS with mandatory warning.
# ---------------------------------------------------------------------------
def test_fixture_37_use_of_funds_verified_warning():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING
    inp.cfo_last_5y = [-5.0, -5.0, -5.0, 10.0, 10.55]  # sum = 5.55
    inp.pat_last_5y = [20.0, 20.0, 20.0, 20.0, 20.0]  # sum = 100 -> ratio = 0.0555
    inp.revenue_last_5y = [100.0, 150.0, 250.0, 350.0, 400.0]  # 4x growth
    inp.cumulative_working_capital_change_5y = -80.325  # 85% of (100-5.55)=94.45
    inp.liquid_cushion_first_year = 22.0  # 22% of 100
    inp.liquid_cushion_last_year = 76.0  # 19% of 400
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[4].has_mandatory_warning is True
    assert 5 in res.warning_checks
    assert "WARNING" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 38 (Rev 6): same as 37 but liquid cushion rises well past the 10%
# tolerance -> condition (c) fails, override blocked, REJECT.
# ---------------------------------------------------------------------------
def test_fixture_38_use_of_funds_hoarding_blocks_override():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING
    inp.cfo_last_5y = [-5.0, -5.0, -5.0, 10.0, 10.55]
    inp.pat_last_5y = [20.0, 20.0, 20.0, 20.0, 20.0]
    inp.revenue_last_5y = [100.0, 150.0, 250.0, 350.0, 400.0]
    inp.cumulative_working_capital_change_5y = -80.325
    inp.liquid_cushion_first_year = 18.0  # 18% of 100
    inp.liquid_cushion_last_year = 124.0  # 31% of 400
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert "in the first year (must not exceed a 10% rise): NOT met" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 39 (Rev 6): same as 37 but revenue is flat (1.05x < 1.5x) ->
# condition (a) fails.
# ---------------------------------------------------------------------------
def test_fixture_39_use_of_funds_no_real_growth():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING
    inp.cfo_last_5y = [-5.0, -5.0, -5.0, 10.0, 10.55]
    inp.pat_last_5y = [20.0, 20.0, 20.0, 20.0, 20.0]
    inp.revenue_last_5y = [100.0, 100.0, 102.0, 104.0, 105.0]  # 1.05x
    inp.cumulative_working_capital_change_5y = -80.325
    inp.liquid_cushion_first_year = 22.0
    inp.liquid_cushion_last_year = 19.95
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert ">= 1.5x required): NOT met" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 40 (Rev 6): same as 37 but WC change covers only 25% of the gap ->
# condition (b) fails.
# ---------------------------------------------------------------------------
def test_fixture_40_use_of_funds_not_a_working_capital_story():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING
    inp.cfo_last_5y = [-5.0, -5.0, -5.0, 10.0, 10.55]
    inp.pat_last_5y = [20.0, 20.0, 20.0, 20.0, 20.0]
    inp.revenue_last_5y = [100.0, 150.0, 250.0, 350.0, 400.0]
    inp.cumulative_working_capital_change_5y = -23.6125  # 25% of 94.45
    inp.liquid_cushion_first_year = 22.0
    inp.liquid_cushion_last_year = 76.0
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert ">= 60% required): NOT met" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 41 (Rev 6): same as 37 but only 4 of 5 required years available ->
# a verified-benign shortfall is "not disqualifying", so a short window falls
# through to INCONCLUSIVE, not FAIL or a premature PASS-with-warning.
# ---------------------------------------------------------------------------
def test_fixture_41_use_of_funds_short_window_holds():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING
    inp.cfo_last_5y = [-5.0, -5.0, 10.0, 10.55]
    inp.pat_last_5y = [20.0, 20.0, 20.0, 20.0]
    inp.revenue_last_5y = [150.0, 250.0, 350.0, 400.0]
    inp.cumulative_working_capital_change_5y = -80.325
    inp.liquid_cushion_first_year = 33.0  # 22% of 150 (this window's first year)
    inp.liquid_cushion_last_year = 76.0  # 19% of 400
    res = run_phase1(inp)
    assert 5 in res.inconclusive_checks
    assert "based on 4 of the required 5 years" in res.checks[4].finding


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
# Fixture 11 (Rev 4): Tier1 (Financial Services), legal fees 1.6% of revenue
# (> 1.35% flag threshold), opinion clean, no other issues -> REJECT.
# ---------------------------------------------------------------------------
def test_fixture_11_legal_fee_exceeds_sector_band():
    inp = make_clean_company_input()
    inp.industry_sector = IndustrySector.TIER1_FINANCIAL_SERVICES
    inp.legal_fees = 16.0  # 1.6% of revenue=1000
    inp.legal_fees_prior_year = 15.0
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert 1 in res.failing_checks
    assert "LEGAL_PCT_REVENUE_EXCEEDS_SECTOR_BAND" in res.checks[0].reason_code


# ---------------------------------------------------------------------------
# Fixture 24 (Rev 4): Tier4 (Manufacturing), legal fees 0.35% of revenue
# (within sourced band, below the 0.45% flag threshold), legal/audit ratio 7x
# -> CLEARED, finding carries the secondary-ratio pass_note.
# ---------------------------------------------------------------------------
def test_fixture_24_legal_audit_ratio_high_but_within_sector_band():
    inp = make_clean_company_input()
    inp.industry_sector = IndustrySector.TIER4_MANUFACTURING_INDUSTRIALS
    inp.legal_fees = 3.5  # 0.35% of revenue
    inp.legal_fees_prior_year = 3.4
    inp.audit_fees = 0.5  # ratio = 7x
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert "not treated as a fail trigger" in res.checks[0].finding


# ---------------------------------------------------------------------------
# Fixture 25 (Rev 4): legal fees jump 2.4x YoY, disclosed litigation
# settlement found -> surge gate does not fire, PASS.
# ---------------------------------------------------------------------------
def test_fixture_25_explained_surge_passes():
    inp = make_clean_company_input()
    inp.industry_sector = IndustrySector.TIER4_MANUFACTURING_INDUSTRIALS
    inp.legal_fees = 3.0  # 0.3% of revenue, within band
    inp.legal_fees_prior_year = 1.25  # 2.4x jump
    inp.legal_fee_surge_explained = True
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[0].status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Fixture 26 (Rev 4): same 2.4x jump, no disclosed cause found -> REJECT.
# ---------------------------------------------------------------------------
def test_fixture_26_unexplained_surge_fails():
    inp = make_clean_company_input()
    inp.industry_sector = IndustrySector.TIER4_MANUFACTURING_INDUSTRIALS
    inp.legal_fees = 3.0
    inp.legal_fees_prior_year = 1.25
    inp.legal_fee_surge_explained = False
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert "LEGAL_FEES_UNEXPLAINED_SURGE_OVER_2X_YOY" in res.checks[0].reason_code


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
# Fixture 13 (Rev 4): audit_fees = 0, revenue/industry_sector/legal_fees
# populated and within sector band, opinion clean -> CLEARED. audit_fees is
# no longer a required field, so its absence/zero must not block a PASS
# reached on the primary revenue-normalized test.
# ---------------------------------------------------------------------------
def test_fixture_13_audit_fees_zero_no_longer_blocks_pass():
    inp = make_clean_company_input()
    inp.audit_fees = 0.0
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert 1 not in res.failing_checks
    assert 1 not in res.inconclusive_checks


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


# ---------------------------------------------------------------------------
# Fixture 19 (Rev 3): Check 5 with only 4 years of CFO/PAT, ratio -0.12 ->
# REJECT, finding names the years-available shortfall.
# ---------------------------------------------------------------------------
def test_fixture_19_check5_short_window_suffix():
    inp = make_clean_company_input()
    inp.cfo_last_5y = [-10.0, -10.0, -10.0, -12.0]
    inp.pat_last_5y = [50.0, 50.0, 50.0, 185.0]  # cumulative_pat = 335, ratio = -0.12
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert "(based on 4 of the required 5 years)" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 20 (Rev 3): Check 2 pledge 0%, FALLBACK-tier trend -> PASS,
# confidence MEDIUM, finding contains the trend-inferred note.
# ---------------------------------------------------------------------------
def test_fixture_20_pledge_fallback_confidence():
    inp = make_clean_company_input()
    inp.pledged_pct_of_promoter_holding = 0.0
    inp.pledged_pct_history_last_4q = [0.0]
    inp.pledged_pct_history_retrieval_tier = RetrievalTier.FALLBACK
    res = run_phase1(inp)
    assert res.checks[1].status == CheckStatus.PASS
    assert res.checks[1].confidence == Confidence.MEDIUM
    assert "not a confirmed quarterly series" in res.checks[1].finding
    assert 2 in res.low_confidence_checks


# ---------------------------------------------------------------------------
# Fixture 21 (Rev 3): Check 1 regulatory_action.nature = NONE, FALLBACK tier
# (SEBI portal unreachable) -> PASS, confidence MEDIUM.
# ---------------------------------------------------------------------------
def test_fixture_21_regulatory_action_fallback_confidence():
    inp = make_clean_company_input()
    inp.regulatory_action.nature = RegulatoryNature.NONE
    inp.regulatory_action.retrieval_tier = RetrievalTier.FALLBACK
    res = run_phase1(inp)
    assert res.checks[0].status == CheckStatus.PASS
    assert res.checks[0].confidence == Confidence.MEDIUM
    assert 1 in res.low_confidence_checks


# ---------------------------------------------------------------------------
# Fixture 22 (Rev 3): Check 6 restatement search finds an ESG/BRSR-only
# restatement -> PASS, finding contains the ESG-exclusion note.
# ---------------------------------------------------------------------------
def test_fixture_22_esg_restatement_excluded():
    inp = make_clean_company_input()
    inp.restatement_of_past_accounts = False
    inp.restatement_esg_only_excluded = True
    res = run_phase1(inp)
    assert res.checks[5].status == CheckStatus.PASS
    assert "ESG/BRSR data restatement" in res.checks[5].finding


# ---------------------------------------------------------------------------
# Fixture 23 (Rev 3): Check 5 with only 3 years, no disqualifying event,
# years_5y_series_gap_checked = false -> HOLD_INCONCLUSIVE, finding notes the
# §8.4-C completeness sub-step was not recorded as attempted.
# ---------------------------------------------------------------------------
def test_fixture_23_short_window_gap_not_checked():
    inp = make_clean_company_input()
    inp.cfo_last_5y = [100.0, 110.0, 120.0]
    inp.pat_last_5y = [90.0, 100.0, 110.0]
    inp.years_5y_series_gap_checked = False
    res = run_phase1(inp)
    assert 5 in res.inconclusive_checks
    assert "not recorded as attempted" in res.checks[4].finding


# ---------------------------------------------------------------------------
# Fixture 27 (Rev 5): Bank, litigation exposure 2% of net worth, routine
# guarantee/LC/forex exposure 850% of net worth (ordinary business) ->
# CLEARED — the primary motivating case for the litigation/routine split.
# ---------------------------------------------------------------------------
def test_fixture_27_bank_routine_guarantees_excluded():
    inp = make_clean_company_input()
    inp.litigation_claims_exposure = 20.0  # 2% of net worth = 1000
    inp.routine_guarantee_exposure = 8500.0  # 850%, ordinary LC/guarantee/forex
    inp.contingent_liabilities_breakdown_available = True
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[3].status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Fixture 28 (Rev 5): EPC contractor, litigation exposure 25% of net worth
# (disputed tax demand + contested claim) -> REJECT even with high routine
# guarantee volume — the split doesn't make Check 4 toothless.
# ---------------------------------------------------------------------------
def test_fixture_28_genuine_litigation_still_fails():
    inp = make_clean_company_input()
    inp.litigation_claims_exposure = 250.0  # 25% of net worth
    inp.routine_guarantee_exposure = 3000.0  # 300%, performance/bid bonds
    inp.contingent_liabilities_breakdown_available = True
    res = run_phase1(inp)
    assert res.verdict == Verdict.REJECT
    assert "litigation & claims exposure 25.0% of net worth vs 20% limit" in res.checks[3].finding


# ---------------------------------------------------------------------------
# Fixture 29 (Rev 5): lump total = 3% of net worth, no breakdown available ->
# CLEARED via the §8.4-F immateriality fast-path.
# ---------------------------------------------------------------------------
def test_fixture_29_lump_total_immateriality_fastpath():
    inp = make_clean_company_input()
    inp.contingent_liabilities = 30.0  # 3% of net worth
    inp.contingent_liabilities_breakdown_available = False
    inp.litigation_claims_exposure = None
    inp.routine_guarantee_exposure = None
    res = run_phase1(inp)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res.checks[3].confidence == Confidence.MEDIUM


# ---------------------------------------------------------------------------
# Fixture 30 (Rev 5): lump total = 40% of net worth, no breakdown available
# -> HOLD_INCONCLUSIVE — a large undisclosed-breakdown total is genuinely
# unresolved, not assumed either way.
# ---------------------------------------------------------------------------
def test_fixture_30_lump_total_large_inconclusive():
    inp = make_clean_company_input()
    inp.contingent_liabilities = 400.0  # 40% of net worth
    inp.contingent_liabilities_breakdown_available = False
    inp.litigation_claims_exposure = None
    inp.routine_guarantee_exposure = None
    res = run_phase1(inp)
    assert 4 in res.inconclusive_checks
