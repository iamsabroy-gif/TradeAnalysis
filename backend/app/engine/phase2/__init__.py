from .matrix import INDUSTRY_BOUNDARY_MATRIX, SectorThresholds, get_sector_thresholds
from .calculator import compute_median, compute_roce, compute_net_debt_to_ebitda, compute_ccc, apply_trend_modifier
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
from .orchestrator import run_phase2, Phase2GatekeeperError
from .fixtures import (
    make_saas_company_input,
    make_utility_company_input,
    make_red_flag_company_input,
    make_cash_hoarder_company_input,
    make_deteriorating_company_input,
)

__all__ = [
    "INDUSTRY_BOUNDARY_MATRIX",
    "SectorThresholds",
    "get_sector_thresholds",
    "compute_median",
    "compute_roce",
    "compute_net_debt_to_ebitda",
    "compute_ccc",
    "apply_trend_modifier",
    "check7_return_on_capital",
    "check8_margin_trajectory",
    "check9_segment_economics",
    "check10_leverage_quantum_and_trend",
    "check11_interest_service_adequacy",
    "check12_maturity_and_refinancing",
    "check13_cost_of_debt_rating_covenants",
    "check14_loans_and_advances_given",
    "check15_guarantees_and_off_balance_sheet",
    "check16_working_capital_cycle",
    "check17_moat_corroboration",
    "check18_competitive_position",
    "run_phase2",
    "Phase2GatekeeperError",
    "make_saas_company_input",
    "make_utility_company_input",
    "make_red_flag_company_input",
    "make_cash_hoarder_company_input",
    "make_deteriorating_company_input",
]
