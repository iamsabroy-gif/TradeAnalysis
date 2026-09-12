"""
Analyst Working Table Renderer for Phase 3 Gatekeeper.
Strictly maps to Docs/Rules/Phase3-Rules.md §4 (Internal Working Table).
"""

from backend.app.models.phase3_schemas import Phase3Result


def render_phase3_analyst_table(result: Phase3Result) -> str:
    """
    Renders Phase 3 execution result into the standardized Markdown Internal Working Table.
    """
    val = result.valuation
    ret = result.return_path
    story = result.story_scan

    lines = [
        f"# Phase 3 — {result.company_name} ({result.ticker})",
        f"**Evaluation ID:** `{result.result_id}`  |  **Generated:** {result.created_at}",
        "",
        f"## FINAL VERDICT: **{result.verdict.value}**",
        "",
        "### 1. The Numbers (Valuation & Returns)",
        "| Metric | Current | Peer Avg | 5-Yr Avg | Status |",
        "| :-- | :-- | :-- | :-- | :-- |",
        f"| P/E | {val.pe_comparison.current:.1f}x | {val.pe_comparison.peer_avg:.1f}x | {val.pe_comparison.hist_5y_avg:.1f}x | **{val.pe_comparison.status.value}** |",
    ]

    if val.ev_ebitda_comparison is not None:
        ev = val.ev_ebitda_comparison
        lines.append(
            f"| EV/EBITDA | {ev.current:.1f}x | {ev.peer_avg:.1f}x | {ev.hist_5y_avg:.1f}x | **{ev.status.value}** |"
        )

    lines.extend([
        "",
        "**The 20% Return Path:**",
        f"- Target Return: {ret.target_cagr_pct:.1f}% CAGR over {ret.horizon_years} years",
        f"- Required Earnings Growth: **{ret.required_eps_growth_pct:.1f}%** (Historical: {ret.historical_eps_growth_pct:.1f}%) → **{ret.probability.value}**",
        f"- Dividend Yield Contribution: {ret.dividend_yield_pct:.1f}%",
        f"- Annualized P/E Re-rating: {ret.annualized_pe_rerating_pct:.1f}%",
        f"- Verdict: *{ret.verdict_statement}*",
        "",
        "### 2. The Story (Narrative Confirmation)",
        "| Section | Finding / Observation | Verdict |",
        "| :-- | :-- | :-- |",
    ])

    for item in story.contradictions:
        status_badge = "CONTRADICTION" if item.triggered else "CONFIRMED"
        lines.append(f"| {item.title} ({item.section_source}) | {item.detail} | **{status_badge}** |")

    lines.extend([
        "",
        "## Why the Verdict",
        f"- {result.why_verdict}",
        f"- Overall Story Summary: {story.summary}",
    ])

    return "\n".join(lines)
