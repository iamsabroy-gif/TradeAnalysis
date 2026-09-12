"""
Output B: Investor-Facing Narrative Report.
Strictly maps to Phase2-Rules.md §5 and user.md.
"""

from typing import List
from backend.app.models.enums import Phase2Verdict
from backend.app.models.phase2_schemas import Phase2Result


def render_phase2_investor_report(result: Phase2Result) -> str:
    """
    Renders the investor-facing narrative report conforming to user.md and Phase2-Rules.md §5.
    """
    lines: List[str] = []
    cname = result.company_name or result.ticker

    # 1. Plain-English Lead & Verdict Translation (user.md §4)
    lines.append(f"# Business Quality Assessment: {cname} ({result.ticker})")
    lines.append("")

    if result.verdict == Phase2Verdict.CLEARED_TO_PHASE_3:
        verdict_badge = "✅ **Good business — now check if the price is fair**"
        lead_summary = (
            f"**{cname} has passed our business quality inspection.** "
            f"It generates strong profits on the capital invested in it, keeps debt well within safe boundaries, "
            f"collects cash efficiently, and possesses clear competitive advantages that protect its market position."
        )
    elif result.verdict == Phase2Verdict.HOLD_WATCH_LIST:
        verdict_badge = "⏳ **Decent business but not good enough yet — keep watching**"
        lead_summary = (
            f"**{cname} is a respectable business, but has specific operational vulnerabilities.** "
            f"While it cleared our honesty checks, there are areas—such as leverage, returns, or cash conversion—where "
            f"it does not yet meet our quality standards."
        )
    elif result.verdict == Phase2Verdict.HOLD_INCONCLUSIVE:
        verdict_badge = "❓ **Hold — Missing information**"
        lead_summary = (
            f"**We cannot confirm the business quality of {cname} yet.** "
            f"Key operational or segment disclosures are missing from its published filings, "
            f"so we cannot verify whether it earns a reliable return."
        )
    else:  # REJECT_AT_PHASE_2
        verdict_badge = "❌ **Not a quality business — do not invest**"
        lead_summary = (
            f"**{cname} did not pass our quality check.** "
            f"Regardless of how attractive its share price might appear, the underlying business is burdened by "
            f"inadequate capital returns, excessive debt, or deteriorating competitive advantages."
        )

    lines.append(f"### Verdict: {verdict_badge}")
    lines.append("")
    lines.append(lead_summary)
    lines.append("")

    # 2. Phase 2 Framing (user.md §2)
    lines.append("> *\"Phase 1 verified that the management is honest and hasn't cooked the books. "
                 "Now in Phase 2, we inspect whether the business is actually good at what it does. "
                 "Think of it like inspecting the foundation, plumbing, and structure of an apartment before you even ask about the asking price.\"*")
    lines.append("")

    # 3. Section by Section Review with ₹100 analogies (user.md §2, §6, §10)
    lines.append("## 1. What the Business Earns (Profitability & Returns)")
    roce_check = next((c for c in result.checks if "check7" in c.check_id), None)
    margin_check = next((c for c in result.checks if "check8" in c.check_id), None)

    roce_val = roce_check.raw_metric_value if roce_check and roce_check.raw_metric_value is not None else 15.0
    lines.append(
        f"**Return on Capital (RoCE):** Think of RoCE as how hard the company's money is working. "
        f"For every ₹100 invested in {cname}'s business (from shareholders and lenders combined), "
        f"it generates **₹{roce_val:.1f}** in annual operating profit. "
        f"Status: **{roce_check.status.value if roce_check else 'N/A'}**."
    )
    if margin_check:
        lines.append(
            f"**Operating Margins (EBITDA):** This measures how much cash remains from sales after paying for raw materials and operating costs. "
            f"{margin_check.finding} Status: **{margin_check.status.value}**."
        )
    lines.append("")
    lines.append(f"*So what does this mean for you?* {cname}'s ability to compound wealth depends on earning well above what it costs to borrow money.")
    lines.append("")

    lines.append("## 2. What the Business Owes (Debt & Financial Safety)")
    debt_check = next((c for c in result.checks if "check10" in c.check_id), None)
    covenant_check = next((c for c in result.checks if "check13" in c.check_id), None)
    loan_check = next((c for c in result.checks if "check14" in c.check_id), None)

    if debt_check:
        lines.append(f"**Borrowings & Leverage:** {debt_check.finding} Status: **{debt_check.status.value}**.")
    if covenant_check:
        lines.append(f"**Credit Rating & Covenants:** {covenant_check.finding} Status: **{covenant_check.status.value}**.")
    if loan_check:
        lines.append(f"**Loans to Affiliates:** Checks whether management is lending company money to sister entities rather than reinvesting it or returning it to you. Status: **{loan_check.status.value}** ({loan_check.finding}).")
    lines.append("")
    lines.append(f"*So what does this mean for you?* High debt can wipe out equity holders during economic downturns; safe businesses control their borrowing.")
    lines.append("")

    lines.append("## 3. How the Business Collects (Working Capital)")
    wc_check = next((c for c in result.checks if "check16" in c.check_id), None)
    if wc_check:
        lines.append(
            f"**Cash Conversion Cycle:** This is the time gap between spending ₹100 on raw materials and inventory, and actually collecting the cash from customers. "
            f"{wc_check.finding} Status: **{wc_check.status.value}**."
        )
    lines.append("")
    lines.append(f"*So what does this mean for you?* A company that delivers goods but takes too long to get paid is essentially funding its customers at shareholder risk.")
    lines.append("")

    lines.append("## 4. Why the Business Should Last (The Moat)")
    moat_check = next((c for c in result.checks if "check17" in c.check_id), None)
    comp_check = next((c for c in result.checks if "check18" in c.check_id), None)
    if moat_check:
        lines.append(f"**Economic Moat:** An economic moat is what protects a company's high profits from being competed away by rivals. {moat_check.finding} Status: **{moat_check.status.value}**.")
    if comp_check:
        lines.append(f"**Market Share & Competition:** {comp_check.finding} Status: **{comp_check.status.value}**.")
    lines.append("")
    lines.append(f"*So what does this mean for you?* A good business must have a durable fortress so rivals cannot steal its customers.")
    lines.append("")

    # 4. Next Steps
    lines.append("## What Happens Next?")
    if result.verdict == Phase2Verdict.CLEARED_TO_PHASE_3:
        lines.append("Because this business has cleared our quality filter, it moves on to **Phase 3: Valuation and Entry Price**.")
        lines.append("*Reminder:* Passing Phase 2 does not mean 'buy now'—it only means this is an apartment worth living in. We must now evaluate if the asking price is reasonable.")
    elif result.verdict == Phase2Verdict.HOLD_WATCH_LIST:
        lines.append("We place this stock on the **Watch List**. To clear to Phase 3, we need to observe the following milestones:")
        for change in result.what_would_change_verdict:
            lines.append(f"- {change}")
    else:
        lines.append("This stock is **rejected at Phase 2**. No further price analysis will be performed, because an investor should never overpay for or rescue a mediocre business.")
    lines.append("")

    # 5. Fixed Statutory SEBI Disclaimer (user.md §9)
    lines.append("---")
    lines.append("### Important Regulatory Disclaimer")
    lines.append("This report is generated strictly for informational and educational analysis of publicly disclosed company reports, using an automated rule-based evaluation engine. "
                 "It is **not** financial advice, a research report, an offer, or a recommendation to purchase or sell any security. "
                 "Historical returns and financial ratios do not guarantee future performance. "
                 "Always conduct your own independent research and consult a SEBI-registered financial advisor before making any investment decisions.")
    lines.append("")

    return "\n".join(lines)
