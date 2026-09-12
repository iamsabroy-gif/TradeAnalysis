"""
Implementation of Checks 7 to 18 for Phase 2 Gatekeeper (Business Quality Check).
Strictly maps to Phase2-Rules.md §2.
"""

from typing import List, Optional
from backend.app.models.enums import (
    Confidence,
    MoatType,
    Phase2CheckGroup,
    Phase2CheckStatus,
    Phase2Sector,
)
from backend.app.models.phase2_schemas import (
    CompanyPhase2Input,
    Phase2CheckResult,
)
from .calculator import (
    apply_trend_modifier,
    compute_ccc,
    compute_debt_to_equity,
    compute_interest_coverage,
    compute_median,
    compute_net_debt,
    compute_net_debt_to_ebitda,
    compute_roce,
    is_consecutively_decreasing,
    is_consecutively_increasing,
)
from .matrix import SectorThresholds, get_sector_thresholds


def check7_return_on_capital(
    data: CompanyPhase2Input,
    thresholds: SectorThresholds,
) -> Phase2CheckResult:
    """Check 7: Return on Capital Employed (5-year median, trend, vs sector matrix)."""
    if not data.financials:
        return Phase2CheckResult(
            check_id="check7_return_on_capital",
            q_number="Q19, Q20",
            title="Return on Capital Employed (RoCE)",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="No financial statement history provided for RoCE calculation.",
            source="P&L and Balance Sheet",
            confidence=Confidence.LOW,
            inconclusive_reason="Missing 5-year financials.",
        )

    roce_series: List[float] = []
    for f in data.financials:
        if f.roce_pct is not None:
            roce_series.append(f.roce_pct)
        else:
            r = compute_roce(f.ebit, f.total_equity, f.gross_debt, f.cash_and_equivalents)
            roce_series.append(r)

    median_roce = compute_median(roce_series)
    latest_roce = roce_series[-1] if roce_series else 0.0

    # Count year-over-year declines in 5-year window
    declines = 0
    for i in range(len(roce_series) - 1):
        if roce_series[i + 1] < roce_series[i]:
            declines += 1

    # Check FAIL conditions
    is_fail = False
    fail_reasons = []
    if median_roce < thresholds.roce_fail_ceiling:
        is_fail = True
        fail_reasons.append(f"5-yr median RoCE ({median_roce:.1f}%) < {thresholds.roce_fail_ceiling:.1f}% sector floor")
    if len(roce_series) >= 5 and declines >= 4 and latest_roce < 15.0:
        is_fail = True
        fail_reasons.append(f"RoCE declined in {declines} of last 5 years and latest year ({latest_roce:.1f}%) < 15%")
    if latest_roce < 0:
        is_fail = True
        fail_reasons.append(f"Latest-year RoCE is negative ({latest_roce:.1f}%)")

    threshold_str = f"Pass >= {thresholds.roce_pass_floor:.1f}%, Fail < {thresholds.roce_fail_ceiling:.1f}%"

    if is_fail:
        status = Phase2CheckStatus.FAIL
        finding = f"FAIL: {'; '.join(fail_reasons)}."
        return Phase2CheckResult(
            check_id="check7_return_on_capital",
            q_number="Q19, Q20",
            title="Return on Capital Employed (RoCE)",
            group=Phase2CheckGroup.EARNINGS,
            status=status,
            raw_metric_value=median_roce,
            threshold_applied=threshold_str,
            finding=finding,
            source="P&L, Balance Sheet, Screener.in",
            fields_used=["ebit", "total_equity", "gross_debt", "cash_and_equivalents"],
        )

    # Check PASS / CONCERN
    if median_roce >= thresholds.roce_pass_floor and not (len(roce_series) >= 3 and is_consecutively_decreasing(roce_series, 3)):
        initial_status = Phase2CheckStatus.PASS
    else:
        initial_status = Phase2CheckStatus.CONCERN

    # Trend modifier: 3 consecutive years
    improving_3y = is_consecutively_increasing(roce_series, 3)
    deteriorating_3y = is_consecutively_decreasing(roce_series, 3)
    final_status, mod_applied = apply_trend_modifier(initial_status, improving_3y, deteriorating_3y)

    finding = f"5-yr median RoCE is {median_roce:.1f}% (latest: {latest_roce:.1f}%). {threshold_str}."
    if mod_applied:
        if final_status == Phase2CheckStatus.PASS:
            finding += " Upgraded from CONCERN to PASS via Trend Modifier (3 consecutive years of improvement)."
        else:
            finding += " Downgraded from PASS to CONCERN via Trend Modifier (3 consecutive years of deterioration)."

    return Phase2CheckResult(
        check_id="check7_return_on_capital",
        q_number="Q19, Q20",
        title="Return on Capital Employed (RoCE)",
        group=Phase2CheckGroup.EARNINGS,
        status=final_status,
        raw_metric_value=median_roce,
        threshold_applied=threshold_str,
        trend_modifier_applied=mod_applied,
        original_status=initial_status if mod_applied else None,
        finding=finding,
        source="P&L, Balance Sheet, Screener.in",
        fields_used=["ebit", "total_equity", "gross_debt", "cash_and_equivalents"],
        what_would_clear=f"Sustain 5-year median RoCE >= {thresholds.roce_pass_floor:.1f}%" if final_status == Phase2CheckStatus.CONCERN else None,
    )


def check8_margin_trajectory(
    data: CompanyPhase2Input,
) -> Phase2CheckResult:
    """Check 8: Margin Trajectory (Gross, EBITDA, Net Margin trends and drivers)."""
    if not data.financials:
        return Phase2CheckResult(
            check_id="check8_margin_trajectory",
            q_number="Q19",
            title="Margin Trajectory",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="Missing financial history to evaluate margins.",
            source="P&L, MD&A",
            confidence=Confidence.LOW,
            inconclusive_reason="No financial data.",
        )

    ebitda_margins: List[float] = []
    net_margins: List[float] = []
    for f in data.financials:
        em = f.ebitda_margin_pct if f.ebitda_margin_pct is not None else ((f.ebitda / f.revenue) * 100.0 if f.revenue > 0 else 0.0)
        nm = f.net_margin_pct if f.net_margin_pct is not None else ((f.pat / f.revenue) * 100.0 if f.revenue > 0 else 0.0)
        ebitda_margins.append(em)
        net_margins.append(nm)

    latest_ebitda_margin = ebitda_margins[-1]
    last3_net_negative_count = sum(1 for m in net_margins[-3:] if m < 0)

    # 3-year average EBITDA margin and change
    last3_ebitda = ebitda_margins[-3:] if len(ebitda_margins) >= 3 else ebitda_margins
    avg3_ebitda = sum(last3_ebitda) / len(last3_ebitda) if last3_ebitda else 0.0
    ebitda_drop_pct_of_avg = 0.0
    if len(last3_ebitda) >= 3 and avg3_ebitda > 0:
        drop = last3_ebitda[0] - last3_ebitda[-1]
        ebitda_drop_pct_of_avg = (drop / avg3_ebitda) * 100.0

    # Margin moves without identified driver are inconclusive
    if not data.margin_driver_disclosed and abs(ebitda_drop_pct_of_avg) > 10.0:
        return Phase2CheckResult(
            check_id="check8_margin_trajectory",
            q_number="Q19",
            title="Margin Trajectory",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding=f"EBITDA margin shifted by {ebitda_drop_pct_of_avg:.1f}% of 3-yr average without identified driver in MD&A or concall.",
            source="P&L, MD&A",
            confidence=Confidence.MEDIUM,
            inconclusive_reason="Unexplained margin move.",
            what_would_clear="Disclose primary driver of margin contraction in MD&A/investor call.",
        )

    # Check FAIL conditions
    if latest_ebitda_margin <= 0:
        return Phase2CheckResult(
            check_id="check8_margin_trajectory",
            q_number="Q19",
            title="Margin Trajectory",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=latest_ebitda_margin,
            threshold_applied="EBITDA margin > 0%",
            finding=f"FAIL: Latest-year EBITDA margin is negative or zero ({latest_ebitda_margin:.1f}%).",
            source="P&L",
            fields_used=["revenue", "ebitda"],
        )

    if ebitda_drop_pct_of_avg > 25.0:
        return Phase2CheckResult(
            check_id="check8_margin_trajectory",
            q_number="Q19",
            title="Margin Trajectory",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=ebitda_drop_pct_of_avg,
            threshold_applied="3-yr EBITDA margin drop <= 25% of 3-yr average",
            finding=f"FAIL: EBITDA margin contracted by {ebitda_drop_pct_of_avg:.1f}% of its 3-year average (> 25% limit).",
            source="P&L",
            fields_used=["ebitda_margin_pct"],
        )

    if last3_net_negative_count >= 2:
        return Phase2CheckResult(
            check_id="check8_margin_trajectory",
            q_number="Q19",
            title="Margin Trajectory",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.FAIL,
            finding=f"FAIL: Net margin was negative in {last3_net_negative_count} of the last 3 years.",
            source="P&L",
            fields_used=["pat", "revenue"],
        )

    # Check CONCERN vs PASS
    if 10.0 <= ebitda_drop_pct_of_avg <= 25.0:
        return Phase2CheckResult(
            check_id="check8_margin_trajectory",
            q_number="Q19",
            title="Margin Trajectory",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.CONCERN,
            raw_metric_value=ebitda_drop_pct_of_avg,
            threshold_applied="EBITDA margin contraction < 10% of 3-yr avg",
            finding=f"CONCERN: EBITDA margin contracted by {ebitda_drop_pct_of_avg:.1f}% of its 3-year average (10-25% zone).",
            source="P&L, MD&A",
            fields_used=["ebitda_margin_pct"],
            what_would_clear="Stabilize EBITDA margin within ±10% relative variance.",
        )

    return Phase2CheckResult(
        check_id="check8_margin_trajectory",
        q_number="Q19",
        title="Margin Trajectory",
        group=Phase2CheckGroup.EARNINGS,
        status=Phase2CheckStatus.PASS,
        raw_metric_value=latest_ebitda_margin,
        threshold_applied="Stable EBITDA margin (within ±10% variance) and positive net margin",
        finding=f"PASS: Latest EBITDA margin is {latest_ebitda_margin:.1f}%, trajectory is stable/rising over 3 years.",
        source="P&L, MD&A",
        fields_used=["revenue", "ebitda", "pat"],
    )


def check9_segment_economics(
    data: CompanyPhase2Input,
) -> Phase2CheckResult:
    """Check 9: Segment Economics (Dominant segment revenue & margin health)."""
    if len(data.segments) <= 1:
        return Phase2CheckResult(
            check_id="check9_segment_economics",
            q_number="Q18",
            title="Segment Economics",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.NOT_APPLICABLE,
            finding="NOT_APPLICABLE: Company reports a single operating segment; evaluated via Check 8.",
            source="Annual Report -> Segment Reporting Note",
        )

    total_rev = sum(s.history[-1].revenue for s in data.segments if s.history)
    if total_rev <= 0:
        return Phase2CheckResult(
            check_id="check9_segment_economics",
            q_number="Q18",
            title="Segment Economics",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="Segment revenue totals are missing or zero.",
            source="Annual Report",
            inconclusive_reason="No segment revenue data.",
        )

    # Check if segment results/margins are disclosed
    has_results = any(h.margin_pct is not None or h.segment_result is not None for s in data.segments for h in s.history)
    if not has_results:
        return Phase2CheckResult(
            check_id="check9_segment_economics",
            q_number="Q18",
            title="Segment Economics",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="Company reports multiple segments but discloses revenue only, without segment results/margins.",
            source="Annual Report -> Segment Reporting Note",
            inconclusive_reason="Missing segment profitability disclosure.",
            what_would_clear="Segment results and profit margins disclosed in quarterly/annual filings.",
        )

    # Identify dominant segment (>40% revenue) and other material segments (>=10%)
    dominant_segment = None
    concern_segments = []
    for s in data.segments:
        if not s.history:
            continue
        seg_rev = s.history[-1].revenue
        pct = (seg_rev / total_rev) * 100.0
        rev_history = [h.revenue for h in s.history]
        margin_history = [
            h.margin_pct if h.margin_pct is not None else ((h.segment_result / h.revenue * 100.0) if (h.segment_result and h.revenue > 0) else 0.0)
            for h in s.history
        ]

        rev_declining = is_consecutively_decreasing(rev_history, 2)
        margin_declining = is_consecutively_decreasing(margin_history, 2)

        if pct > 40.0:
            dominant_segment = (s.name, pct, rev_declining, margin_declining)
        elif pct >= 10.0 and rev_declining and margin_declining:
            concern_segments.append(s.name)

    if dominant_segment and dominant_segment[2] and dominant_segment[3]:
        return Phase2CheckResult(
            check_id="check9_segment_economics",
            q_number="Q18",
            title="Segment Economics",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.FAIL,
            finding=f"FAIL: Dominant segment '{dominant_segment[0]}' ({dominant_segment[1]:.1f}% of rev) shows both declining revenue and margin over 3 years.",
            source="Annual Report -> Segment Reporting",
            fields_used=["segment_revenue", "segment_margin"],
        )

    if concern_segments:
        return Phase2CheckResult(
            check_id="check9_segment_economics",
            q_number="Q18",
            title="Segment Economics",
            group=Phase2CheckGroup.EARNINGS,
            status=Phase2CheckStatus.CONCERN,
            finding=f"CONCERN: Material segment(s) {concern_segments} (>=10% of revenue) show both declining revenue and margins.",
            source="Annual Report -> Segment Reporting",
            what_would_clear="Stabilize revenue and margins in underperforming segments.",
        )

    return Phase2CheckResult(
        check_id="check9_segment_economics",
        q_number="Q18",
        title="Segment Economics",
        group=Phase2CheckGroup.EARNINGS,
        status=Phase2CheckStatus.PASS,
        finding=f"PASS: Primary segments are growing or stable on revenue and margins.",
        source="Annual Report -> Segment Reporting",
    )


def check10_leverage_quantum_and_trend(
    data: CompanyPhase2Input,
    thresholds: SectorThresholds,
) -> Phase2CheckResult:
    """Check 10: Leverage Quantum & Trend (Net Debt / EBITDA, Debt / Equity, Net-cash auto-PASS)."""
    if not data.financials:
        return Phase2CheckResult(
            check_id="check10_leverage_quantum",
            q_number="Q22, Q20",
            title="Leverage Quantum & Trend",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="Missing balance sheet / debt history.",
            source="Balance Sheet + P&L",
            inconclusive_reason="No debt or EBITDA data.",
        )

    latest = data.financials[-1]
    net_debt = compute_net_debt(latest.gross_debt, latest.cash_and_equivalents)

    # 1. Net-cash auto-PASS: cash exceeds total debt
    if net_debt < 0:
        return Phase2CheckResult(
            check_id="check10_leverage_quantum",
            q_number="Q22, Q20",
            title="Leverage Quantum & Trend",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.PASS,
            raw_metric_value=0.0,
            threshold_applied=f"Net Debt/EBITDA <= {thresholds.net_debt_ebitda_pass_ceiling:.1f}x",
            finding=f"PASS (Net-Cash): Company carries net cash of ₹{abs(net_debt):.1f} Cr. Leverage risk displaced to Checks 14 & 15.",
            source="Balance Sheet",
            fields_used=["gross_debt", "cash_and_equivalents"],
        )

    # Negative net worth check
    if latest.total_equity <= 0:
        return Phase2CheckResult(
            check_id="check10_leverage_quantum",
            q_number="Q22, Q20",
            title="Leverage Quantum & Trend",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="Total equity (net worth) > 0",
            finding=f"FAIL: Total equity (net worth) is negative or zero (₹{latest.total_equity:.1f} Cr).",
            source="Balance Sheet",
            fields_used=["total_equity"],
        )

    net_debt_ebitda = compute_net_debt_to_ebitda(latest.gross_debt, latest.cash_and_equivalents, latest.ebitda)
    debt_equity = compute_debt_to_equity(latest.gross_debt, latest.total_equity)

    # 3-year Net Debt / EBITDA series
    history_nde = [
        compute_net_debt_to_ebitda(f.gross_debt, f.cash_and_equivalents, f.ebitda)
        for f in data.financials[-3:]
    ]

    threshold_str = f"Pass <= {thresholds.net_debt_ebitda_pass_ceiling:.1f}x, Fail > {thresholds.net_debt_ebitda_fail_floor:.1f}x"

    # Check FAIL conditions
    if net_debt_ebitda > thresholds.net_debt_ebitda_fail_floor:
        return Phase2CheckResult(
            check_id="check10_leverage_quantum",
            q_number="Q22, Q20",
            title="Leverage Quantum & Trend",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=net_debt_ebitda,
            threshold_applied=threshold_str,
            finding=f"FAIL: Net Debt / EBITDA is {net_debt_ebitda:.2f}x (> {thresholds.net_debt_ebitda_fail_floor:.1f}x sector limit).",
            source="Balance Sheet + P&L",
            fields_used=["gross_debt", "cash_and_equivalents", "ebitda"],
        )

    # Check CONCERN vs PASS
    if thresholds.net_debt_ebitda_pass_ceiling < net_debt_ebitda <= thresholds.net_debt_ebitda_fail_floor:
        initial_status = Phase2CheckStatus.CONCERN
    else:
        initial_status = Phase2CheckStatus.PASS

    # Trend modifier: debt rising consecutively for 3 years
    rising_3y = is_consecutively_increasing(history_nde, 3)
    falling_3y = is_consecutively_decreasing(history_nde, 3)
    final_status, mod_applied = apply_trend_modifier(initial_status, falling_3y, rising_3y)

    finding = f"Net Debt / EBITDA is {net_debt_ebitda:.2f}x, Debt/Equity is {debt_equity:.2f}x. {threshold_str}."
    if mod_applied:
        if final_status == Phase2CheckStatus.CONCERN:
            finding += " Downgraded to CONCERN via Trend Modifier (leverage has increased for 3 consecutive years)."
        else:
            finding += " Upgraded to PASS via Trend Modifier (deleveraging for 3 consecutive years)."

    return Phase2CheckResult(
        check_id="check10_leverage_quantum",
        q_number="Q22, Q20",
        title="Leverage Quantum & Trend",
        group=Phase2CheckGroup.LEVERAGE,
        status=final_status,
        raw_metric_value=net_debt_ebitda,
        threshold_applied=threshold_str,
        trend_modifier_applied=mod_applied,
        original_status=initial_status if mod_applied else None,
        finding=finding,
        source="Balance Sheet + P&L",
        fields_used=["gross_debt", "cash_and_equivalents", "ebitda", "total_equity"],
        what_would_clear=f"Reduce Net Debt/EBITDA below {thresholds.net_debt_ebitda_pass_ceiling:.1f}x" if final_status == Phase2CheckStatus.CONCERN else None,
    )


def check11_interest_service_adequacy(
    data: CompanyPhase2Input,
    thresholds: SectorThresholds,
) -> Phase2CheckResult:
    """Check 11: Interest-Service Adequacy (EBIT / Finance Cost, Downturn Stress Test)."""
    if not data.financials:
        return Phase2CheckResult(
            check_id="check11_interest_service",
            q_number="Q26, Q20",
            title="Interest-Service Adequacy",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="Missing financial history for interest coverage.",
            source="P&L",
            inconclusive_reason="No EBIT or Finance Cost.",
        )

    latest = data.financials[-1]
    finance_cost = latest.finance_cost if latest.finance_cost is not None else 0.0

    # Net-cash & finance cost < 1% EBIT -> NOT_APPLICABLE
    net_debt = compute_net_debt(latest.gross_debt, latest.cash_and_equivalents)
    if net_debt < 0 and (latest.ebit > 0 and finance_cost < 0.01 * latest.ebit):
        return Phase2CheckResult(
            check_id="check11_interest_service",
            q_number="Q26, Q20",
            title="Interest-Service Adequacy",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.NOT_APPLICABLE,
            finding="NOT_APPLICABLE: Company is net cash and finance cost is < 1% of EBIT.",
            source="P&L, Balance Sheet",
        )

    coverages: List[float] = [
        compute_interest_coverage(f.ebit, f.finance_cost if f.finance_cost is not None else 0.0)
        for f in data.financials[-3:]
    ]
    latest_coverage = coverages[-1]

    threshold_str = f"Pass >= {thresholds.interest_coverage_pass_floor:.1f}x, Fail < {thresholds.interest_coverage_fail_ceiling:.1f}x"

    # Fail check: latest coverage below ceiling, or fell below in any of last 3 years
    if latest_coverage < thresholds.interest_coverage_fail_ceiling or any(c < thresholds.interest_coverage_fail_ceiling for c in coverages):
        return Phase2CheckResult(
            check_id="check11_interest_service",
            q_number="Q26, Q20",
            title="Interest-Service Adequacy",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=latest_coverage,
            threshold_applied=threshold_str,
            finding=f"FAIL: Interest coverage ({latest_coverage:.2f}x) is below the {thresholds.interest_coverage_fail_ceiling:.1f}x sector floor.",
            source="P&L",
            fields_used=["ebit", "finance_cost"],
        )

    # Order-book stress test: 30% EBITDA decline
    stress_fails = False
    if data.order_book_driven:
        stressed_ebit = latest.ebit * 0.70
        stressed_cov = compute_interest_coverage(stressed_ebit, finance_cost)
        if stressed_cov < thresholds.interest_coverage_pass_floor:
            stress_fails = True

    if thresholds.interest_coverage_fail_ceiling <= latest_coverage < thresholds.interest_coverage_pass_floor or stress_fails:
        finding = f"CONCERN: Interest coverage is {latest_coverage:.2f}x. {threshold_str}."
        if stress_fails:
            finding += " Fails 30% EBITDA downturn stress test."
        return Phase2CheckResult(
            check_id="check11_interest_service",
            q_number="Q26, Q20",
            title="Interest-Service Adequacy",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.CONCERN,
            raw_metric_value=latest_coverage,
            threshold_applied=threshold_str,
            finding=finding,
            source="P&L",
            fields_used=["ebit", "finance_cost"],
            what_would_clear=f"Increase interest coverage >= {thresholds.interest_coverage_pass_floor:.1f}x",
        )

    return Phase2CheckResult(
        check_id="check11_interest_service",
        q_number="Q26, Q20",
        title="Interest-Service Adequacy",
        group=Phase2CheckGroup.LEVERAGE,
        status=Phase2CheckStatus.PASS,
        raw_metric_value=latest_coverage,
        threshold_applied=threshold_str,
        finding=f"PASS: Interest coverage is {latest_coverage:.2f}x (>= {thresholds.interest_coverage_pass_floor:.1f}x floor).",
        source="P&L",
        fields_used=["ebit", "finance_cost"],
    )


def check12_maturity_and_refinancing(
    data: CompanyPhase2Input,
    thresholds: SectorThresholds,
) -> Phase2CheckResult:
    """Check 12: Maturity & Refinancing Risk (12-month liquidity coverage & short-term debt %)."""
    latest = data.financials[-1] if data.financials else None
    gross_debt = latest.gross_debt if latest else 0.0
    if gross_debt <= 0:
        return Phase2CheckResult(
            check_id="check12_maturity_refinancing",
            q_number="Q23",
            title="Maturity & Refinancing Risk",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.NOT_APPLICABLE,
            finding="NOT_APPLICABLE: Company has zero borrowings.",
            source="Annual Report -> Borrowings Note",
        )

    d = data.debt_refinancing
    cash = latest.cash_and_equivalents if latest else 0.0
    cfo = latest.cfo if (latest and latest.cfo is not None) else 0.0
    total_available = cash + cfo + d.undrawn_committed_lines

    if d.principal_due_next_12m > total_available and d.principal_due_next_12m > 0:
        return Phase2CheckResult(
            check_id="check12_maturity_refinancing",
            q_number="Q23",
            title="Maturity & Refinancing Risk",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=d.principal_due_next_12m,
            threshold_applied="12-month debt maturities <= Cash + CFO + Undrawn Lines",
            finding=f"FAIL: Debt due in 12m (₹{d.principal_due_next_12m:.1f} Cr) exceeds available liquidity (₹{total_available:.1f} Cr). Refinancing gap.",
            source="Annual Report -> Borrowings Maturity Schedule",
            fields_used=["principal_due_next_12m", "cash_and_equivalents", "cfo"],
        )

    st_pct = (d.short_term_borrowings / gross_debt) * 100.0 if gross_debt > 0 else 0.0
    if st_pct > thresholds.max_st_debt_concern_pct:
        return Phase2CheckResult(
            check_id="check12_maturity_refinancing",
            q_number="Q23",
            title="Maturity & Refinancing Risk",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.CONCERN,
            raw_metric_value=st_pct,
            threshold_applied=f"Short-term Debt <= {thresholds.max_st_debt_concern_pct:.1f}% of Total Debt",
            finding=f"CONCERN: Short-term borrowings are {st_pct:.1f}% of total debt (> {thresholds.max_st_debt_concern_pct:.1f}% sector limit).",
            source="Annual Report -> Borrowings Note",
            fields_used=["short_term_borrowings", "gross_debt"],
            what_would_clear=f"Refinance short-term borrowings into long-term debt below {thresholds.max_st_debt_concern_pct:.1f}%.",
        )

    return Phase2CheckResult(
        check_id="check12_maturity_refinancing",
        q_number="Q23",
        title="Maturity & Refinancing Risk",
        group=Phase2CheckGroup.LEVERAGE,
        status=Phase2CheckStatus.PASS,
        finding=f"PASS: 12-month debt maturities (₹{d.principal_due_next_12m:.1f} Cr) are comfortably covered by liquidity (₹{total_available:.1f} Cr).",
        source="Annual Report -> Borrowings Note",
    )


def check13_cost_of_debt_rating_covenants(
    data: CompanyPhase2Input,
) -> Phase2CheckResult:
    """Check 13: Cost of Debt, Credit Rating & Covenants."""
    latest = data.financials[-1] if data.financials else None
    gross_debt = latest.gross_debt if latest else 0.0
    c = data.credit_covenants

    if gross_debt <= 0 and not c.credit_rating:
        return Phase2CheckResult(
            check_id="check13_cost_rating_covenants",
            q_number="Q24, Q25",
            title="Cost of Debt, Rating & Covenants",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.NOT_APPLICABLE,
            finding="NOT_APPLICABLE: No borrowings and no rated debt instruments.",
            source="Credit Rating Agency Reports, Annual Report",
        )

    # Check FAIL conditions
    # 1. Below investment grade (< BBB-) or default (D)
    rating_upper = (c.credit_rating or "").upper()
    below_ig = any(junk in rating_upper for junk in ["BB", "B", "C", "D"]) and "BBB" not in rating_upper

    if below_ig or "DEFAULT" in rating_upper:
        return Phase2CheckResult(
            check_id="check13_cost_rating_covenants",
            q_number="Q24, Q25",
            title="Cost of Debt, Rating & Covenants",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="Investment grade rating (>= BBB-)",
            finding=f"FAIL: Rating is below investment grade or in default ('{c.credit_rating}').",
            source="Rating Agency Release (CRISIL/ICRA/CARE/India Ratings)",
        )

    if c.downgrades_last_3y_notches >= 2:
        return Phase2CheckResult(
            check_id="check13_cost_rating_covenants",
            q_number="Q24, Q25",
            title="Cost of Debt, Rating & Covenants",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="Downgrades in last 3 years < 2 notches",
            finding=f"FAIL: Credit rating was downgraded by {c.downgrades_last_3y_notches} notches over the last 3 years.",
            source="Rating Agency Release",
        )

    if c.covenant_breach_disclosed:
        waiver_note = " (waiver obtained, but still a breach)" if c.covenant_waiver_obtained else ""
        return Phase2CheckResult(
            check_id="check13_cost_rating_covenants",
            q_number="Q24, Q25",
            title="Cost of Debt, Rating & Covenants",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="No financial covenant breaches",
            finding=f"FAIL: Financial covenant breach disclosed{waiver_note}.",
            source="Annual Report -> Borrowings Note",
        )

    # Check CONCERN conditions
    concerns = []
    if c.downgrades_last_3y_notches == 1:
        concerns.append("1-notch rating downgrade in last 3 years")
    if c.rating_outlook == "NEGATIVE":
        concerns.append("Rating on Negative outlook")
    if c.unrated_with_material_debt:
        concerns.append("Carries material debt but is unrated")
    if c.borrowing_cost_yoy_increase_bps and c.borrowing_cost_yoy_increase_bps > 150.0:
        concerns.append(f"Borrowing cost rose {c.borrowing_cost_yoy_increase_bps:.0f} bps YoY (>150 bps threshold)")
    if c.substantially_all_assets_pledged:
        concerns.append("Substantially all assets are pledged as security")

    if concerns:
        return Phase2CheckResult(
            check_id="check13_cost_rating_covenants",
            q_number="Q24, Q25",
            title="Cost of Debt, Rating & Covenants",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.CONCERN,
            finding=f"CONCERN: {'; '.join(concerns)}.",
            source="Rating Agency Release, Annual Report",
            what_would_clear="Stabilize rating outlook and reduce collateral encumbrance.",
        )

    return Phase2CheckResult(
        check_id="check13_cost_rating_covenants",
        q_number="Q24, Q25",
        title="Cost of Debt, Rating & Covenants",
        group=Phase2CheckGroup.LEVERAGE,
        status=Phase2CheckStatus.PASS,
        finding=f"PASS: Credit rating is '{c.credit_rating or 'Investment Grade'}' ({c.rating_outlook or 'Stable'}), no covenant breaches.",
        source="Rating Agency Release, Annual Report",
    )


def check14_loans_and_advances_given(
    data: CompanyPhase2Input,
) -> Phase2CheckResult:
    """Check 14: Loans and Advances Given to Other Companies (Capital discipline)."""
    latest = data.financials[-1] if data.financials else None
    net_worth = latest.total_equity if latest else 0.0
    l = data.loans_given

    pct_net_worth = l.pct_of_net_worth
    if pct_net_worth is None and net_worth > 0:
        pct_net_worth = (l.total_loans_advances_to_entities / net_worth) * 100.0
    pct_val = pct_net_worth or 0.0

    # Tightened limit for net-cash companies: 15% vs standard 25%
    is_net_cash = False
    if latest:
        is_net_cash = compute_net_debt(latest.gross_debt, latest.cash_and_equivalents) < 0
    fail_ceiling = 15.0 if is_net_cash else 25.0

    # FAIL checks
    if pct_val > fail_ceiling:
        net_cash_note = " (tightened to 15% for net-cash companies)" if is_net_cash else ""
        return Phase2CheckResult(
            check_id="check14_loans_given",
            q_number="Q27",
            title="Loans and Advances Given to Others",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=pct_val,
            threshold_applied=f"Loans given <= {fail_ceiling:.0f}% of net worth{net_cash_note}",
            finding=f"FAIL: Inter-corporate loans/advances are {pct_val:.1f}% of net worth (> {fail_ceiling:.0f}% limit{net_cash_note}).",
            source="Annual Report -> Loans & Advances + Related Party Notes",
            fields_used=["total_loans_advances_to_entities", "total_equity"],
        )

    if l.is_non_interest_bearing_material:
        return Phase2CheckResult(
            check_id="check14_loans_given",
            q_number="Q27",
            title="Loans and Advances Given to Others",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="Loans must be interest-bearing at arm's length",
            finding="FAIL: Material loans/advances to affiliates are non-interest-bearing (funding affiliates at shareholder expense).",
            source="Annual Report -> Related Party Notes",
        )

    if l.has_provisions_or_writeoffs:
        return Phase2CheckResult(
            check_id="check14_loans_given",
            q_number="Q27",
            title="Loans and Advances Given to Others",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="No write-offs or impairment against affiliate loans",
            finding="FAIL: Provision or write-off recognized against inter-corporate loans.",
            source="Annual Report -> Loans & Advances Note",
        )

    # CONCERN checks
    if 10.0 <= pct_val <= fail_ceiling or l.growing_faster_than_revenue:
        reasons = []
        if pct_val >= 10.0:
            reasons.append(f"exposure is {pct_val:.1f}% of net worth (10-{fail_ceiling:.0f}% zone)")
        if l.growing_faster_than_revenue:
            reasons.append("loans grew faster than revenue over 3 years")
        return Phase2CheckResult(
            check_id="check14_loans_given",
            q_number="Q27",
            title="Loans and Advances Given to Others",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.CONCERN,
            raw_metric_value=pct_val,
            threshold_applied="Loans given <= 10% of net worth",
            finding=f"CONCERN: {'; '.join(reasons)}.",
            source="Annual Report -> Related Party Notes",
            what_would_clear="Reduce inter-corporate loan exposure below 10% of net worth.",
        )

    return Phase2CheckResult(
        check_id="check14_loans_given",
        q_number="Q27",
        title="Loans and Advances Given to Others",
        group=Phase2CheckGroup.LEVERAGE,
        status=Phase2CheckStatus.PASS,
        raw_metric_value=pct_val,
        threshold_applied="Loans given <= 10% of net worth",
        finding=f"PASS: Inter-corporate loans/advances are {pct_val:.1f}% of net worth (<= 10% limit), performing at arm's length.",
        source="Annual Report -> Related Party Notes",
    )


def check15_guarantees_and_off_balance_sheet(
    data: CompanyPhase2Input,
) -> Phase2CheckResult:
    """Check 15: Guarantees & Off-Balance-Sheet Commitments."""
    latest = data.financials[-1] if data.financials else None
    net_worth = latest.total_equity if latest else 0.0
    g = data.guarantees

    if g.total_guarantees == 0 and not g.guarantees_for_non_subs_material:
        return Phase2CheckResult(
            check_id="check15_guarantees_off_bs",
            q_number="Q28",
            title="Guarantees & Off-Balance-Sheet",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.NOT_APPLICABLE,
            finding="NOT_APPLICABLE: No corporate guarantees or letters of comfort disclosed.",
            source="Annual Report -> Contingent Liability Note",
        )

    pct_net_worth = g.pct_of_net_worth
    if pct_net_worth is None and net_worth > 0:
        pct_net_worth = (g.total_guarantees / net_worth) * 100.0
    pct_val = pct_net_worth or 0.0

    # FAIL checks
    if g.guarantees_for_non_subs_material:
        return Phase2CheckResult(
            check_id="check15_guarantees_off_bs",
            q_number="Q28",
            title="Guarantees & Off-Balance-Sheet",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="No guarantees for non-subsidiary entities",
            finding="FAIL: Material corporate guarantees provided on behalf of non-subsidiaries (promoter group/third parties).",
            source="Annual Report -> Contingent Liabilities",
        )

    if pct_val > 50.0:
        return Phase2CheckResult(
            check_id="check15_guarantees_off_bs",
            q_number="Q28",
            title="Guarantees & Off-Balance-Sheet",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=pct_val,
            threshold_applied="Total guarantees <= 50% of net worth",
            finding=f"FAIL: Total corporate guarantees are {pct_val:.1f}% of net worth (> 50% ceiling).",
            source="Annual Report -> Contingent Liabilities",
        )

    if g.guarantee_invoked_or_paid:
        return Phase2CheckResult(
            check_id="check15_guarantees_off_bs",
            q_number="Q28",
            title="Guarantees & Off-Balance-Sheet",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="No invoked guarantees",
            finding="FAIL: A corporate guarantee has been invoked or payment made under one.",
            source="Annual Report -> Contingent Liabilities",
        )

    # CONCERN checks
    if 25.0 <= pct_val <= 50.0 or g.borrowed_from_group_undisclosed_terms:
        reasons = []
        if pct_val >= 25.0:
            reasons.append(f"guarantees are {pct_val:.1f}% of net worth (25-50% zone)")
        if g.borrowed_from_group_undisclosed_terms:
            reasons.append("borrowed from related parties on undisclosed terms")
        return Phase2CheckResult(
            check_id="check15_guarantees_off_bs",
            q_number="Q28",
            title="Guarantees & Off-Balance-Sheet",
            group=Phase2CheckGroup.LEVERAGE,
            status=Phase2CheckStatus.CONCERN,
            raw_metric_value=pct_val,
            threshold_applied="Guarantees <= 25% of net worth",
            finding=f"CONCERN: {'; '.join(reasons)}.",
            source="Annual Report -> Contingent Liabilities",
            what_would_clear="Reduce total guarantees below 25% of net worth.",
        )

    return Phase2CheckResult(
        check_id="check15_guarantees_off_bs",
        q_number="Q28",
        title="Guarantees & Off-Balance-Sheet",
        group=Phase2CheckGroup.LEVERAGE,
        status=Phase2CheckStatus.PASS,
        raw_metric_value=pct_val,
        threshold_applied="Guarantees <= 25% of net worth",
        finding=f"PASS: Guarantees are limited to consolidated subsidiaries and total {pct_val:.1f}% of net worth (<= 25% limit).",
        source="Annual Report -> Contingent Liabilities",
    )


def check16_working_capital_cycle(
    data: CompanyPhase2Input,
    thresholds: SectorThresholds,
) -> Phase2CheckResult:
    """Check 16: Working Capital Cycle (CCC trend, 3-yr deterioration, Critical Cap on receivable days)."""
    if not data.working_capital:
        return Phase2CheckResult(
            check_id="check16_working_capital_cycle",
            q_number="Q20",
            title="Working-Capital Cycle",
            group=Phase2CheckGroup.COLLECTION,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="No working capital days history provided.",
            source="Screener.in / Balance Sheet",
            inconclusive_reason="Missing working capital data.",
        )

    ccc_series = [compute_ccc(w.receivable_days, w.inventory_days, w.payable_days) for w in data.working_capital]
    latest_rec_days = data.working_capital[-1].receivable_days
    latest_ccc = ccc_series[-1]

    # 3-year deterioration: ccc_series[-1] - ccc_series[0]
    ccc_deterioration = 0.0
    if len(ccc_series) >= 3:
        ccc_deterioration = ccc_series[-1] - ccc_series[-3]

    threshold_str = f"Deterioration <= {thresholds.ccc_deterioration_fail_days:.0f} days, Max Rec Days Cap {thresholds.max_receivable_days_critical_cap:.0f} days"

    # FAIL: CCC deteriorated > threshold AND receivable days > critical cap
    if ccc_deterioration > thresholds.ccc_deterioration_fail_days and latest_rec_days > thresholds.max_receivable_days_critical_cap:
        return Phase2CheckResult(
            check_id="check16_working_capital_cycle",
            q_number="Q20",
            title="Working-Capital Cycle",
            group=Phase2CheckGroup.COLLECTION,
            status=Phase2CheckStatus.FAIL,
            raw_metric_value=ccc_deterioration,
            threshold_applied=threshold_str,
            finding=(
                f"FAIL: Cash conversion cycle lengthened by {ccc_deterioration:.0f} days (> {thresholds.ccc_deterioration_fail_days:.0f} day limit) "
                f"and receivable days are {latest_rec_days:.0f} days (> {thresholds.max_receivable_days_critical_cap:.0f} day critical cap)."
            ),
            source="Screener.in -> Working Capital Days",
            fields_used=["receivable_days", "inventory_days", "payable_days"],
        )

    # CONCERN checks
    rec_days_growth_3y = 0.0
    if len(data.working_capital) >= 3 and data.working_capital[-3].receivable_days > 0:
        rec_days_growth_3y = ((latest_rec_days - data.working_capital[-3].receivable_days) / data.working_capital[-3].receivable_days) * 100.0

    if ccc_deterioration > 15.0 or rec_days_growth_3y > 30.0:
        reasons = []
        if ccc_deterioration > 15.0:
            reasons.append(f"CCC deteriorated by {ccc_deterioration:.0f} days over 3 years")
        if rec_days_growth_3y > 30.0:
            reasons.append(f"receivable days expanded by {rec_days_growth_3y:.1f}% (> 30% limit)")
        return Phase2CheckResult(
            check_id="check16_working_capital_cycle",
            q_number="Q20",
            title="Working-Capital Cycle",
            group=Phase2CheckGroup.COLLECTION,
            status=Phase2CheckStatus.CONCERN,
            raw_metric_value=ccc_deterioration,
            threshold_applied=threshold_str,
            finding=f"CONCERN: {'; '.join(reasons)}.",
            source="Screener.in -> Working Capital Days",
            what_would_clear="Stabilize receivable days and bring cash conversion cycle back in line.",
        )

    return Phase2CheckResult(
        check_id="check16_working_capital_cycle",
        q_number="Q20",
        title="Working-Capital Cycle",
        group=Phase2CheckGroup.COLLECTION,
        status=Phase2CheckStatus.PASS,
        raw_metric_value=latest_ccc,
        threshold_applied="Stable or improving CCC over 3 years",
        finding=f"PASS: Cash conversion cycle is {latest_ccc:.0f} days (receivables: {latest_rec_days:.0f} days), stable/improving over 3 years.",
        source="Screener.in -> Working Capital Days",
    )


def check17_moat_corroboration(
    data: CompanyPhase2Input,
    thresholds: SectorThresholds,
) -> Phase2CheckResult:
    """
    Check 17: Moat Corroboration (Testing claimed moat against 4 quantitative proofs).
    (a) Sustained RoCE >= sector pass threshold in >=4 of last 5 years.
    (b) Gross margin stable or rising over 3 years.
    (c) Market share stable or rising over 3 years.
    (d) Realisation rising at or above input-cost inflation (pricing power).
    """
    if data.moat.claimed_moat_type == MoatType.NONE and not data.moat.moat_description:
        return Phase2CheckResult(
            check_id="check17_moat_corroboration",
            q_number="Q29",
            title="Moat Corroboration",
            group=Phase2CheckGroup.LONGEVITY,
            status=Phase2CheckStatus.CONCERN,
            finding="CONCERN: No economic moat claimed or demonstrated. Commodity/undifferentiated business profile.",
            source="Annual Report -> MD&A",
            what_would_clear="Demonstrate competitive differentiation or pricing power.",
        )

    # Evaluate (a): RoCE sustained >= pass floor in 4/5 years
    roce_list = [f.roce_pct if f.roce_pct is not None else compute_roce(f.ebit, f.total_equity, f.gross_debt, f.cash_and_equivalents) for f in data.financials]
    qualifying_roce_years = sum(1 for r in roce_list if r >= thresholds.roce_pass_floor)
    corroborator_a = (len(roce_list) >= 4 and qualifying_roce_years >= 4)
    roce_deteriorating = is_consecutively_decreasing(roce_list, 3)

    # Evaluate (b): Gross margin stable or rising over 3 years
    gm_list = [f.gross_margin_pct for f in data.financials if f.gross_margin_pct is not None]
    corroborator_b = len(gm_list) >= 3 and (gm_list[-1] >= gm_list[-3] - 1.0)
    gm_deteriorating = is_consecutively_decreasing(gm_list, 3)

    # Evaluate (c): Market share stable or rising over 3 years
    mkt_shares = list(data.competition.market_share_history.values())
    corroborator_c = len(mkt_shares) >= 3 and (mkt_shares[-1] >= mkt_shares[0] - 0.5)
    share_deteriorating = is_consecutively_decreasing(mkt_shares, 3)

    # Evaluate (d): Realisation / pricing power
    corroborator_d = data.moat.realisation_rising_vs_inflation is True

    corroborator_count = sum([corroborator_a, corroborator_b, corroborator_c, corroborator_d])
    has_hard_financial_proof = corroborator_a or corroborator_b

    # Contradicted moat: falling returns, falling margins, falling share
    if roce_deteriorating and gm_deteriorating and share_deteriorating:
        return Phase2CheckResult(
            check_id="check17_moat_corroboration",
            q_number="Q29",
            title="Moat Corroboration",
            group=Phase2CheckGroup.LONGEVITY,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="Claimed moat must not be contradicted by financials",
            finding=f"FAIL: Claimed moat ('{data.moat.claimed_moat_type.value}') is disproved — returns, gross margins, and market share are all in simultaneous decline.",
            source="P&L, Annual Report, Industry Data",
        )

    if data.moat.licence_subsidy_expiring_within_3y:
        return Phase2CheckResult(
            check_id="check17_moat_corroboration",
            q_number="Q29",
            title="Moat Corroboration",
            group=Phase2CheckGroup.LONGEVITY,
            status=Phase2CheckStatus.CONCERN,
            finding="CONCERN: Moat rests on a regulatory licence or policy subsidy with a known expiry/review within 3 years.",
            source="Annual Report -> MD&A",
            what_would_clear="Obtain formal regulatory renewal or extension.",
        )

    if corroborator_count >= 2 and has_hard_financial_proof:
        return Phase2CheckResult(
            check_id="check17_moat_corroboration",
            q_number="Q29",
            title="Moat Corroboration",
            group=Phase2CheckGroup.LONGEVITY,
            status=Phase2CheckStatus.PASS,
            finding=(
                f"PASS: Stated moat ('{data.moat.claimed_moat_type.value}') corroborated by {corroborator_count} quantitative proofs "
                f"(Hard proof: {'RoCE' if corroborator_a else 'Gross Margin'})."
            ),
            source="P&L, Annual Report MD&A",
        )

    return Phase2CheckResult(
        check_id="check17_moat_corroboration",
        q_number="Q29",
        title="Moat Corroboration",
        group=Phase2CheckGroup.LONGEVITY,
        status=Phase2CheckStatus.CONCERN,
        finding=f"CONCERN: Only {corroborator_count} of 4 moat corroborators present (requires >=2 including hard financial proof).",
        source="P&L, Annual Report MD&A",
        what_would_clear="Demonstrate multi-year return persistence or gross margin pricing resilience.",
    )


def check18_competitive_position(
    data: CompanyPhase2Input,
) -> Phase2CheckResult:
    """Check 18: Competitive Position (Market share trajectory vs peers & industry)."""
    c = data.competition
    if not c.market_share_data_available:
        return Phase2CheckResult(
            check_id="check18_competitive_position",
            q_number="Q31",
            title="Competitive Position",
            group=Phase2CheckGroup.LONGEVITY,
            status=Phase2CheckStatus.INCONCLUSIVE,
            finding="INCONCLUSIVE: No verifiable market share or peer industry data available.",
            source="Industry Reports, AR 'Industry Structure'",
            inconclusive_reason="No reliable market share data.",
            what_would_clear="Independent industry market share tracking from research or trade bodies.",
        )

    shares = list(c.market_share_history.values())
    share_declining_3y = is_consecutively_decreasing(shares, 3)

    if share_declining_3y and c.revenue_trailed_industry_3y:
        return Phase2CheckResult(
            check_id="check18_competitive_position",
            q_number="Q31",
            title="Competitive Position",
            group=Phase2CheckGroup.LONGEVITY,
            status=Phase2CheckStatus.FAIL,
            threshold_applied="Market share must not decline for 3 consecutive years while trailing industry",
            finding="FAIL: Market share has declined for 3 consecutive years and revenue growth has trailed the industry in each year.",
            source="Industry Body Filings, Annual Reports",
        )

    concerns = []
    if shares and len(shares) >= 2 and shares[-1] < shares[0]:
        concerns.append("Market share flat-to-down while industry is expanding")
    if c.largest_competitor_growing_materially_faster:
        concerns.append("Largest competitor is gaining share materially faster")
    if c.disruptive_entrant_or_substitute:
        concerns.append("Credible new entrant or substitute technology is displacing core product")

    if concerns:
        return Phase2CheckResult(
            check_id="check18_competitive_position",
            q_number="Q31",
            title="Competitive Position",
            group=Phase2CheckGroup.LONGEVITY,
            status=Phase2CheckStatus.CONCERN,
            finding=f"CONCERN: {'; '.join(concerns)}.",
            source="Annual Report 'Industry Structure', Peer filings",
            what_would_clear="Stabilize market share and outpace median peer growth.",
        )

    return Phase2CheckResult(
        check_id="check18_competitive_position",
        q_number="Q31",
        title="Competitive Position",
        group=Phase2CheckGroup.LONGEVITY,
        status=Phase2CheckStatus.PASS,
        finding="PASS: Market share is stable or expanding against primary competitors.",
        source="Industry Body Data, Peer Filings",
    )
