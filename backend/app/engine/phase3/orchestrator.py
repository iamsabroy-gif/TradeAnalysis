"""
Phase 3 Master Decision Orchestrator (Valuation & Story Confirmation Engine).
Strictly maps to Docs/Rules/Phase3-Rules.md §0, §2, §3 and Docs/Rules/Phase3-Algorithms.md §1, §3.
All thresholds and the verdict decision matrix are now driven by the central Rule Engine.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid

from backend.app.models.enums import (
    Phase2Verdict,
    Phase3Verdict,
    ReturnProbability,
    ValuationStatus,
)
from backend.app.models.phase2_schemas import Phase2Result
from backend.app.models.phase3_schemas import (
    CompanyPhase3Input,
    Phase3Result,
    ReturnPathAnalysis,
    StoryScanAnalysis,
    ValuationAnalysis,
)
from backend.app.engine.rules.config import (
    Phase3DecisionMatrix,
    Phase3RuleConfig,
)
from .return_path import calc_return_path
from .story_scan import scan_contradictions
from .valuation import calc_valuation


class Phase3GatekeeperError(ValueError):
    """Raised when a company fails the Phase 2 entry condition prerequisite."""
    pass


# ── Verdict prose templates keyed by Phase3Verdict value ──
_VERDICT_PROSE = {
    Phase3Verdict.AVOID_STORY_CONTRADICTION.value: (
        lambda v, rp, ss: (
            f"Fatal Story Contradiction: Even if valuation appears acceptable, "
            f"the management narrative fails reality verification: "
            f"{'; '.join(c.detail for c in ss.contradictions if c.triggered)}",
            "The story doesn't match the actions. We checked if the management's promises "
            "match their deeds and discovered a major red flag. When words and numbers conflict, "
            "we always trust the numbers and walk away.",
        )
    ),
    Phase3Verdict.AVOID_OVERVALUED.value: (
        lambda v, rp, ss: (
            f"Quality Trap / Overvalued: To make a {rp.target_cagr_pct:.0f}% annual return from current price, "
            f"the company must achieve {rp.required_eps_growth_pct:.1f}% EPS growth "
            f"(vs {rp.historical_eps_growth_pct:.1f}% historical), which is mathematically improbable.",
            "The business is great, but the price tag is a fantasy. Paying today's price means "
            "the company would have to grow at an impossible rate for you to make a solid return. "
            "It's like buying a lovely apartment at triple its fair neighborhood value.",
        )
    ),
    Phase3Verdict.BUY_HIGH_CONVICTION.value: (
        lambda v, rp, ss: (
            f"High Conviction Buy: Valuation is fair ({v.explanation}), the {rp.target_cagr_pct:.0f}% return path "
            f"is probable ({rp.required_eps_growth_pct:.1f}% vs {rp.historical_eps_growth_pct:.1f}% historical), "
            f"and all narrative checks confirm operational reality.",
            "The numbers and the story align. You are buying a proven, quality company at an honest "
            f"price with a high probability of delivering your target {rp.target_cagr_pct:.0f}% annual return.",
        )
    ),
    Phase3Verdict.BUY_SPECULATIVE.value: (
        lambda v, rp, ss: (
            f"Speculative Buy: High business quality and confirmed story, but trading at a premium multiple "
            f"({v.pe_comparison.current:.1f}x P/E). Delivering {rp.target_cagr_pct:.0f}% CAGR requires aggressive sustained execution.",
            "A fine business with a verified story, but you are paying top dollar. For you to profit, "
            "management must execute without making a single mistake.",
        )
    ),
    Phase3Verdict.HOLD_FAIR_VALUE.value: (
        lambda v, rp, ss: (
            f"Hold / Fair Value: The company is sound, but currently priced at full value. "
            f"Required EPS growth of {rp.required_eps_growth_pct:.1f}% leaves no margin of safety.",
            "The company is priced exactly at what it is worth. There is no bargain here, "
            "and no cushion if something goes wrong. We wait for a pullback.",
        )
    ),
}


def synthesize_phase3_verdict(
    valuation: ValuationAnalysis,
    return_path: ReturnPathAnalysis,
    story_scan: StoryScanAnalysis,
    decision_matrix: Optional[Phase3DecisionMatrix] = None,
) -> tuple[Phase3Verdict, str, str]:
    """
    Applies the priority-based decision matrix per Phase3-Algorithms.md §3.
    Uses the configurable decision matrix from the Rule Engine.
    Returns: (verdict, why_verdict_technical, layman_explanation)
    """
    if decision_matrix is None:
        from backend.app.engine.rules.registry import get_active_rules_config
        decision_matrix = get_active_rules_config().phase3_decision_matrix

    has_fatal = story_scan.has_fatal_contradiction
    rp_value = return_path.probability.value  # e.g. "PROBABLE"
    val_value = valuation.overall_status.value  # e.g. "FAIR"

    # Evaluate matrix entries in priority order
    sorted_entries = sorted(decision_matrix.entries, key=lambda e: e.priority)
    matched_verdict_str = None

    for entry in sorted_entries:
        if entry.story_contradiction != has_fatal:
            continue
        if rp_value not in entry.return_path:
            continue
        if val_value not in entry.valuation:
            continue
        matched_verdict_str = entry.verdict
        break

    # Default fallback if no matrix entry matches
    if matched_verdict_str is None:
        matched_verdict_str = Phase3Verdict.HOLD_FAIR_VALUE.value

    # Resolve the verdict enum
    verdict = Phase3Verdict(matched_verdict_str)

    # Generate prose from templates
    prose_fn = _VERDICT_PROSE.get(verdict.value)
    if prose_fn:
        why, layman = prose_fn(valuation, return_path, story_scan)
    else:
        why = f"Verdict: {verdict.value}"
        layman = "Assessment complete. Please review the detailed analysis."

    return verdict, why, layman


def run_phase3(
    input_data: CompanyPhase3Input,
    phase2_result: Optional[Phase2Result] = None,
    config: Optional[Phase3RuleConfig] = None,
    decision_matrix: Optional[Phase3DecisionMatrix] = None,
) -> Phase3Result:
    """
    Executes the Phase 3 Gatekeeper pipeline:
    1. Enforces Phase 2 entry prerequisite if phase2_result is provided.
    2. Runs Valuation Analysis (Check A).
    3. Runs Return Path Math (Check B).
    4. Runs Story Contradiction Scan (Check C).
    5. Applies Decision Matrix to reach final verdict and layman prose.

    All thresholds are sourced from the Rule Engine config.
    If no config/matrix is provided, uses the active registry config.
    """
    if config is None or decision_matrix is None:
        from backend.app.engine.rules.registry import get_active_rules_config
        active_cfg = get_active_rules_config()
        if config is None:
            config = active_cfg.phase3
        if decision_matrix is None:
            decision_matrix = active_cfg.phase3_decision_matrix

    # 0. Entry condition enforcement (Phase3-Rules.md §0)
    phase2_id = None
    if phase2_result is not None:
        phase2_id = phase2_result.result_id
        if phase2_result.verdict != Phase2Verdict.CLEARED_TO_PHASE_3:
            raise Phase3GatekeeperError(
                f"Entry condition failed: Company has Phase 2 verdict '{phase2_result.verdict.value}'. "
                f"Only stocks with 'CLEARED TO PHASE 3' may enter Phase 3."
            )

    # 1. Valuation Analysis — config-driven
    valuation = calc_valuation(input_data, config=config)

    # 2. Return Path Calculation — config-driven
    return_path = calc_return_path(input_data, config=config)

    # 3. Story Contradiction Scan — config-driven
    story_scan = scan_contradictions(input_data, config=config)

    # 4. Final Decision Synthesis — matrix-driven
    verdict, why, layman = synthesize_phase3_verdict(
        valuation, return_path, story_scan, decision_matrix=decision_matrix
    )

    result_id = f"p3-{input_data.ticker.upper()}-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()

    return Phase3Result(
        result_id=result_id,
        ticker=input_data.ticker.upper(),
        company_name=input_data.company_name or input_data.ticker.upper(),
        phase2_result_id=phase2_id,
        verdict=verdict,
        valuation=valuation,
        return_path=return_path,
        story_scan=story_scan,
        why_verdict=why,
        layman_explanation=layman,
        created_at=created_at,
    )

