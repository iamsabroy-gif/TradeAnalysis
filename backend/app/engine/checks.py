"""
Check functions 1 to 6 for Phase 1 Gatekeeper.
Strictly maps to Phase1-Algorithms.md §3 to §8.
Pure functions — zero network or disk I/O.
"""

from typing import List

from backend.app.models.enums import (
    AuditOpinion,
    CheckStatus,
    CompanyType,
    RegulatoryNature,
    ReportingBasis,
)
from backend.app.models.schemas import CheckResult, CompanyInput
from .helpers import (
    apply_track_record_guard,
    assert_comparable,
    compose_citation,
    derive_pledged_pct_of_total_shares,
)


def check1_auditor_regulator(input_data: CompanyInput) -> CheckResult:
    """
    Check 1 — Auditor & Regulator Integrity (Section A Q1)
    Phase1-Algorithms.md §3
    """
    fields_used = [
        "audit_opinion",
        "auditor_resigned_mid_tenure_last_3y",
        "regulatory_action",
        "legal_fees",
        "audit_fees",
    ]

    # Required fields null check
    if (
        input_data.auditor_resigned_mid_tenure_last_3y is None
        or input_data.audit_opinion is None
        or input_data.regulatory_action.active_or_past_5y is None
        or input_data.legal_fees is None
        or input_data.audit_fees is None
    ):
        return CheckResult(
            check_id=1,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 1 inconclusive due to missing inputs",
            reason_code="CHECK_1_DATA_MISSING",
            missing_data=(
                "Check 1: missing one or more of [auditor resignation history, "
                "audit opinion, regulatory action status, legal/audit fee figures]"
            ),
            fields_used=fields_used,
        )

    disqualifying_event_found = (
        input_data.auditor_resigned_mid_tenure_last_3y is True
        or input_data.audit_opinion != AuditOpinion.CLEAN
        or input_data.regulatory_action.nature
        in {
            RegulatoryNature.FRAUD,
            RegulatoryNature.SIPHONING,
            RegulatoryNature.MANIPULATION,
            RegulatoryNature.ACCOUNTING_IRREGULARITY,
        }
    )

    guard = apply_track_record_guard(
        years_required=3,
        years_available=input_data.years_of_track_record_available,
        disqualifying_event_found=disqualifying_event_found,
    )
    if guard is not None:
        citation, _ = compose_citation(input_data, fields_used)
        if guard == CheckStatus.FAIL:
            return CheckResult(
                check_id=1,
                status=CheckStatus.FAIL,
                finding="Disqualifying auditor/regulator issue found despite short track record",
                reason_code="AUDITOR_DISQUALIFYING_SHORT_HISTORY",
                fields_used=fields_used,
                citation=citation,
            )
        return CheckResult(
            check_id=1,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 1: insufficient track record (only "
            f"{input_data.years_of_track_record_available if input_data.years_of_track_record_available is not None else 'unknown'} "
            "years available vs 3 required)",
            reason_code="INSUFFICIENT_TRACK_RECORD",
            missing_data="Track record length not established or < 3 years",
            fields_used=fields_used,
            citation=citation,
        )

    fail_reasons: List[str] = []
    inconclusive_notes: List[str] = []

    if input_data.auditor_resigned_mid_tenure_last_3y is True:
        fail_reasons.append("AUDITOR_RESIGNED_MID_TENURE")

    if input_data.audit_opinion != AuditOpinion.CLEAN:
        fail_reasons.append(f"AUDIT_OPINION_NOT_CLEAN:{input_data.audit_opinion.value}")

    if (
        input_data.regulatory_action.active_or_past_5y is True
        and input_data.regulatory_action.nature
        in {
            RegulatoryNature.FRAUD,
            RegulatoryNature.SIPHONING,
            RegulatoryNature.MANIPULATION,
            RegulatoryNature.ACCOUNTING_IRREGULARITY,
        }
    ):
        fail_reasons.append(f"REGULATORY_ACTION:{input_data.regulatory_action.nature.value}")

    # Fee-ratio sub-check comparability guard
    fee_mismatch = assert_comparable(input_data, ["legal_fees", "audit_fees"])
    if fee_mismatch is not None:
        inconclusive_notes.append(f"legal/audit fee ratio not computable: {fee_mismatch}")
    elif input_data.audit_fees > 0:
        ratio = input_data.legal_fees / input_data.audit_fees
        surge = (
            input_data.legal_fees_prior_year is not None
            and input_data.legal_fees_prior_year > 0
            and (input_data.legal_fees / input_data.legal_fees_prior_year) > 2.0
        )
        if ratio > 5.0:
            fail_reasons.append(f"LEGAL_FEES_EXCEED_5X_AUDIT_FEES:{round(ratio, 2)}x")
        elif surge:
            fail_reasons.append("LEGAL_FEES_SURGE_OVER_2X_YOY")
    else:
        # audit_fees is zero — ratio undefined, not a red flag (Algo spec rev 2 fix)
        inconclusive_notes.append("audit_fees is zero; legal/audit ratio undefined")

    citation, _ = compose_citation(input_data, fields_used)
    basis = (
        input_data.provenance["legal_fees"].basis
        if "legal_fees" in input_data.provenance
        else ReportingBasis.NOT_APPLICABLE
    )

    if fail_reasons:
        return CheckResult(
            check_id=1,
            status=CheckStatus.FAIL,
            finding="; ".join(fail_reasons),
            reason_code="; ".join(fail_reasons),
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    if inconclusive_notes:
        return CheckResult(
            check_id=1,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 1 sub-check inconclusive",
            reason_code="CHECK_1_SUBCHECK_INCONCLUSIVE",
            missing_data="; ".join(inconclusive_notes),
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    return CheckResult(
        check_id=1,
        status=CheckStatus.PASS,
        finding="Clean opinion, no mid-tenure resignation, no disqualifying regulatory action, legal/audit fee ratio normal",
        reason_code="AUDITOR_REGULATOR_CLEAN",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
    )


def detect_rising_trend(history: List[float]) -> bool:
    """
    History is oldest -> newest, length up to 4.
    Rising trend = each quarter >= previous (allow ties), overall net increase,
    OR any single-quarter jump > 2 percentage points vs prior quarter.
    """
    if len(history) < 2:
        return False

    is_non_decreasing = all(history[i] >= history[i - 1] for i in range(1, len(history)))
    net_increase = history[-1] - history[0] > 0
    if is_non_decreasing and net_increase:
        return True

    for i in range(1, len(history)):
        if history[i] - history[i - 1] > 2.0:
            return True

    return False


def check2_promoter_pledge(input_data: CompanyInput) -> CheckResult:
    """
    Check 2 — Promoter Pledge & Encumbrance (Section A Q2)
    Phase1-Algorithms.md §4
    """
    # Auto-pass exceptions
    if input_data.company_type == CompanyType.GOVT_PSU:
        return CheckResult(
            check_id=2,
            status=CheckStatus.PASS,
            finding="Government PSU (govt shareholding >= 51%) — pledge check N/A",
            reason_code="GOVT_PSU_EXEMPT",
            fields_used=["govt_shareholding_pct"],
        )

    if input_data.company_type == CompanyType.PROFESSIONALLY_MANAGED:
        return CheckResult(
            check_id=2,
            status=CheckStatus.PASS,
            finding="Zero promoter holding — no promoter shares exist to pledge",
            reason_code="PROFESSIONALLY_MANAGED_EXEMPT",
            fields_used=["promoter_holding_pct_of_company"],
        )

    # Normal path
    fields_used = [
        "promoter_holding_pct_of_company",
        "pledged_pct_of_promoter_holding",
        "pledged_pct_history_last_4q",
    ]

    if (
        input_data.promoter_holding_pct_of_company is None
        or input_data.pledged_pct_of_promoter_holding is None
        or input_data.pledged_pct_history_last_4q is None
    ):
        return CheckResult(
            check_id=2,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 2 inconclusive due to missing pledge inputs",
            reason_code="CHECK_2_DATA_MISSING",
            missing_data="Check 2: missing promoter holding %, latest pledge %, or 4-quarter pledge history",
            fields_used=fields_used,
        )

    trend_rising = detect_rising_trend(input_data.pledged_pct_history_last_4q)
    low_base = input_data.promoter_holding_pct_of_company < 5.0
    citation, _ = compose_citation(input_data, fields_used)

    if low_base:
        pledged_of_total = derive_pledged_pct_of_total_shares(input_data)
        if pledged_of_total is None:
            return CheckResult(
                check_id=2,
                status=CheckStatus.INCONCLUSIVE,
                finding="Check 2: promoter base < 5% of company; pledged % of total shares required but missing",
                reason_code="PLEDGED_OF_TOTAL_MISSING",
                missing_data="Check 2: promoter base < 5% of company; pledged % of total shares outstanding required but missing",
                fields_used=fields_used,
                citation=citation,
            )

        fail_a = (
            input_data.pledged_pct_of_promoter_holding > 10.0
            and pledged_of_total > 0.5
        )
        fail_b = False  # qualitative check, defaults false if unknown/undeterminable

        if fail_a or fail_b:
            return CheckResult(
                check_id=2,
                status=CheckStatus.FAIL,
                finding=(
                    f"pledge material even after low-base adjustment: "
                    f"{input_data.pledged_pct_of_promoter_holding}% of promoter holding, "
                    f"{pledged_of_total}% of total shares"
                ),
                reason_code="LOW_BASE_PLEDGE_MATERIAL",
                fields_used=fields_used + ["pledged_pct_of_total_shares"],
                citation=citation,
            )
        else:
            return CheckResult(
                check_id=2,
                status=CheckStatus.PASS,
                finding=(
                    f"pledge % elevated ({input_data.pledged_pct_of_promoter_holding}%) due to small promoter base, "
                    f"total shares pledged {pledged_of_total}% <= 0.5% — not treated as a red flag"
                ),
                reason_code="LOW_BASE_PLEDGE_SAFE",
                fields_used=fields_used + ["pledged_pct_of_total_shares"],
                citation=citation,
            )

    # Standard thresholds
    if input_data.pledged_pct_of_promoter_holding > 10.0:
        return CheckResult(
            check_id=2,
            status=CheckStatus.FAIL,
            finding=f"pledge {input_data.pledged_pct_of_promoter_holding}% vs 10% limit (absolute threshold)",
            reason_code="PLEDGE_EXCEEDS_10PCT",
            fields_used=fields_used,
            citation=citation,
        )

    if trend_rising:
        return CheckResult(
            check_id=2,
            status=CheckStatus.FAIL,
            finding="pledged % rising over last 2-4 quarters (or unexplained single-quarter spike > 2pp)",
            reason_code="PLEDGE_RISING_TREND",
            fields_used=fields_used,
            citation=citation,
        )

    return CheckResult(
        check_id=2,
        status=CheckStatus.PASS,
        finding=f"pledge {input_data.pledged_pct_of_promoter_holding}% (<= 10%), stable/declining over last 4 quarters",
        reason_code="PLEDGE_SAFE",
        fields_used=fields_used,
        citation=citation,
    )


def check3_related_party(input_data: CompanyInput) -> CheckResult:
    """
    Check 3 — Related-Party 'Leakage' (Section A Q3)
    Phase1-Algorithms.md §5
    """
    fields_used = ["rpt_sales_plus_purchases", "revenue", "unusual_affiliate_dealings"]

    if (
        input_data.rpt_sales_plus_purchases is None
        or input_data.revenue is None
        or input_data.unusual_affiliate_dealings is None
    ):
        return CheckResult(
            check_id=3,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 3 inconclusive due to missing inputs",
            reason_code="CHECK_3_DATA_MISSING",
            missing_data="Check 3: missing RPT sales+purchases, revenue, or affiliate-dealings assessment",
            fields_used=fields_used,
        )

    mismatch = assert_comparable(input_data, ["rpt_sales_plus_purchases", "revenue"])
    if mismatch is not None:
        return CheckResult(
            check_id=3,
            status=CheckStatus.INCONCLUSIVE,
            finding=f"Check 3: {mismatch}",
            reason_code="CHECK_3_COMPARABILITY_MISMATCH",
            missing_data=f"Check 3: {mismatch}",
            fields_used=fields_used,
        )

    if input_data.revenue <= 0:
        return CheckResult(
            check_id=3,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 3: revenue is zero/negative, RPT % undefined",
            reason_code="REVENUE_ZERO_OR_NEGATIVE",
            missing_data="revenue is zero or negative",
            fields_used=fields_used,
        )

    rpt_pct = round((input_data.rpt_sales_plus_purchases / input_data.revenue) * 100.0, 2)
    citation, _ = compose_citation(input_data, fields_used)
    basis = (
        input_data.provenance["revenue"].basis
        if "revenue" in input_data.provenance
        else ReportingBasis.NOT_APPLICABLE
    )

    if rpt_pct > 5.0:
        return CheckResult(
            check_id=3,
            status=CheckStatus.FAIL,
            finding=f"RPT {rpt_pct}% of revenue vs 5% limit",
            reason_code="RPT_EXCEEDS_5PCT",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    if input_data.unusual_affiliate_dealings is True:
        return CheckResult(
            check_id=3,
            status=CheckStatus.FAIL,
            finding="large/unexplained loans or deals with promoter-owned unlisted affiliates",
            reason_code="UNUSUAL_AFFILIATE_DEALINGS",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    return CheckResult(
        check_id=3,
        status=CheckStatus.PASS,
        finding=f"RPT {rpt_pct}% of revenue (<= 5%), no suspicious affiliate transactions",
        reason_code="RPT_NORMAL",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
    )


def check4_contingent_liabilities(input_data: CompanyInput) -> CheckResult:
    """
    Check 4 — Contingent Liabilities (Section A Q4)
    Phase1-Algorithms.md §6
    """
    fields_used = ["contingent_liabilities", "net_worth"]

    if (
        input_data.contingent_liabilities is None
        or input_data.net_worth is None
    ):
        return CheckResult(
            check_id=4,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 4 inconclusive due to missing inputs",
            reason_code="CHECK_4_DATA_MISSING",
            missing_data="Check 4: missing contingent liabilities or net worth figure",
            fields_used=fields_used,
        )

    mismatch = assert_comparable(input_data, ["contingent_liabilities", "net_worth"])
    if mismatch is not None:
        return CheckResult(
            check_id=4,
            status=CheckStatus.INCONCLUSIVE,
            finding=f"Check 4: {mismatch}",
            reason_code="CHECK_4_COMPARABILITY_MISMATCH",
            missing_data=f"Check 4: {mismatch}",
            fields_used=fields_used,
        )

    citation, _ = compose_citation(input_data, fields_used)
    basis = (
        input_data.provenance["net_worth"].basis
        if "net_worth" in input_data.provenance
        else ReportingBasis.NOT_APPLICABLE
    )

    if input_data.net_worth <= 0:
        return CheckResult(
            check_id=4,
            status=CheckStatus.FAIL,
            finding=f"net worth {input_data.net_worth} <= 0 (broken balance sheet)",
            reason_code="NEGATIVE_NET_WORTH",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    ratio_pct = round((input_data.contingent_liabilities / input_data.net_worth) * 100.0, 2)

    if ratio_pct > 15.0:
        return CheckResult(
            check_id=4,
            status=CheckStatus.FAIL,
            finding=f"contingent liabilities {ratio_pct}% of net worth vs 15% limit",
            reason_code="CONTINGENT_LIABILITIES_EXCEED_15PCT",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    return CheckResult(
        check_id=4,
        status=CheckStatus.PASS,
        finding=f"contingent liabilities {ratio_pct}% of net worth (<= 15%)",
        reason_code="CONTINGENT_LIABILITIES_SAFE",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
    )


def check5_cash_conversion(input_data: CompanyInput) -> CheckResult:
    """
    Check 5 — Show Me the Cash (Section A Q5)
    Phase1-Algorithms.md §7
    """
    fields_used = ["cfo_last_5y", "pat_last_5y"]

    if input_data.cfo_last_5y is None or input_data.pat_last_5y is None:
        return CheckResult(
            check_id=5,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 5 inconclusive due to missing CFO or PAT series",
            reason_code="CHECK_5_DATA_MISSING",
            missing_data="Check 5: missing 5-year CFO and/or PAT series",
            fields_used=fields_used,
        )

    n = len(input_data.cfo_last_5y)
    if n != len(input_data.pat_last_5y):
        return CheckResult(
            check_id=5,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 5: CFO and PAT series have mismatched year counts",
            reason_code="SERIES_LENGTH_MISMATCH",
            missing_data="Check 5: CFO and PAT series have mismatched year counts",
            fields_used=fields_used,
        )

    mismatch = assert_comparable(input_data, ["cfo_last_5y", "pat_last_5y"])
    if mismatch is not None:
        return CheckResult(
            check_id=5,
            status=CheckStatus.INCONCLUSIVE,
            finding=f"Check 5: {mismatch}",
            reason_code="CHECK_5_COMPARABILITY_MISMATCH",
            missing_data=f"Check 5: {mismatch}",
            fields_used=fields_used,
        )

    negative_cfo_years = sum(1 for y in input_data.cfo_last_5y if y < 0)
    cumulative_cfo = sum(input_data.cfo_last_5y)
    cumulative_pat = sum(input_data.pat_last_5y)

    disqualifying_event = (
        (negative_cfo_years >= 3)
        or (cumulative_pat <= 0)
        or (cumulative_pat > 0 and (cumulative_cfo / cumulative_pat) < 0.80)
    )

    guard = apply_track_record_guard(
        years_required=5,
        years_available=n,  # actual series length
        disqualifying_event_found=disqualifying_event,
    )

    citation, _ = compose_citation(input_data, fields_used)
    basis = (
        input_data.provenance["cfo_last_5y"].basis
        if "cfo_last_5y" in input_data.provenance
        else ReportingBasis.NOT_APPLICABLE
    )

    if guard is not None:
        if guard == CheckStatus.FAIL:
            return CheckResult(
                check_id=5,
                status=CheckStatus.FAIL,
                finding=f"Disqualifying cash conversion failure found in {n}-year record",
                reason_code="CASH_FLOW_DISQUALIFYING_SHORT_HISTORY",
                fields_used=fields_used,
                citation=citation,
                basis=basis,
            )
        return CheckResult(
            check_id=5,
            status=CheckStatus.INCONCLUSIVE,
            finding=f"Check 5: insufficient track record (only {n} years available vs 5 required)",
            reason_code="INSUFFICIENT_TRACK_RECORD",
            missing_data=f"insufficient track record (only {n} years available)",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    if negative_cfo_years >= 3:
        return CheckResult(
            check_id=5,
            status=CheckStatus.FAIL,
            finding=f"{negative_cfo_years} of last 5 years had negative CFO (>= 3 triggers fail)",
            reason_code="NEGATIVE_CFO_YEARS_GE_3",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    if cumulative_pat <= 0:
        return CheckResult(
            check_id=5,
            status=CheckStatus.FAIL,
            finding=f"cumulative 5-yr PAT {cumulative_pat} <= 0",
            reason_code="CUMULATIVE_PAT_LE_0",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    cfo_pat_ratio = cumulative_cfo / cumulative_pat
    if cfo_pat_ratio < 0.80:
        return CheckResult(
            check_id=5,
            status=CheckStatus.FAIL,
            finding=f"cumulative CFO/PAT ratio {round(cfo_pat_ratio, 2)} < 0.80",
            reason_code="CFO_PAT_RATIO_LT_0_80",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    return CheckResult(
        check_id=5,
        status=CheckStatus.PASS,
        finding=f"CFO/PAT ratio {round(cfo_pat_ratio, 2)} (>= 0.80), {negative_cfo_years} negative-CFO years (<= 2)",
        reason_code="CASH_CONVERSION_HEALTHY",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
    )


def check6_executive_stability(input_data: CompanyInput) -> CheckResult:
    """
    Check 6 — Executive Stability (Section A Q6)
    Phase1-Algorithms.md §8
    """
    fields_used = ["cfo_changes_last_3y", "restatement_of_past_accounts"]

    if (
        input_data.cfo_changes_last_3y is None
        or input_data.restatement_of_past_accounts is None
    ):
        return CheckResult(
            check_id=6,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 6 inconclusive due to missing CFO change count or restatement history",
            reason_code="CHECK_6_DATA_MISSING",
            missing_data="Check 6: missing CFO change count or restatement history",
            fields_used=fields_used,
        )

    disqualifying_event = (
        input_data.cfo_changes_last_3y > 1
        or input_data.restatement_of_past_accounts is True
    )

    guard = apply_track_record_guard(
        years_required=3,
        years_available=input_data.years_of_track_record_available,
        disqualifying_event_found=disqualifying_event,
    )

    citation, _ = compose_citation(input_data, fields_used)

    if guard is not None:
        if guard == CheckStatus.FAIL:
            return CheckResult(
                check_id=6,
                status=CheckStatus.FAIL,
                finding="Disqualifying executive instability found despite short track record",
                reason_code="EXECUTIVE_DISQUALIFYING_SHORT_HISTORY",
                fields_used=fields_used,
                citation=citation,
            )
        return CheckResult(
            check_id=6,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 6: insufficient track record (only "
            f"{input_data.years_of_track_record_available if input_data.years_of_track_record_available is not None else 'unknown'} "
            "years available vs 3 required)",
            reason_code="INSUFFICIENT_TRACK_RECORD",
            missing_data="Track record length not established or < 3 years",
            fields_used=fields_used,
            citation=citation,
        )

    if input_data.cfo_changes_last_3y > 1:
        return CheckResult(
            check_id=6,
            status=CheckStatus.FAIL,
            finding=f"{input_data.cfo_changes_last_3y} CFO changes in last 3 years (> 1 triggers fail)",
            reason_code="CFO_CHANGES_GT_1",
            fields_used=fields_used,
            citation=citation,
        )

    if input_data.restatement_of_past_accounts is True:
        return CheckResult(
            check_id=6,
            status=CheckStatus.FAIL,
            finding="retroactive restatement of past accounts",
            reason_code="ACCOUNTING_RESTATEMENT",
            fields_used=fields_used,
            citation=citation,
        )

    return CheckResult(
        check_id=6,
        status=CheckStatus.PASS,
        finding=f"{input_data.cfo_changes_last_3y} CFO change(s) (<= 1), no restatement",
        reason_code="EXECUTIVE_STABILITY_HEALTHY",
        fields_used=fields_used,
        citation=citation,
    )
