"""
Phase 3 Gatekeeper Engine (Valuation & Story Confirmation).
"""

from .fixtures import (
    make_fair_value_hold_input,
    make_high_conviction_buy_input,
    make_overvalued_avoid_input,
    make_speculative_buy_input,
    make_story_contradiction_avoid_input,
)
from .orchestrator import (
    Phase3GatekeeperError,
    run_phase3,
    synthesize_phase3_verdict,
)
from .return_path import calc_return_path
from .story_scan import scan_contradictions
from .valuation import calc_valuation

__all__ = [
    "calc_valuation",
    "calc_return_path",
    "scan_contradictions",
    "synthesize_phase3_verdict",
    "run_phase3",
    "Phase3GatekeeperError",
    "make_high_conviction_buy_input",
    "make_speculative_buy_input",
    "make_fair_value_hold_input",
    "make_overvalued_avoid_input",
    "make_story_contradiction_avoid_input",
]
