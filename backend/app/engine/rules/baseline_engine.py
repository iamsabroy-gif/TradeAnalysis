"""
Baseline Engine: Unified Full-Spectrum Governance & Quality Processor.
Strictly implements Docs/Rules/baseline-engine-implementation.md §2 (Engine Execution Logic).

Linear execution sequence:
1. Phase 1: The Red-Flag Filter (Binary Gate, Checks 1–6)
   - If any check is FAIL -> REJECT immediately. Stop execution.
   - Else -> CLEARED TO PHASE 2.
2. Phase 2: The Quality Screen (Nuanced Grading, Checks 7–18)
   - Resolves Sector Profile from company tags/keyword mapping.
   - Evaluates Checks 7–18 against sector boundaries and calibrated rules.
   - Applies 3-year trend modifiers.
   - Verdict Synthesis:
     * Any FAIL -> REJECT AT PHASE 2
     * >= 3 CONCERNS -> REJECT AT PHASE 2
     * >= 1 INCONCLUSIVE -> HOLD — INCONCLUSIVE
     * >= 1 CONCERN -> HOLD — WATCH LIST
     * Else -> CLEARED TO PHASE 3
3. Report Generation: Produces technical markdown table and user.md narrative report.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from backend.app.models.enums import (
    CheckStatus as Phase1CheckStatus,
    Phase2CheckStatus,
    Phase2Sector,
    Phase2Verdict,
    Verdict as Phase1Verdict,
)
from backend.app.models.schemas import CompanyInput, Phase1Result
from backend.app.models.phase2_schemas import CompanyPhase2Input, Phase2Result
from backend.app.engine.phase2.orchestrator import Phase2GatekeeperError
from backend.app.engine.rules.config import (
    RulesConfiguration,
    create_default_rules_configuration,
)
from backend.app.engine.rules.registry import (
    get_active_rules_config,
    resolve_sector_from_keyword,
)


class BaselineEvaluationResult(BaseModel):
    """
    Unified end-to-end evaluation result across Phase 1 and Phase 2.
    """
    ticker: str
    company_name: Optional[str] = None
    resolved_sector: Optional[str] = None
    sector_resolution_reason: Optional[str] = None
    final_verdict: str
    final_verdict_summary: str
    phase1_cleared: bool
    phase1_result: Optional[Phase1Result] = None
    phase2_result: Optional[Phase2Result] = None
    checks_evaluated_count: int = 0
    executed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    analyst_table_markdown: str = ""
    investor_report_markdown: str = ""


class BaselineEngine:
    """
    Core execution engine implementing 'Logic in Excel, Execution in Code'.
    """

    def __init__(self, config: Optional[RulesConfiguration] = None):
        self.config = config or get_active_rules_config()

    def execute(
        self,
        phase1_input: CompanyInput,
        phase2_input: Optional[CompanyPhase2Input] = None,
        custom_config: Optional[RulesConfiguration] = None,
    ) -> BaselineEvaluationResult:
        """
        Executes the linear baseline analysis sequence for a stock:
        Phase 1 (Binary Gate) -> If Cleared -> Phase 2 (Quality Screen) -> Verdict Synthesis.
        """
        from backend.app.engine.orchestrator import run_phase1
        from backend.app.engine.phase2.orchestrator import run_phase2
        from backend.app.rendering.phase2 import (
            render_phase2_analyst_table,
            render_phase2_investor_report,
        )
        from backend.app.rendering.investor_prose import render_investor_report

        P1_TITLES = {
            1: "Auditor & Regulatory Integrity",
            2: "Promoter Share Pledge",
            3: "Related-Party Transactions & Leakage",
            4: "Contingent Liabilities & Capital Risk",
            5: "Cash Conversion & Earnings Quality",
            6: "Executive Stability & Account Restatements",
        }

        def _p1_analyst_md(p1: Phase1Result) -> str:
            lines = [
                "| Check # | Check Name | Status | Finding |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for c in p1.checks:
                c_title = P1_TITLES.get(c.check_id, f"Check {c.check_id}")
                lines.append(f"| Check {c.check_id} | {c_title} | **{c.status.value}** | {c.finding} |")
            return "\n".join(lines)

        def _p1_investor_md(p1: Phase1Result) -> str:
            inv = render_investor_report(p1)
            headline = inv.get("headline", "")
            lead_story = inv.get("lead_story", "")
            return f"### Phase 1 Gatekeeper: {inv.get('badge_label', p1.verdict.value)}\n\n**{headline}**\n\n{lead_story}"

        cfg = custom_config or self.config or get_active_rules_config()
        ticker = (phase1_input.ticker or (phase2_input.ticker if phase2_input else "") or "UNKNOWN").upper()

        # Step 1: Sector Resolution
        resolved_sector_name = None
        resolution_reason = None
        sector_keyword = (
            (phase2_input.company_name if phase2_input and phase2_input.company_name else None)
            or getattr(phase1_input, "industry_sector", None)
            or ticker
        )
        if sector_keyword:
            matched_sec, reason = resolve_sector_from_keyword(sector_keyword, cfg)
            resolved_sector_name = matched_sec.value
            resolution_reason = reason

        # Step 2: Phase 1 — Red-Flag Filter (Binary Gate)
        p1_res = run_phase1(phase1_input, rule_config=cfg.phase1)
        checks_evaluated = len(p1_res.checks)
        p1_inv_data = render_investor_report(p1_res)

        # Binary Gate Decision: Stop immediately if any Phase 1 check fails
        if p1_res.verdict == Phase1Verdict.REJECT:
            p1_analyst = _p1_analyst_md(p1_res)
            p1_investor = _p1_investor_md(p1_res)
            return BaselineEvaluationResult(
                ticker=ticker,
                company_name=ticker,
                resolved_sector=resolved_sector_name,
                sector_resolution_reason=resolution_reason,
                final_verdict="REJECT (FAILED PHASE 1 GATE)",
                final_verdict_summary=p1_inv_data.get("headline", "Failed Phase 1 Forensic Gate"),
                phase1_cleared=False,
                phase1_result=p1_res,
                phase2_result=None,
                checks_evaluated_count=checks_evaluated,
                analyst_table_markdown=p1_analyst,
                investor_report_markdown=p1_investor,
            )

        if p1_res.verdict == Phase1Verdict.HOLD_INCONCLUSIVE:
            p1_analyst = _p1_analyst_md(p1_res)
            p1_investor = _p1_investor_md(p1_res)
            return BaselineEvaluationResult(
                ticker=ticker,
                company_name=ticker,
                resolved_sector=resolved_sector_name,
                sector_resolution_reason=resolution_reason,
                final_verdict="HOLD — INCONCLUSIVE (PHASE 1)",
                final_verdict_summary=p1_inv_data.get("headline", "Phase 1 Inconclusive"),
                phase1_cleared=False,
                phase1_result=p1_res,
                phase2_result=None,
                checks_evaluated_count=checks_evaluated,
                analyst_table_markdown=p1_analyst,
            )

        # Step 3: Phase 1 Cleared -> Enter Phase 2 Quality Screen
        if phase2_input is None:
            # Phase 1 is cleared, but no Phase 2 financial series provided
            p1_analyst = _p1_analyst_md(p1_res)
            p1_investor = _p1_investor_md(p1_res)
            return BaselineEvaluationResult(
                ticker=ticker,
                company_name=ticker,
                resolved_sector=resolved_sector_name,
                sector_resolution_reason=resolution_reason,
                final_verdict="CLEARED TO PHASE 2",
                final_verdict_summary="Phase 1 forensic safety gate passed. Awaiting Phase 2 financial series.",
                phase1_cleared=True,
                phase1_result=p1_res,
                phase2_result=None,
                checks_evaluated_count=checks_evaluated,
                analyst_table_markdown=p1_analyst,
                investor_report_markdown=p1_investor,
            )

        # Auto-assign resolved sector if not explicitly overridden on input
        if resolved_sector_name and phase2_input.sector == Phase2Sector.STANDARD and sector_keyword:
            for s in Phase2Sector:
                if s.value == resolved_sector_name:
                    phase2_input.sector = s
                    break

        p2_res = run_phase2(
            input_data=phase2_input,
            phase1_result=p1_res,
            matrix_config=cfg.phase2_matrix,
        )
        checks_evaluated += len(p2_res.checks)

        # Combine reports
        combined_analyst = (
            f"## Phase 1 Forensic Safety Gate Table\n\n"
            f"{_p1_analyst_md(p1_res)}\n\n"
            f"---\n\n"
            f"## Phase 2 Business Quality & Moat Table\n\n"
            f"{render_phase2_analyst_table(p2_res)}"
        )
        combined_investor = (
            f"# Full-Spectrum Investment Memorandum: {ticker}\n\n"
            f"**Overall Verdict:** `{p2_res.verdict.value}`\n\n"
            f"**Executive Verdict Summary:** {p2_res.verdict_summary}\n\n"
            f"---\n\n"
            f"### Phase 1: Forensic Integrity\n\n"
            f"{_p1_investor_md(p1_res)}\n\n"
            f"---\n\n"
            f"### Phase 2: Quality, Moat & Capital Allocation\n\n"
            f"{render_phase2_investor_report(p2_res)}"
        )

        return BaselineEvaluationResult(
            ticker=ticker,
            company_name=phase2_input.company_name or ticker,
            resolved_sector=p2_res.sector.value,
            sector_resolution_reason=resolution_reason or f"Sector profile: {p2_res.sector.value}",
            final_verdict=p2_res.verdict.value,
            final_verdict_summary=p2_res.verdict_summary,
            phase1_cleared=True,
            phase1_result=p1_res,
            phase2_result=p2_res,
            checks_evaluated_count=checks_evaluated,
            analyst_table_markdown=combined_analyst,
            investor_report_markdown=combined_investor,
        )
