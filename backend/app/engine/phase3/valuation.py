"""
Valuation Gap Analysis for Phase 3 Gatekeeper (Check A / Section E, Q21).
Strictly maps to Docs/Rules/Phase3-Rules.md §2 Check A and Docs/Rules/Phase3-Algorithms.md §2 Step 2.
All thresholds are now driven by Phase3RuleConfig from the central Rule Engine.
"""

from typing import Optional

from backend.app.models.enums import ValuationStatus
from backend.app.models.phase3_schemas import (
    CompanyPhase3Input,
    ValuationAnalysis,
    ValuationMetricItem,
)
from backend.app.engine.rules.config import Phase3RuleConfig


def _classify_metric(
    current: float,
    hist_avg: float,
    peer_avg: float,
    variance_pct: float,
) -> ValuationStatus:
    """
    Classifies a valuation metric as FAIR, EXPENSIVE, or CONCERN using
    a configurable variance tolerance above the benchmark.
    """
    hist_ceiling = hist_avg * (1.0 + variance_pct / 100.0)
    peer_ceiling = peer_avg * (1.0 + variance_pct / 100.0)

    below_hist = current <= hist_ceiling
    below_peer = current <= peer_ceiling

    if below_hist and below_peer:
        return ValuationStatus.FAIR
    elif not below_hist and not below_peer:
        return ValuationStatus.EXPENSIVE
    else:
        return ValuationStatus.CONCERN


def calc_valuation(
    input_data: CompanyPhase3Input,
    config: Optional[Phase3RuleConfig] = None,
) -> ValuationAnalysis:
    """
    Compares Current P/E and EV/EBITDA against 5-year historical average and peer average.
    Assigns FAIR, EXPENSIVE, or CONCERN status using configurable variance tolerance.

    All numeric thresholds are sourced from `config` (Phase3RuleConfig).
    If no config is provided, uses the active registry config.
    """
    if config is None:
        from backend.app.engine.rules.registry import get_active_rules_config
        config = get_active_rules_config().phase3

    variance = config.valuation_fair_variance_pct

    pe = input_data.current_pe
    pe_hist = input_data.hist_5y_avg_pe
    pe_peer = input_data.peer_avg_pe

    # 1. Primary evaluation: P/E Ratio
    pe_status = _classify_metric(pe, pe_hist, pe_peer, variance)

    if pe_status == ValuationStatus.FAIR:
        pe_notes = (
            f"Trading within {variance:.0f}% tolerance of both historical multiple "
            f"({pe:.1f}x vs 5-Yr Avg {pe_hist:.1f}x) and peer group average ({pe_peer:.1f}x)."
        )
    elif pe_status == ValuationStatus.EXPENSIVE:
        pe_notes = (
            f"Trading at a premium above both historical average ({pe:.1f}x vs 5-Yr Avg {pe_hist:.1f}x) "
            f"and peer average ({pe_peer:.1f}x), exceeding {variance:.0f}% tolerance."
        )
    else:
        if pe <= pe_peer * (1 + variance / 100) and pe > pe_hist * (1 + variance / 100):
            pe_notes = (
                f"Divergent valuation: within {variance:.0f}% of peers ({pe_peer:.1f}x), "
                f"but elevated relative to own 5-year history ({pe_hist:.1f}x). Potential value trap."
            )
        else:
            pe_notes = (
                f"Divergent valuation: within {variance:.0f}% of own history ({pe_hist:.1f}x), "
                f"but trading at a premium relative to peers ({pe_peer:.1f}x)."
            )

    pe_item = ValuationMetricItem(
        metric_name="P/E",
        current=pe,
        peer_avg=pe_peer,
        hist_5y_avg=pe_hist,
        status=pe_status,
        notes=pe_notes,
    )

    # 2. Secondary confirmation: EV/EBITDA (if provided)
    ev_item = None
    if (
        input_data.current_ev_ebitda is not None
        and input_data.peer_avg_ev_ebitda is not None
        and input_data.hist_5y_avg_ev_ebitda is not None
    ):
        ev = input_data.current_ev_ebitda
        ev_hist = input_data.hist_5y_avg_ev_ebitda
        ev_peer = input_data.peer_avg_ev_ebitda

        ev_status = _classify_metric(ev, ev_hist, ev_peer, variance)

        if ev_status == ValuationStatus.FAIR:
            ev_notes = (
                f"Current EV/EBITDA ({ev:.1f}x) within {variance:.0f}% tolerance of "
                f"5-Yr Avg ({ev_hist:.1f}x) and Peer Avg ({ev_peer:.1f}x)."
            )
        elif ev_status == ValuationStatus.EXPENSIVE:
            ev_notes = (
                f"Current EV/EBITDA ({ev:.1f}x) > 5-Yr Avg ({ev_hist:.1f}x) and "
                f"Peer Avg ({ev_peer:.1f}x), exceeding {variance:.0f}% tolerance."
            )
        else:
            ev_notes = (
                f"EV/EBITDA ({ev:.1f}x) diverges between peers ({ev_peer:.1f}x) "
                f"and historical ({ev_hist:.1f}x)."
            )

        ev_item = ValuationMetricItem(
            metric_name="EV/EBITDA",
            current=ev,
            peer_avg=ev_peer,
            hist_5y_avg=ev_hist,
            status=ev_status,
            notes=ev_notes,
        )

    # Overall valuation status follows primary P/E comparison
    overall_status = pe_status
    explanation = pe_notes

    return ValuationAnalysis(
        pe_comparison=pe_item,
        ev_ebitda_comparison=ev_item,
        overall_status=overall_status,
        explanation=explanation,
    )

