"""
Check functions 1 to 6 for Phase 1 Gatekeeper.
Strictly maps to Phase1-Algorithms-v3.md §3 to §8.
Pure functions — zero network or disk I/O.
"""

from typing import List, Optional

from backend.app.models.enums import (
    AuditOpinion,
    CheckStatus,
    CompanyType,
    Confidence,
    RegulatoryNature,
    ReportingBasis,
    RetrievalTier,
    WorkingCapitalCycleTier,
)
from backend.app.models.schemas import CheckResult, CompanyInput
from backend.app.engine.rules.config import Phase1RuleConfig


def _get_phase1_cfg(rule_config: Optional[Phase1RuleConfig] = None) -> Phase1RuleConfig:
    if rule_config is not None:
        return rule_config
    try:
        from backend.app.engine.rules.registry import get_active_rules_config
        return get_active_rules_config().phase1
    except Exception:
        return Phase1RuleConfig()

from .helpers import (
    apply_track_record_guard,
    assert_comparable,
    build_finding_suffix,
    compose_citation,
    derive_pledged_pct_of_total_shares,
    roll_up_confidence,
    sector_flag_threshold,
    verify_use_of_funds,
    working_capital_cycle_thresholds,
)

_DISQUALIFYING_REGULATORY_NATURES = {
    RegulatoryNature.FRAUD,
    RegulatoryNature.SIPHONING,
    RegulatoryNature.MANIPULATION,
    RegulatoryNature.ACCOUNTING_IRREGULARITY,
}


def check1_auditor_regulator(
    input_data: CompanyInput,
    rule_config: Optional[Phase1RuleConfig] = None,
) -> CheckResult:
    """
    Check 1 — Auditor & Regulator Integrity (Section A Q1)
    Phase1-Algorithms-v3.md §3. Rev 4: the fee-anomaly sub-check is now a
    revenue-normalized, industry-tiered test (Rules §2 Check 1.4 / §8.4-E),
    not a flat multiple of audit fees. audit_fees is secondary/non-binding.
    """
    fields_used = [
        "audit_opinion",
        "auditor_resigned_mid_tenure_last_3y",
        "regulatory_action",
        "legal_fees",
        "revenue",
        "industry_sector",
    ]

    if (
        input_data.auditor_resigned_mid_tenure_last_3y is None
        or input_data.audit_opinion is None
        or input_data.regulatory_action.active_or_past_5y is None
        or input_data.legal_fees is None
        or input_data.revenue is None
        or input_data.industry_sector is None
    ):
        return CheckResult(
            check_id=1,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 1 inconclusive due to missing inputs",
            reason_code="CHECK_1_DATA_MISSING",
            missing_data=(
                "Check 1: missing one or more of [auditor resignation history, "
                "audit opinion, regulatory action status, legal fees, revenue, "
                "industry sector classification]"
            ),
            fields_used=fields_used,
        )

    years_available = input_data.years_of_track_record_available
    disqualifying_event_found = (
        input_data.auditor_resigned_mid_tenure_last_3y is True
        or input_data.audit_opinion != AuditOpinion.CLEAN
        or input_data.regulatory_action.nature in _DISQUALIFYING_REGULATORY_NATURES
    )

    guard = apply_track_record_guard(
        years_required=3,
        years_available=years_available,
        disqualifying_event_found=disqualifying_event_found,
    )
    suffix = build_finding_suffix(3, years_available)
    confidence = roll_up_confidence(
        fields_used,
        {"regulatory_action": input_data.regulatory_action.retrieval_tier},
    )
    if guard is not None:
        citation, _ = compose_citation(input_data, fields_used)
        if guard == CheckStatus.FAIL:
            return CheckResult(
                check_id=1,
                status=CheckStatus.FAIL,
                finding="Disqualifying auditor/regulator issue found despite short track record" + suffix,
                reason_code="AUDITOR_DISQUALIFYING_SHORT_HISTORY",
                fields_used=fields_used,
                citation=citation,
                confidence=confidence,
            )
        return CheckResult(
            check_id=1,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 1: insufficient track record (only "
            f"{years_available if years_available is not None else 'unknown'} "
            "years available vs 3 required)" + suffix,
            reason_code="INSUFFICIENT_TRACK_RECORD",
            missing_data="Track record length not established or < 3 years",
            fields_used=fields_used,
            citation=citation,
            confidence=confidence,
        )

    fail_reasons: List[str] = []
    inconclusive_notes: List[str] = []
    pass_notes: List[str] = []

    if input_data.auditor_resigned_mid_tenure_last_3y is True:
        fail_reasons.append("AUDITOR_RESIGNED_MID_TENURE")

    if input_data.audit_opinion != AuditOpinion.CLEAN:
        fail_reasons.append(f"AUDIT_OPINION_NOT_CLEAN:{input_data.audit_opinion.value}")

    if (
        input_data.regulatory_action.active_or_past_5y is True
        and input_data.regulatory_action.nature is not None
        and input_data.regulatory_action.nature in _DISQUALIFYING_REGULATORY_NATURES
    ):
        fail_reasons.append(f"REGULATORY_ACTION:{input_data.regulatory_action.nature.value}")
    # Note: ROUTINE_PROCEDURAL nature is explicitly excluded — not a fail trigger.

    # Fee-anomaly sub-check — Rev 4 (Rules §2 Check 1.4 / §8.4-E). Primary test
    # is revenue-normalized and industry-tiered; audit-fee ratio is a
    # non-binding secondary observation only.
    fee_mismatch = assert_comparable(input_data, ["legal_fees", "revenue"])
    if fee_mismatch is not None:
        inconclusive_notes.append(f"legal-fee-to-revenue check not computable: {fee_mismatch}")
    elif input_data.revenue <= 0:
        inconclusive_notes.append("revenue is zero/negative; legal-fee-to-revenue check undefined")
    else:
        legal_pct_revenue = (input_data.legal_fees / input_data.revenue) * 100.0
        flag_threshold = sector_flag_threshold(input_data.industry_sector)
        surge = (
            input_data.legal_fees_prior_year is not None
            and input_data.legal_fees_prior_year > 0
            and (input_data.legal_fees / input_data.legal_fees_prior_year) > 2.0
            and input_data.legal_fee_surge_explained is not True
        )
        if legal_pct_revenue > flag_threshold:
            fail_reasons.append(
                f"LEGAL_PCT_REVENUE_EXCEEDS_SECTOR_BAND:{round(legal_pct_revenue, 3)}%>"
                f"{flag_threshold}% ({input_data.industry_sector.value})"
            )
        elif surge:
            fail_reasons.append("LEGAL_FEES_UNEXPLAINED_SURGE_OVER_2X_YOY")
        else:
            # Secondary corroboration only (Rules §8.4-E(c)) — never a
            # standalone fail trigger.
            secondary_mismatch = assert_comparable(input_data, ["legal_fees", "audit_fees"])
            if secondary_mismatch is None and input_data.audit_fees is not None and input_data.audit_fees > 0:
                ratio = input_data.legal_fees / input_data.audit_fees
                if ratio > 5.0:
                    pass_notes.append(
                        f"legal/audit fee ratio {round(ratio, 2)}x is elevated but legal spend "
                        "is within the sector's revenue-intensity band, so not treated as a fail trigger"
                    )

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
            finding="; ".join(fail_reasons) + suffix,
            reason_code="; ".join(fail_reasons),
            fields_used=fields_used,
            citation=citation,
            basis=basis,
            confidence=confidence,
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
            confidence=confidence,
        )

    note_suffix = (" — " + "; ".join(pass_notes)) if pass_notes else ""
    return CheckResult(
        check_id=1,
        status=CheckStatus.PASS,
        finding=(
            "clean opinion, no mid-tenure resignation, no disqualifying regulatory action, "
            "legal spend within sector revenue-intensity band" + note_suffix + suffix
        ),
        reason_code="AUDITOR_REGULATOR_CLEAN",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
        confidence=confidence,
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


def check2_promoter_pledge(
    input_data: CompanyInput,
    rule_config: Optional[Phase1RuleConfig] = None,
) -> CheckResult:
    """
    Check 2 — Promoter Pledge & Encumbrance (Section A Q2)
    Phase1-Algorithms.md §4
    """
    cfg = _get_phase1_cfg(rule_config)

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

    # Rev 3 — confidence keyed on how pledged_pct_history_last_4q was sourced
    # per Rules §8.4-B: an actual quarterly series (PRIMARY) vs a single
    # figure plus a "no new pledge" filing standing in for a trend (FALLBACK).
    confidence = roll_up_confidence(
        fields_used,
        {"pledged_pct_history_last_4q": input_data.pledged_pct_history_retrieval_tier},
    )
    trend_finding_note = ""
    if input_data.pledged_pct_history_retrieval_tier == RetrievalTier.FALLBACK:
        trend_finding_note = (
            " (trend inferred from latest-quarter figure plus a no-new-pledge "
            "compliance filing, not a confirmed quarterly series)"
        )

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
            input_data.pledged_pct_of_promoter_holding > cfg.promoter_pledge_fail_pct
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
                    f"{pledged_of_total}% of total shares" + trend_finding_note
                ),
                reason_code="LOW_BASE_PLEDGE_MATERIAL",
                fields_used=fields_used + ["pledged_pct_of_total_shares"],
                citation=citation,
                confidence=confidence,
            )
        else:
            return CheckResult(
                check_id=2,
                status=CheckStatus.PASS,
                finding=(
                    f"pledge % elevated ({input_data.pledged_pct_of_promoter_holding}%) due to small promoter base, "
                    f"total shares pledged {pledged_of_total}% <= 0.5% — not treated as a red flag" + trend_finding_note
                ),
                reason_code="LOW_BASE_PLEDGE_SAFE",
                fields_used=fields_used + ["pledged_pct_of_total_shares"],
                citation=citation,
                confidence=confidence,
            )

    # Standard thresholds
    if input_data.pledged_pct_of_promoter_holding > cfg.promoter_pledge_fail_pct:
        return CheckResult(
            check_id=2,
            status=CheckStatus.FAIL,
            finding=f"pledge {input_data.pledged_pct_of_promoter_holding}% vs {cfg.promoter_pledge_fail_pct}% limit (absolute threshold)" + trend_finding_note,
            reason_code="PLEDGE_EXCEEDS_10PCT",
            fields_used=fields_used,
            citation=citation,
            confidence=confidence,
        )

    if trend_rising:
        return CheckResult(
            check_id=2,
            status=CheckStatus.FAIL,
            finding="pledged % rising over last 2-4 quarters (or unexplained single-quarter spike > 2pp)" + trend_finding_note,
            reason_code="PLEDGE_RISING_TREND",
            fields_used=fields_used,
            citation=citation,
            confidence=confidence,
        )

    return CheckResult(
        check_id=2,
        status=CheckStatus.PASS,
        finding=f"pledge {input_data.pledged_pct_of_promoter_holding}% (<= {cfg.promoter_pledge_fail_pct}%), stable/declining over last 4 quarters" + trend_finding_note,
        reason_code="PLEDGE_SAFE",
        fields_used=fields_used,
        citation=citation,
        confidence=confidence,
    )


def check3_related_party(
    input_data: CompanyInput,
    rule_config: Optional[Phase1RuleConfig] = None,
) -> CheckResult:
    """
    Check 3 — Related-Party 'Leakage' (Section A Q3)
    Phase1-Algorithms.md §5
    """
    cfg = _get_phase1_cfg(rule_config)
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

    if rpt_pct > cfg.rpt_sales_purchases_fail_pct:
        return CheckResult(
            check_id=3,
            status=CheckStatus.FAIL,
            finding=f"RPT {rpt_pct}% of revenue vs {cfg.rpt_sales_purchases_fail_pct}% limit",
            reason_code="RPT_EXCEEDS_LIMIT",
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
        finding=f"RPT {rpt_pct}% of revenue (<= {cfg.rpt_sales_purchases_fail_pct}%), no suspicious affiliate transactions",
        reason_code="RPT_NORMAL",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
    )


def check4_contingent_liabilities(
    input_data: CompanyInput,
    rule_config: Optional[Phase1RuleConfig] = None,
) -> CheckResult:
    """
    Check 4 — Contingent Liabilities (Section A Q4)
    Phase1-Algorithms-v3.md §6. Rev 5: the flat total-over-net-worth ratio is
    replaced by a litigation-vs-routine split (Rules §2 Check 4 / §8.4-F) —
    routine guarantee/LC/bills-discounted exposure is excluded entirely.
    net_worth <= 0 remains an unconditional FAIL.
    """
    cfg = _get_phase1_cfg(rule_config)
    if input_data.net_worth is None:
        return CheckResult(
            check_id=4,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 4 inconclusive due to missing inputs",
            reason_code="CHECK_4_DATA_MISSING",
            missing_data="Check 4: missing net worth figure",
            fields_used=["net_worth"],
        )

    if input_data.net_worth <= 0:
        nw_citation, _ = compose_citation(input_data, ["net_worth"])
        basis = (
            input_data.provenance["net_worth"].basis
            if "net_worth" in input_data.provenance
            else ReportingBasis.NOT_APPLICABLE
        )
        return CheckResult(
            check_id=4,
            status=CheckStatus.FAIL,
            finding=f"net worth {input_data.net_worth} <= 0 (broken balance sheet)",
            reason_code="NEGATIVE_NET_WORTH",
            fields_used=["net_worth"],
            citation=nw_citation,
            basis=basis,
        )

    # Rev 5 §8.4-F step 4: an AR disclosing only a lump total, with no
    # Schedule III sub-category breakdown, gets an immateriality fast-path.
    if input_data.contingent_liabilities_breakdown_available is not True:
        fields_used = ["contingent_liabilities", "net_worth"]
        if input_data.contingent_liabilities is None:
            return CheckResult(
                check_id=4,
                status=CheckStatus.INCONCLUSIVE,
                finding="Check 4 inconclusive due to missing inputs",
                reason_code="CHECK_4_DATA_MISSING",
                missing_data="Check 4: no contingent liabilities figure (lump total or sub-category breakdown) available",
                fields_used=fields_used,
            )

        mismatch = assert_comparable(input_data, fields_used)
        if mismatch is not None:
            return CheckResult(
                check_id=4,
                status=CheckStatus.INCONCLUSIVE,
                finding=f"Check 4: {mismatch}",
                reason_code="CHECK_4_COMPARABILITY_MISMATCH",
                missing_data=f"Check 4: {mismatch}",
                fields_used=fields_used,
            )

        lump_pct = round((input_data.contingent_liabilities / input_data.net_worth) * 100.0, 2)
        lump_citation, _ = compose_citation(input_data, fields_used)
        basis = (
            input_data.provenance["net_worth"].basis
            if "net_worth" in input_data.provenance
            else ReportingBasis.NOT_APPLICABLE
        )
        if lump_pct <= 5.0:
            return CheckResult(
                check_id=4,
                status=CheckStatus.PASS,
                finding=(
                    f"contingent liabilities {lump_pct}% of net worth (<= 5%, immaterial — "
                    "no Schedule III sub-category breakdown was disclosed, but the total is "
                    "small enough that a litigation/routine split cannot change the verdict)"
                ),
                reason_code="CONTINGENT_LIABILITIES_LUMP_IMMATERIAL",
                fields_used=fields_used,
                citation=lump_citation,
                basis=basis,
                confidence=Confidence.MEDIUM,
            )
        return CheckResult(
            check_id=4,
            status=CheckStatus.INCONCLUSIVE,
            finding=(
                f"Check 4: contingent liabilities disclosed as a single total ({lump_pct}% of "
                "net worth) with no Schedule III sub-category breakdown — litigation/routine "
                "split not available (§8.4-F)"
            ),
            reason_code="CONTINGENT_LIABILITIES_BREAKDOWN_UNAVAILABLE",
            missing_data=(
                f"contingent liabilities disclosed as a single total ({lump_pct}% of net worth) "
                "with no Schedule III sub-category breakdown"
            ),
            fields_used=fields_used,
            citation=lump_citation,
            basis=basis,
        )

    # Primary path: the litigation/routine breakdown was extracted per §8.4-F.
    fields_used = ["litigation_claims_exposure", "routine_guarantee_exposure", "net_worth"]
    if input_data.litigation_claims_exposure is None:
        return CheckResult(
            check_id=4,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 4 inconclusive due to missing inputs",
            reason_code="CHECK_4_DATA_MISSING",
            missing_data="Check 4: breakdown flagged available but litigation_claims_exposure missing",
            fields_used=fields_used,
        )

    mismatch = assert_comparable(input_data, ["litigation_claims_exposure", "net_worth"])
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
    ratio_pct = round((input_data.litigation_claims_exposure / input_data.net_worth) * 100.0, 2)
    thresh = 20.0

    if ratio_pct > thresh:
        return CheckResult(
            check_id=4,
            status=CheckStatus.FAIL,
            finding=(
                f"litigation & claims exposure {ratio_pct}% of net worth vs 20% limit "
                "(routine guarantees/LCs/bills discounted excluded, §8.4-F)"
            ),
            reason_code="LITIGATION_CLAIMS_EXCEED_20PCT",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    return CheckResult(
        check_id=4,
        status=CheckStatus.PASS,
        finding=(
            f"litigation & claims exposure {ratio_pct}% of net worth (<= 20%); "
            "routine business-linked exposure excluded from this ratio per §8.4-F"
        ),
        reason_code="LITIGATION_CLAIMS_SAFE",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
    )


def check5_cash_conversion(
    input_data: CompanyInput,
    rule_config: Optional[Phase1RuleConfig] = None,
) -> CheckResult:
    """
    Check 5 — Show Me the Cash (Section A Q5)
    Phase1-Algorithms-v3.md §7. Rev 5: flat 0.80/>=3-of-5 rule replaced by
    working-capital-cycle tiering (§8.4-G), a global 0.50 hard floor, and a
    not-applicable path for lending institutions. Rev 6: every trigger except
    cumulative PAT <= 0 routes through verify_use_of_funds() (§8.4-H) before
    resolving to FAIL — a verified-benign shortfall becomes a PASS carrying
    has_mandatory_warning = true.
    """
    cfg = _get_phase1_cfg(rule_config)
    if input_data.working_capital_cycle_tier is None:
        return CheckResult(
            check_id=5,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 5 inconclusive due to missing inputs",
            reason_code="CHECK_5_DATA_MISSING",
            missing_data="Check 5: missing working-capital-cycle classification (Rules §8.4-G)",
            fields_used=["working_capital_cycle_tier"],
        )

    if input_data.working_capital_cycle_tier == WorkingCapitalCycleTier.LENDING_INSTITUTION_NA:
        return CheckResult(
            check_id=5,
            status=CheckStatus.INCONCLUSIVE,
            finding=(
                "not applicable — CFO/PAT is not a meaningful metric for lending institutions "
                "(banks/NBFCs/insurers); their operating cash flow is dominated by loan-book/"
                "deposit movement, not P&L-linked working capital (Rules §8.4-G)"
            ),
            reason_code="LENDING_INSTITUTION_NOT_APPLICABLE",
            missing_data="CFO/PAT not a meaningful metric for lending institutions",
            fields_used=["working_capital_cycle_tier"],
        )

    fields_used = ["cfo_last_5y", "pat_last_5y", "working_capital_cycle_tier"]

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

    thresholds = working_capital_cycle_thresholds(input_data.working_capital_cycle_tier)

    negative_cfo_years = sum(1 for y in input_data.cfo_last_5y if y < 0)
    cumulative_cfo = sum(input_data.cfo_last_5y)
    cumulative_pat = sum(input_data.pat_last_5y)
    cfo_pat_ratio = (cumulative_cfo / cumulative_pat) if cumulative_pat > 0 else None

    # Rev 6: cumulative_pat <= 0 is the one trigger with no verification path.
    pat_negative_or_zero = cumulative_pat <= 0

    negative_years_breach = negative_cfo_years >= thresholds["negative_years_trigger"]
    hard_floor_breach = cfo_pat_ratio is not None and cfo_pat_ratio < 0.50
    target_floor = thresholds["cfo_pat_floor"] if input_data.working_capital_cycle_tier else cfg.cfo_pat_ratio_fail_floor
    tier_floor_breach = cfo_pat_ratio is not None and cfo_pat_ratio < target_floor
    any_verifiable_trigger = negative_years_breach or hard_floor_breach or tier_floor_breach

    verification = None
    if any_verifiable_trigger and not pat_negative_or_zero:
        verification = verify_use_of_funds(input_data, cumulative_pat, cumulative_cfo)
    verified_ok = verification is not None and verification["verified"] is True

    disqualifying_event = pat_negative_or_zero or (any_verifiable_trigger and not verified_ok)

    guard = apply_track_record_guard(
        years_required=5,
        years_available=n,  # actual series length, not the company-wide field
        disqualifying_event_found=disqualifying_event,
    )
    suffix = build_finding_suffix(5, n)

    citation, _ = compose_citation(input_data, fields_used)
    basis = (
        input_data.provenance["cfo_last_5y"].basis
        if "cfo_last_5y" in input_data.provenance
        else ReportingBasis.NOT_APPLICABLE
    )

    if guard is not None:
        gap_note = ""
        if n < 5:
            gap_note = (
                ""
                if input_data.years_5y_series_gap_checked is True
                else " — 5-year completeness sub-step (Rules §8.4-C) not recorded as attempted"
            )
        if guard == CheckStatus.FAIL:
            return CheckResult(
                check_id=5,
                status=CheckStatus.FAIL,
                finding=f"Disqualifying cash conversion failure found in {n}-year record" + suffix + gap_note,
                reason_code="CASH_FLOW_DISQUALIFYING_SHORT_HISTORY",
                fields_used=fields_used,
                citation=citation,
                basis=basis,
            )
        return CheckResult(
            check_id=5,
            status=CheckStatus.INCONCLUSIVE,
            finding=f"Check 5: insufficient track record (only {n} years available vs 5 required)" + suffix + gap_note,
            reason_code="INSUFFICIENT_TRACK_RECORD",
            missing_data=f"insufficient track record (only {n} years available)" + gap_note,
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    if pat_negative_or_zero:
        return CheckResult(
            check_id=5,
            status=CheckStatus.FAIL,
            finding=f"cumulative 5-yr PAT {cumulative_pat} <= 0" + suffix,
            reason_code="CUMULATIVE_PAT_LE_0",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    if any_verifiable_trigger:
        trigger_desc: List[str] = []
        if negative_years_breach:
            trigger_desc.append(
                f"{negative_cfo_years} of last 5 years had negative CFO "
                f"(>= {thresholds['negative_years_trigger']} triggers this sector's tier)"
            )
        if hard_floor_breach and cfo_pat_ratio is not None:
            trigger_desc.append(f"CFO/PAT ratio {round(cfo_pat_ratio, 3)} < 0.50 global hard floor")
        elif tier_floor_breach and cfo_pat_ratio is not None:
            trigger_desc.append(
                f"CFO/PAT ratio {round(cfo_pat_ratio, 3)} < {thresholds['cfo_pat_floor']} sector tier threshold"
            )
        trigger_text = "; ".join(trigger_desc)

        if verified_ok and verification is not None:
            raw_notes = verification.get("notes")
            notes_list = raw_notes if isinstance(raw_notes, list) else []
            notes_str = "; ".join(str(n) for n in notes_list)
            uof_fields = fields_used + [
                "revenue_last_5y",
                "cumulative_working_capital_change_5y",
                "liquid_cushion_first_year",
                "liquid_cushion_last_year",
            ]
            uof_citation, _ = compose_citation(input_data, uof_fields)
            return CheckResult(
                check_id=5,
                status=CheckStatus.PASS,
                finding=(
                    "WARNING — " + trigger_text + ", but verified as business-expansion-linked "
                    "per Rules §8.4-H: " + notes_str + suffix
                ),
                reason_code="CASH_CONVERSION_VERIFIED_WARNING",
                fields_used=uof_fields,
                citation=uof_citation,
                basis=basis,
                has_mandatory_warning=True,
            )

        if verification is None:
            return CheckResult(
                check_id=5,
                status=CheckStatus.FAIL,
                finding=(
                    trigger_text + " — use-of-funds verification (§8.4-H) could not be attempted: "
                    "revenue_last_5y / cumulative_working_capital_change_5y / liquid_cushion "
                    "figures not available" + suffix
                ),
                reason_code="CASH_CONVERSION_TRIGGER_UNVERIFIED",
                fields_used=fields_used,
                citation=citation,
                basis=basis,
            )

        raw_notes = verification.get("notes")
        notes_list = raw_notes if isinstance(raw_notes, list) else []
        notes_str = "; ".join(str(n) for n in notes_list)
        return CheckResult(
            check_id=5,
            status=CheckStatus.FAIL,
            finding=(
                trigger_text + " — use-of-funds verification (§8.4-H) attempted and did not "
                "clear: " + notes_str + suffix
            ),
            reason_code="CASH_CONVERSION_TRIGGER_FAILED_VERIFICATION",
            fields_used=fields_used,
            citation=citation,
            basis=basis,
        )

    return CheckResult(
        check_id=5,
        status=CheckStatus.PASS,
        finding=(
            f"CFO/PAT ratio {round(cfo_pat_ratio, 3) if cfo_pat_ratio is not None else cfo_pat_ratio} "
            f"(>= {thresholds['cfo_pat_floor']} tier threshold), {negative_cfo_years} negative-CFO years "
            f"(< {thresholds['negative_years_trigger']} trigger)" + suffix
        ),
        reason_code="CASH_CONVERSION_HEALTHY",
        fields_used=fields_used,
        citation=citation,
        basis=basis,
    )


def check6_executive_stability(
    input_data: CompanyInput,
    rule_config: Optional[Phase1RuleConfig] = None,
) -> CheckResult:
    """
    Check 6 — Executive Stability (Section A Q6)
    Phase1-Algorithms.md §8
    """
    cfg = _get_phase1_cfg(rule_config)
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

    years_available = input_data.years_of_track_record_available
    guard = apply_track_record_guard(
        years_required=3,
        years_available=years_available,
        disqualifying_event_found=disqualifying_event,
    )
    suffix = build_finding_suffix(3, years_available)

    citation, _ = compose_citation(input_data, fields_used)
    confidence = roll_up_confidence(
        fields_used,
        {"restatement_of_past_accounts": input_data.restatement_search_retrieval_tier},
    )

    if guard is not None:
        if guard == CheckStatus.FAIL:
            return CheckResult(
                check_id=6,
                status=CheckStatus.FAIL,
                finding="Disqualifying executive instability found despite short track record" + suffix,
                reason_code="EXECUTIVE_DISQUALIFYING_SHORT_HISTORY",
                fields_used=fields_used,
                citation=citation,
                confidence=confidence,
            )
        return CheckResult(
            check_id=6,
            status=CheckStatus.INCONCLUSIVE,
            finding="Check 6: insufficient track record (only "
            f"{years_available if years_available is not None else 'unknown'} "
            "years available vs 3 required)" + suffix,
            reason_code="INSUFFICIENT_TRACK_RECORD",
            missing_data="Track record length not established or < 3 years",
            fields_used=fields_used,
            citation=citation,
            confidence=confidence,
        )

    # Rev 3 — Rules §8.4-D disambiguation: an ESG/BRSR-only restatement found
    # and excluded must be visible even on a PASS.
    esg_note = ""
    if input_data.restatement_esg_only_excluded is True:
        esg_note = (
            " (an ESG/BRSR data restatement was found and confirmed unrelated to the "
            "financial statements — does not count toward this check)"
        )

    if input_data.cfo_changes_last_3y > 1:
        return CheckResult(
            check_id=6,
            status=CheckStatus.FAIL,
            finding=f"{input_data.cfo_changes_last_3y} CFO changes in last 3 years (> 1 triggers fail)" + suffix,
            reason_code="CFO_CHANGES_GT_1",
            fields_used=fields_used,
            citation=citation,
            confidence=confidence,
        )

    if input_data.restatement_of_past_accounts is True:
        return CheckResult(
            check_id=6,
            status=CheckStatus.FAIL,
            finding="retroactive restatement of past accounts" + suffix,
            reason_code="ACCOUNTING_RESTATEMENT",
            fields_used=fields_used,
            citation=citation,
            confidence=confidence,
        )

    return CheckResult(
        check_id=6,
        status=CheckStatus.PASS,
        finding=f"{input_data.cfo_changes_last_3y} CFO change(s) (<= 1), no restatement" + suffix + esg_note,
        reason_code="EXECUTIVE_STABILITY_HEALTHY",
        fields_used=fields_used,
        citation=citation,
        confidence=confidence,
    )
