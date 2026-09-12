"""
Industry Boundary Matrix for Phase 2 Gatekeeper.
Strictly maps to Phase2-Rules.md §2.5.
"""

from typing import Any, NamedTuple, Optional, Tuple
from backend.app.models.enums import Phase2Sector


class SectorThresholds(NamedTuple):
    # Check 7: Return on Capital Employed (5-yr median)
    roce_pass_floor: float
    roce_fail_ceiling: float

    # Check 10: Leverage Quantum (Net Debt / EBITDA)
    net_debt_ebitda_pass_ceiling: float
    net_debt_ebitda_fail_floor: float

    # Check 11: Interest-Service Adequacy (EBIT / Finance Cost)
    interest_coverage_pass_floor: float
    interest_coverage_fail_ceiling: float

    # Check 12: Max Short-Term Debt % of Total Debt (triggers CONCERN if exceeded)
    max_st_debt_concern_pct: float

    # Check 16: Working Capital Cycle 3-yr CCC Deterioration (days)
    ccc_deterioration_fail_days: float

    # Check 16: Critical Cap on Receivable Days (triggers FAIL if CCC deteriorated > threshold AND rec days > cap)
    max_receivable_days_critical_cap: float


INDUSTRY_BOUNDARY_MATRIX = {
    Phase2Sector.ASSET_LIGHT: SectorThresholds(
        roce_pass_floor=20.0,
        roce_fail_ceiling=15.0,
        net_debt_ebitda_pass_ceiling=1.0,
        net_debt_ebitda_fail_floor=2.0,
        interest_coverage_pass_floor=6.0,
        interest_coverage_fail_ceiling=3.0,
        max_st_debt_concern_pct=15.0,
        ccc_deterioration_fail_days=30.0,
        max_receivable_days_critical_cap=60.0,
    ),
    Phase2Sector.STANDARD: SectorThresholds(
        roce_pass_floor=15.0,
        roce_fail_ceiling=10.0,
        net_debt_ebitda_pass_ceiling=2.0,
        net_debt_ebitda_fail_floor=3.0,
        interest_coverage_pass_floor=4.0,
        interest_coverage_fail_ceiling=2.0,
        max_st_debt_concern_pct=20.0,
        ccc_deterioration_fail_days=60.0,
        max_receivable_days_critical_cap=90.0,
    ),
    Phase2Sector.CAP_INTENSIVE: SectorThresholds(
        roce_pass_floor=12.0,
        roce_fail_ceiling=8.0,
        net_debt_ebitda_pass_ceiling=3.0,
        net_debt_ebitda_fail_floor=4.5,
        interest_coverage_pass_floor=3.0,
        interest_coverage_fail_ceiling=1.5,
        max_st_debt_concern_pct=15.0,
        ccc_deterioration_fail_days=90.0,
        max_receivable_days_critical_cap=120.0,
    ),
    Phase2Sector.REGULATED_INFRA: SectorThresholds(
        roce_pass_floor=10.0,
        roce_fail_ceiling=6.0,
        net_debt_ebitda_pass_ceiling=4.0,
        net_debt_ebitda_fail_floor=6.0,
        interest_coverage_pass_floor=2.0,
        interest_coverage_fail_ceiling=1.0,
        max_st_debt_concern_pct=10.0,
        ccc_deterioration_fail_days=120.0,
        max_receivable_days_critical_cap=150.0,
    ),
}


def _to_sector_thresholds(cfg: Any) -> SectorThresholds:
    if isinstance(cfg, SectorThresholds):
        return cfg
    return SectorThresholds(
        roce_pass_floor=cfg.roce_pass_floor,
        roce_fail_ceiling=cfg.roce_fail_ceiling,
        net_debt_ebitda_pass_ceiling=cfg.net_debt_ebitda_pass_ceiling,
        net_debt_ebitda_fail_floor=cfg.net_debt_ebitda_fail_floor,
        interest_coverage_pass_floor=cfg.interest_coverage_pass_floor,
        interest_coverage_fail_ceiling=cfg.interest_coverage_fail_ceiling,
        max_st_debt_concern_pct=cfg.max_st_debt_concern_pct,
        ccc_deterioration_fail_days=cfg.ccc_deterioration_fail_days,
        max_receivable_days_critical_cap=cfg.max_receivable_days_critical_cap,
    )


def get_sector_thresholds(
    sector: Phase2Sector,
    regulated_contract_revenue_pct: Optional[float] = None,
    matrix_config: Optional[Any] = None,
) -> Tuple[Phase2Sector, SectorThresholds, Optional[str]]:
    """
    Returns resolved sector profile, thresholds, and any note regarding qualification.
    Enforces rule §2.5(3): Regulated/Infra requires >=70% regulated contract revenue.
    Looks up thresholds dynamically from active Rules Configuration if available.
    """
    # Look up active dynamic configuration if not explicitly passed
    cfg_matrix = matrix_config
    if cfg_matrix is None:
        try:
            from backend.app.engine.rules.registry import get_active_rules_config
            cfg_matrix = get_active_rules_config().phase2_matrix
        except Exception:
            cfg_matrix = None

    def _resolve(sec: Phase2Sector) -> SectorThresholds:
        if cfg_matrix and sec.value in cfg_matrix:
            return _to_sector_thresholds(cfg_matrix[sec.value])
        return INDUSTRY_BOUNDARY_MATRIX.get(sec, INDUSTRY_BOUNDARY_MATRIX[Phase2Sector.STANDARD])

    if sector == Phase2Sector.REGULATED_INFRA:
        if regulated_contract_revenue_pct is None or regulated_contract_revenue_pct < 70.0:
            note = (
                f"Regulated/Infra requested but regulated contract revenue is "
                f"{regulated_contract_revenue_pct or 0.0}% (< 70% requirement). "
                f"Falling back to Standard sector thresholds per §2.5(3)."
            )
            return Phase2Sector.STANDARD, _resolve(Phase2Sector.STANDARD), note
        return sector, _resolve(sector), None

    return sector, _resolve(sector), None

