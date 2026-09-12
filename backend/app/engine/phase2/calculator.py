"""
Quantitative calculations and trend helpers for Phase 2 Gatekeeper.
Strictly maps to Phase2-Rules.md §0.1, §1, and §2.
"""

from typing import List, Optional, Tuple
from backend.app.models.enums import Phase2CheckStatus


def compute_median(values: List[float]) -> float:
    """Calculates the median of a numerical series."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2.0)


def is_consecutively_increasing(values: List[float], min_steps: int = 3) -> bool:
    """
    Returns True if the last `min_steps` entries are strictly increasing
    e.g. values[-3] < values[-2] < values[-1].
    """
    if len(values) < min_steps:
        return False
    window = values[-min_steps:]
    for i in range(len(window) - 1):
        if window[i + 1] <= window[i]:
            return False
    return True


def is_consecutively_decreasing(values: List[float], min_steps: int = 3) -> bool:
    """
    Returns True if the last `min_steps` entries are strictly decreasing
    e.g. values[-3] > values[-2] > values[-1].
    """
    if len(values) < min_steps:
        return False
    window = values[-min_steps:]
    for i in range(len(window) - 1):
        if window[i + 1] >= window[i]:
            return False
    return True


def compute_roce(ebit: float, total_equity: float, gross_debt: float, cash: float) -> float:
    """
    Check 7 formula: EBIT ÷ (Total equity + Total debt − Cash and equivalents) * 100
    """
    capital_employed = total_equity + gross_debt - cash
    if capital_employed <= 0:
        return -999.0  # Pathological or negative capital employed
    return (ebit / capital_employed) * 100.0


def compute_net_debt(gross_debt: float, cash: float) -> float:
    """Gross debt minus cash and equivalents."""
    return gross_debt - cash


def compute_net_debt_to_ebitda(gross_debt: float, cash: float, ebitda: float) -> float:
    """
    Check 10 formula: (Gross Debt - Cash) ÷ EBITDA
    """
    if ebitda <= 0:
        return 999.0 if (gross_debt - cash) > 0 else 0.0
    return (gross_debt - cash) / ebitda


def compute_debt_to_equity(gross_debt: float, total_equity: float) -> float:
    """
    Check 10 formula: Total Debt ÷ Total Equity
    """
    if total_equity <= 0:
        return 999.0
    return gross_debt / total_equity


def compute_interest_coverage(ebit: float, finance_cost: float) -> float:
    """
    Check 11 formula: EBIT ÷ Finance Cost
    """
    if finance_cost <= 0:
        return 999.0  # Effectively infinite coverage if no finance cost
    return ebit / finance_cost


def compute_ccc(receivable_days: float, inventory_days: float, payable_days: float) -> float:
    """
    Check 16 formula: Receivable Days + Inventory Days - Payable Days
    """
    return receivable_days + inventory_days - payable_days


def apply_trend_modifier(
    initial_status: Phase2CheckStatus,
    improving_3y: bool,
    deteriorating_3y: bool,
) -> Tuple[Phase2CheckStatus, bool]:
    """
    Implements Phase2-Rules.md §0.1 Trend Modifier:
    - If in CONCERN zone but improved for 3 consecutive years -> upgrade to PASS.
    - If in PASS zone but deteriorated for 3 consecutive years -> downgrade to CONCERN.
    - FAIL is never modified.
    """
    if initial_status == Phase2CheckStatus.CONCERN and improving_3y:
        return Phase2CheckStatus.PASS, True
    if initial_status == Phase2CheckStatus.PASS and deteriorating_3y:
        return Phase2CheckStatus.CONCERN, True
    return initial_status, False
