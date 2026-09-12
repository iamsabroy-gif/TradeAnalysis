"""
Output A: Internal Working Table (Analyst View — Precise, Technical).
Strictly maps to Phase2-Rules.md §4.
"""

from typing import List
from backend.app.models.enums import Phase2CheckGroup
from backend.app.models.phase2_schemas import Phase2CheckResult, Phase2Result


def render_phase2_analyst_table(result: Phase2Result) -> str:
    """
    Renders the exact markdown working table defined in Phase2-Rules.md §4.
    """
    lines: List[str] = []
    cname = result.company_name or result.ticker
    lines.append(f"# Phase 2 — {cname} ({result.ticker})")
    lines.append(f"**As of:** {result.as_of_date}   **Basis:** {result.data_basis.value}")
    lines.append(f"**Sector treatment:** {result.sector.value}")
    if result.phase1_result_id:
        lines.append(f"**Phase 1:** CLEARED TO PHASE 2 (result_id: {result.phase1_result_id})")
    lines.append("")

    lines.append(f"## VERDICT: {result.verdict.value}")
    lines.append(f"*{result.verdict_summary}*")
    lines.append(f"**Concerns:** {result.concerns_count}   **Inconclusive:** {result.inconclusive_count}   **Fails:** {result.fails_count}")
    lines.append("")

    def _render_group(group_title: str, group_enum: Phase2CheckGroup):
        lines.append(f"### {group_title}")
        lines.append("| # | Check | Finding (with number vs threshold) | Source | Status |")
        lines.append("| :-: | :-- | :-- | :-: | :-: |")
        group_checks = [c for c in result.checks if c.group == group_enum]
        for c in group_checks:
            num = c.check_id.replace("check", "").split("_")[0]
            thresh = f" [{c.threshold_applied}]" if c.threshold_applied else ""
            lines.append(f"| {num} | {c.title} | {c.finding}{thresh} | {c.source} | **{c.status.value}** |")
        lines.append("")

    _render_group("Group A — What it earns", Phase2CheckGroup.EARNINGS)
    _render_group("Group B — What it owes", Phase2CheckGroup.LEVERAGE)
    _render_group("Group C — How it collects", Phase2CheckGroup.COLLECTION)
    _render_group("Group D — Why it lasts", Phase2CheckGroup.LONGEVITY)

    # PESTLE context (Q30)
    lines.append("## PESTLE context (no verdict — Q30)")
    if result.pestle_summary:
        for factor, text in result.pestle_summary.items():
            lines.append(f"- **{factor}**: {text}")
    else:
        lines.append("- *No macro or industry disruptions noted in annual report disclosure.*")
    lines.append("")

    # Why the verdict
    lines.append("## Why the verdict")
    if result.why_the_verdict:
        for reason in result.why_the_verdict:
            lines.append(f"- {reason}")
    else:
        lines.append("- Cleared all required checks.")
    lines.append("")

    # What the data does NOT let us conclude
    lines.append("## What the data does NOT let us conclude")
    if result.what_data_does_not_conclude:
        for gap in result.what_data_does_not_conclude:
            lines.append(f"- {gap}")
    else:
        lines.append("- All required technical disclosures were present and verified.")
    lines.append("")

    # What would change this verdict
    lines.append("## What would change this verdict")
    if result.what_would_change_verdict:
        for change in result.what_would_change_verdict:
            lines.append(f"- {change}")
    else:
        lines.append("- Sustained performance across current metrics maintains the cleared status.")
    lines.append("")

    return "\n".join(lines)
