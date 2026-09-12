"""
Phase 2 Master Decision Orchestrator (The Business Quality Check).
Strictly maps to Phase2-Rules.md §0, §2, and §3.
Pure function — zero network or disk I/O.
"""

from datetime import datetime
from typing import Any, List, Optional
import uuid

from backend.app.models.enums import (
    Phase2CheckStatus,
    Phase2Sector,
    Phase2Verdict,
    Verdict as Phase1Verdict,
)
from backend.app.models.schemas import Phase1Result
from backend.app.models.phase2_schemas import (
    CompanyPhase2Input,
    Phase2CheckResult,
    Phase2Result,
)
from .checks import (
    check7_return_on_capital,
    check8_margin_trajectory,
    check9_segment_economics,
    check10_leverage_quantum_and_trend,
    check11_interest_service_adequacy,
    check12_maturity_and_refinancing,
    check13_cost_of_debt_rating_covenants,
    check14_loans_and_advances_given,
    check15_guarantees_and_off_balance_sheet,
    check16_working_capital_cycle,
    check17_moat_corroboration,
    check18_competitive_position,
)
from .matrix import get_sector_thresholds


class Phase2GatekeeperError(ValueError):
    """Raised when a company fails the Phase 1 entry condition."""
    pass


def run_phase2(
    input_data: CompanyPhase2Input,
    phase1_result: Optional[Phase1Result] = None,
    matrix_config: Optional[Any] = None,
) -> Phase2Result:
    """
    Evaluates all twelve Phase 2 quality checks against CompanyPhase2Input.
    Enforces Phase 1 clearance prerequisite and the strict decision hierarchy.
    Uses dynamic matrix_config if provided, otherwise active configuration.
    """
    # 0. Entry condition verification (Phase2-Rules.md §0)
    phase1_cleared = True
    phase1_id = None
    if phase1_result is not None:
        phase1_id = phase1_result.result_id
        if phase1_result.verdict != Phase1Verdict.CLEARED_TO_PHASE_2:
            phase1_cleared = False
            raise Phase2GatekeeperError(
                f"Entry condition failed: Company has Phase 1 verdict '{phase1_result.verdict.value}'. "
                f"Only companies with 'CLEARED TO PHASE 2' may enter Phase 2."
            )

    # 1. Resolve Industry Boundary Matrix sector thresholds
    resolved_sector, thresholds, sector_note = get_sector_thresholds(
        sector=input_data.sector,
        regulated_contract_revenue_pct=input_data.regulated_contract_revenue_pct,
        matrix_config=matrix_config,
    )

    # 2. Evaluate ALL twelve checks — never short-circuit (Phase2-Rules.md §0.3)
    results: List[Phase2CheckResult] = [
        check7_return_on_capital(input_data, thresholds),
        check8_margin_trajectory(input_data),
        check9_segment_economics(input_data),
        check10_leverage_quantum_and_trend(input_data, thresholds),
        check11_interest_service_adequacy(input_data, thresholds),
        check12_maturity_and_refinancing(input_data, thresholds),
        check13_cost_of_debt_rating_covenants(input_data),
        check14_loans_and_advances_given(input_data),
        check15_guarantees_and_off_balance_sheet(input_data),
        check16_working_capital_cycle(input_data, thresholds),
        check17_moat_corroboration(input_data, thresholds),
        check18_competitive_position(input_data),
    ]

    # 3. Categorize statuses
    fails = [r for r in results if r.status == Phase2CheckStatus.FAIL]
    concerns = [r for r in results if r.status == Phase2CheckStatus.CONCERN]
    inconclusives = [r for r in results if r.status == Phase2CheckStatus.INCONCLUSIVE]
    passes = [r for r in results if r.status == Phase2CheckStatus.PASS]

    # 4. Decision Rule Hierarchy (Phase2-Rules.md §3)
    if len(fails) > 0:
        verdict = Phase2Verdict.REJECT_AT_PHASE_2
        verdict_summary = f"REJECT: Failed {len(fails)} check(s) ({', '.join(f.title for f in fails)}) — structurally disqualifying business quality defect."
    elif len(concerns) >= 3:
        verdict = Phase2Verdict.REJECT_AT_PHASE_2
        verdict_summary = f"REJECT: Accumulated {len(concerns)} concerns — structurally mediocre business profile across multiple operational dimensions."
    elif len(inconclusives) >= 1:
        verdict = Phase2Verdict.HOLD_INCONCLUSIVE
        verdict_summary = f"HOLD — INCONCLUSIVE: {len(inconclusives)} required quality check(s) cannot be verified from available data."
    elif len(concerns) >= 1:
        verdict = Phase2Verdict.HOLD_WATCH_LIST
        verdict_summary = f"HOLD — WATCH LIST: Decent business with {len(concerns)} specific operational concern(s) ({', '.join(c.title for c in concerns)})."
    else:
        verdict = Phase2Verdict.CLEARED_TO_PHASE_3
        verdict_summary = "CLEARED TO PHASE 3: High quality business clearing all return, leverage, collection, and moat benchmarks."

    # 5. Build structured analytical narratives
    why_the_verdict = []
    if fails:
        for f in fails:
            why_the_verdict.append(f"FAIL on {f.title}: {f.finding}")
    if concerns:
        for c in concerns:
            why_the_verdict.append(f"CONCERN on {c.title}: {c.finding}")
    if not fails and not concerns and not inconclusives:
        why_the_verdict.append("Cleared all 12 quantitative and qualitative benchmarks against sector standards.")

    what_data_does_not_conclude = []
    for inc in inconclusives:
        what_data_does_not_conclude.append(f"{inc.title}: {inc.finding} (Missing: {inc.inconclusive_reason})")

    what_would_change_verdict = []
    if verdict in {Phase2Verdict.HOLD_WATCH_LIST, Phase2Verdict.REJECT_AT_PHASE_2}:
        for c in concerns:
            if c.what_would_clear:
                what_would_change_verdict.append(f"{c.title}: {c.what_would_clear}")
        for f in fails:
            what_would_change_verdict.append(f"{f.title}: Resolve disqualifying metric breach to conform with sector thresholds.")
    elif verdict == Phase2Verdict.HOLD_INCONCLUSIVE:
        for inc in inconclusives:
            if inc.what_would_clear:
                what_would_change_verdict.append(f"{inc.title}: {inc.what_would_clear}")

    # Build PESTLE summary dict
    pestle_dict = {}
    p = input_data.pestle
    if p.political: pestle_dict["Political"] = p.political
    if p.economic: pestle_dict["Economic"] = p.economic
    if p.social: pestle_dict["Social"] = p.social
    if p.technological: pestle_dict["Technological"] = p.technological
    if p.legal: pestle_dict["Legal"] = p.legal
    if p.environmental: pestle_dict["Environmental"] = p.environmental

    return Phase2Result(
        result_id=str(uuid.uuid4()),
        ticker=input_data.ticker,
        company_name=input_data.company_name,
        as_of_date=input_data.as_of_date,
        data_basis=input_data.data_basis,
        sector=resolved_sector,
        phase1_result_id=phase1_id,
        phase1_cleared=phase1_cleared,
        checks=results,
        verdict=verdict,
        verdict_summary=verdict_summary,
        concerns_count=len(concerns),
        inconclusive_count=len(inconclusives),
        fails_count=len(fails),
        passes_count=len(passes),
        why_the_verdict=why_the_verdict,
        what_data_does_not_conclude=what_data_does_not_conclude,
        what_would_change_verdict=what_would_change_verdict,
        pestle_summary=pestle_dict,
        generated_at=datetime.utcnow().isoformat() + "Z",
    )
