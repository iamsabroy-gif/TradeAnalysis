"""
Return Path Calculation for Phase 3 Gatekeeper (Check B / Section I, Q40).
Strictly maps to Docs/Rules/Phase3-Rules.md §2 Check B and Docs/Rules/Phase3-Algorithms.md §2 Step 3.
All thresholds are now driven by Phase3RuleConfig from the central Rule Engine.
"""

from typing import Optional

from backend.app.models.enums import ReturnProbability
from backend.app.models.phase3_schemas import (
    CompanyPhase3Input,
    ReturnPathAnalysis,
)
from backend.app.engine.rules.config import Phase3RuleConfig


def calc_return_path(
    input_data: CompanyPhase3Input,
    config: Optional[Phase3RuleConfig] = None,
) -> ReturnPathAnalysis:
    """
    Computes required EPS growth to achieve the target CAGR over the investment horizon.
    Maps result to PROBABLE, AGGRESSIVE, or MIRACULOUS based on historical 5-year EPS growth.

    All numeric thresholds are sourced from `config` (Phase3RuleConfig).
    If no config is provided, uses the active registry config.
    """
    if config is None:
        from backend.app.engine.rules.registry import get_active_rules_config
        config = get_active_rules_config().phase3

    target_cagr = input_data.target_cagr_pct
    div_yield = input_data.dividend_yield_pct
    pe_rerate = input_data.expected_pe_change_annualized_pct
    g_hist = input_data.hist_eps_growth_5y_pct

    # Formula per Phase3-Algorithms.md §2 Step 3:
    # Required Growth = Target Return - Dividend Yield - Annualized P/E Change
    required_growth = round(target_cagr - div_yield - pe_rerate, 2)

    # Probability Classification — all thresholds from config
    if pe_rerate >= config.pe_rerate_miraculous_ceiling:
        probability = ReturnProbability.MIRACULOUS
        prob_reason = (
            f"Assumes annual P/E re-rating of {pe_rerate:.1f}% per year, which is an unrealistic multiple expansion."
        )
    elif g_hist <= 0.0:
        if required_growth <= config.growth_probable_margin:
            probability = ReturnProbability.PROBABLE
            prob_reason = "Minimal growth required to meet target return."
        elif required_growth <= config.growth_probable_margin + 3.0:
            probability = ReturnProbability.AGGRESSIVE
            prob_reason = f"Company has zero or negative historical growth ({g_hist:.1f}%), requiring a turnaround."
        else:
            probability = ReturnProbability.MIRACULOUS
            prob_reason = f"Requires {required_growth:.1f}% growth from a historically declining base ({g_hist:.1f}%)."
    else:
        threshold_probable = round(g_hist + config.growth_probable_margin, 2)
        threshold_aggressive = round(config.growth_prob_multiplier * g_hist, 2)

        if required_growth <= threshold_probable:
            probability = ReturnProbability.PROBABLE
            prob_reason = (
                f"Required growth ({required_growth:.1f}%) is within historical capability "
                f"(historical 5-yr EPS CAGR: {g_hist:.1f}% + {config.growth_probable_margin:.0f}% margin)."
            )
        elif required_growth <= threshold_aggressive:
            probability = ReturnProbability.AGGRESSIVE
            prob_reason = (
                f"Required growth ({required_growth:.1f}%) exceeds historical average ({g_hist:.1f}%), "
                f"requiring {config.growth_prob_multiplier:.1f}x acceleration in operational execution."
            )
        else:
            probability = ReturnProbability.MIRACULOUS
            prob_reason = (
                f"Required growth ({required_growth:.1f}%) is over {config.growth_prob_multiplier:.1f}x historical growth ({g_hist:.1f}%), "
                f"making the {target_cagr:.0f}% CAGR hurdle improbable."
            )

    formula_str = (
        f"Required Growth ({required_growth:.1f}%) = Target Return ({target_cagr:.1f}%) "
        f"- Dividend Yield ({div_yield:.1f}%) - P/E Re-rating ({pe_rerate:.1f}%)"
    )

    if probability == ReturnProbability.PROBABLE:
        verdict_statement = f"The math is reasonable: {prob_reason}"
    elif probability == ReturnProbability.AGGRESSIVE:
        verdict_statement = f"The math is stretched: {prob_reason}"
    else:
        verdict_statement = f"The math is a fantasy: {prob_reason}"

    return ReturnPathAnalysis(
        target_cagr_pct=target_cagr,
        horizon_years=input_data.horizon_years,
        dividend_yield_pct=div_yield,
        annualized_pe_rerating_pct=pe_rerate,
        required_eps_growth_pct=required_growth,
        historical_eps_growth_pct=g_hist,
        probability=probability,
        formula_used=formula_str,
        verdict_statement=verdict_statement,
    )

