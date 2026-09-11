"""
Rendering-layer tests for the Rev 3 confidence-disclosure and Rev 6
mandatory-warning-paragraph requirements.
Strictly maps to Phase1-Algorithms-v3.md §10 points 7 and 9.
"""

from backend.app.engine.orchestrator import run_phase1
from backend.app.fixtures import make_clean_company_input
from backend.app.models.enums import RetrievalTier, WorkingCapitalCycleTier
from backend.app.rendering.investor_prose import render_investor_report


def test_low_confidence_check_gets_plain_language_note():
    inp = make_clean_company_input()
    inp.pledged_pct_of_promoter_holding = 0.0
    inp.pledged_pct_history_last_4q = [0.0]
    inp.pledged_pct_history_retrieval_tier = RetrievalTier.FALLBACK
    res = run_phase1(inp)
    rendered = render_investor_report(res)

    assert 2 in rendered["low_confidence_checks"]
    card = next(c for c in rendered["checks"] if c["check_id"] == 2)
    assert card["confidence_note"] is not None
    assert "confidence" not in card["confidence_note"].lower()
    assert "quarter-by-quarter" in card["confidence_note"]

    # Checks with no confidence degradation carry no note.
    clean_card = next(c for c in rendered["checks"] if c["check_id"] == 1)
    assert clean_card["confidence_note"] is None


def test_use_of_funds_warning_gets_dedicated_paragraph():
    inp = make_clean_company_input()
    inp.working_capital_cycle_tier = WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING
    inp.cfo_last_5y = [-5.0, -5.0, -5.0, 10.0, 10.55]
    inp.pat_last_5y = [20.0, 20.0, 20.0, 20.0, 20.0]
    inp.revenue_last_5y = [100.0, 150.0, 250.0, 350.0, 400.0]
    inp.cumulative_working_capital_change_5y = -80.325
    inp.liquid_cushion_first_year = 22.0
    inp.liquid_cushion_last_year = 76.0
    res = run_phase1(inp)
    rendered = render_investor_report(res)

    assert 5 in rendered["warning_checks"]
    card = next(c for c in rendered["checks"] if c["check_id"] == 5)
    assert card["warning"] is not None
    assert "safe enough to study further" in card["warning"]["closing"]
    assert card["status"] == "PASS"

    other_card = next(c for c in rendered["checks"] if c["check_id"] == 1)
    assert other_card["warning"] is None
