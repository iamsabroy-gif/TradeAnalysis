"""
Pure helper functions for the Phase 1 Decision Engine.
Strictly maps to Phase1-Algorithms-v3.md §1, §2, §2a-§2h.
Pure functions — zero network or disk I/O.
"""

from typing import Dict, List, Optional, Tuple

from backend.app.models.enums import (
    CheckStatus,
    CompanyType,
    Confidence,
    IndustrySector,
    ReportingBasis,
    RetrievalTier,
    WorkingCapitalCycleTier,
)
from backend.app.models.schemas import CompanyInput, FieldProvenance


def classify_company_type(
    govt_shareholding_pct: Optional[float],
    promoter_holding_pct_of_company: Optional[float],
) -> CompanyType:
    """
    Feeds Check 2's auto-pass exceptions. Run once per company before checks.
    Phase1-Algorithms.md §1
    """
    if govt_shareholding_pct is not None and govt_shareholding_pct >= 51.0:
        return CompanyType.GOVT_PSU
    if promoter_holding_pct_of_company is not None and promoter_holding_pct_of_company == 0.0:
        return CompanyType.PROFESSIONALLY_MANAGED
    return CompanyType.PRIVATE_PROMOTER


def apply_track_record_guard(
    years_required: int,
    years_available: Optional[int],
    disqualifying_event_found: bool,
) -> Optional[CheckStatus]:
    """
    Applies to Checks 1, 5, 6 (lookback windows of 3, 5, 3 years respectively).
    Returns a forced CheckStatus, or None meaning "proceed to normal evaluation".
    Phase1-Algorithms.md §2
    """
    if years_available is None:
        # We do not know history length. Disqualifying event still fails; else INCONCLUSIVE
        if disqualifying_event_found:
            return CheckStatus.FAIL
        return CheckStatus.INCONCLUSIVE

    if years_available >= years_required:
        return None  # full window available, evaluate normally

    if disqualifying_event_found:
        return CheckStatus.FAIL  # short history can still fail

    return CheckStatus.INCONCLUSIVE


def compose_citation(
    input_data: CompanyInput,
    field_names: List[str],
) -> Tuple[Optional[str], List[str]]:
    """
    Constructs citation string from provenance of consumed fields.
    Returns (citation_str, missing_provenance_field_names).
    Phase1-Algorithms.md §2a
    """
    cited: List[str] = []
    missing: List[str] = []

    for f in field_names:
        if f in input_data.provenance:
            p: FieldProvenance = input_data.provenance[f]
            basis_part = (
                ""
                if p.basis == ReportingBasis.NOT_APPLICABLE
                else f" ({p.basis.value})"
            )
            page_part = "" if p.page is None else f", p.{p.page}"
            cited.append(
                f"{f}: {p.source} {p.period}{basis_part}{page_part} [{p.confidence.value}]"
            )
        else:
            missing.append(f)

    if not cited:
        return None, missing
    return "; ".join(cited), missing


def assert_comparable(
    input_data: CompanyInput,
    field_names: List[str],
) -> Optional[str]:
    """
    Applies to every check dividing one reported figure by another.
    Returns explanation string if fields cannot be validly compared, else None.
    Phase1-Algorithms.md §2b
    """
    provs = [input_data.provenance[f] for f in field_names if f in input_data.provenance]
    if len(provs) < 2:
        return None  # nothing to cross-check; citation_gaps records the gap

    financial = [p for p in provs if p.basis != ReportingBasis.NOT_APPLICABLE]
    bases = sorted(list(set(p.basis for p in financial)))

    if len(bases) > 1:
        bases_str = [b.value for b in bases]
        return (
            f"mixed reporting basis across {field_names}: {bases_str} "
            "— consolidated and standalone figures are not comparable"
        )

    if (
        input_data.data_basis is not None
        and len(bases) == 1
        and bases[0] != input_data.data_basis
    ):
        return (
            f"figures are {bases[0].value} but this run is declared "
            f"{input_data.data_basis.value}"
        )

    periods = sorted(list(set(p.period for p in provs)))
    if len(periods) > 1:
        return (
            f"figures span different periods {periods} "
            "— a ratio across periods is not a valid comparison"
        )

    return None


def derive_pledged_pct_of_total_shares(input_data: CompanyInput) -> Optional[float]:
    """
    Directly reported value wins over derived.
    (promoter's % of company) x (pledged % of that holding) / 100
    Phase1-Algorithms.md §2c
    """
    if input_data.pledged_pct_of_total_shares is not None:
        return input_data.pledged_pct_of_total_shares

    if (
        input_data.promoter_holding_pct_of_company is None
        or input_data.pledged_pct_of_promoter_holding is None
    ):
        return None

    return round(
        (input_data.promoter_holding_pct_of_company * input_data.pledged_pct_of_promoter_holding)
        / 100.0,
        4,
    )


def build_finding_suffix(years_required: Optional[int], years_available: Optional[int]) -> str:
    """
    Rev 3 — Phase1-Algorithms-v3.md §2d.
    Returns "" when the full window was available or years_required does not
    apply to this check.
    """
    if years_required is None or years_available is None:
        return ""
    if years_available >= years_required:
        return ""
    return f" (based on {years_available} of the required {years_required} years)"


def roll_up_confidence(
    fields_used: List[str],
    retrieval_tier_fields: Dict[str, Optional[RetrievalTier]],
) -> Confidence:
    """
    Rev 3 — Phase1-Algorithms-v3.md §2d.
    A field with no tier entry is assumed PRIMARY. HIGH unless a FALLBACK
    tier is present, in which case MEDIUM.
    """
    tiers = [retrieval_tier_fields.get(f, RetrievalTier.PRIMARY) for f in fields_used if f in retrieval_tier_fields]
    if not tiers:
        return Confidence.HIGH
    if any(t == RetrievalTier.UNAVAILABLE for t in tiers):
        return Confidence.HIGH  # unreachable in practice — see §2d
    if any(t == RetrievalTier.FALLBACK for t in tiers):
        return Confidence.MEDIUM
    return Confidence.HIGH


# Rev 4 — Phase1-Algorithms-v3.md §2f / Phase1-Rules-v2.md §8.4-E.
# Flag threshold as a percentage-of-revenue figure (e.g. 1.35 means 1.35%).
_SECTOR_FLAG_THRESHOLDS = {
    IndustrySector.TIER1_FINANCIAL_SERVICES: 1.35,
    IndustrySector.TIER2_PHARMA_HEALTHCARE_IT: 0.75,
    IndustrySector.TIER3_REGULATED_GOVT_TELECOM_ENERGY: 0.68,
    IndustrySector.TIER4_MANUFACTURING_INDUSTRIALS: 0.45,
    IndustrySector.TIER5_RETAIL_FMCG_CONSUMER: 0.30,
    IndustrySector.TIER_OTHER_UNCLASSIFIED: 0.75,
}


def sector_flag_threshold(sector: IndustrySector) -> float:
    """Rev 4 — Rules §8.4-E table, reproduced as data."""
    return _SECTOR_FLAG_THRESHOLDS[sector]


# Rev 5 — Phase1-Algorithms-v3.md §2g / Phase1-Rules-v2.md §8.4-G.
_WC_CYCLE_THRESHOLDS = {
    WorkingCapitalCycleTier.LONG_CYCLE_PROJECT_ACCOUNTING: {"cfo_pat_floor": 0.65, "negative_years_trigger": 4},
    WorkingCapitalCycleTier.MODERATE_CYCLE: {"cfo_pat_floor": 0.75, "negative_years_trigger": 3},
    WorkingCapitalCycleTier.SHORT_CYCLE_ASSET_LIGHT: {"cfo_pat_floor": 0.85, "negative_years_trigger": 3},
    WorkingCapitalCycleTier.TIER_OTHER_UNCLASSIFIED: {"cfo_pat_floor": 0.75, "negative_years_trigger": 3},
    # LENDING_INSTITUTION_NA deliberately has no entry — check5 must branch to
    # INCONCLUSIVE before calling this function for that tier.
}


def working_capital_cycle_thresholds(tier: WorkingCapitalCycleTier) -> Dict[str, float]:
    """Rev 5 — Rules §8.4-G table, reproduced as data."""
    return _WC_CYCLE_THRESHOLDS[tier]


def verify_use_of_funds(
    input_data: CompanyInput,
    cumulative_pat: float,
    cumulative_cfo: float,
) -> Optional[Dict[str, object]]:
    """
    Rev 6 — Phase1-Algorithms-v3.md §2h / Phase1-Rules-v2.md §8.4-H.
    Returns None (not {"verified": False}) if the fields needed to attempt
    verification are missing — callers MUST treat None as "cannot verify".
    """
    required = [
        input_data.revenue_last_5y,
        input_data.cumulative_working_capital_change_5y,
        input_data.liquid_cushion_first_year,
        input_data.liquid_cushion_last_year,
    ]
    if any(v is None for v in required):
        return None
    if len(input_data.revenue_last_5y) < 2 or input_data.revenue_last_5y[0] <= 0:
        return None  # can't compute a first->last growth ratio

    notes: List[str] = []

    # (a) Growth is real
    revenue_growth_ratio = input_data.revenue_last_5y[-1] / input_data.revenue_last_5y[0]
    growth_ok = revenue_growth_ratio >= 1.5
    notes.append(
        f"(a) revenue grew {round(revenue_growth_ratio, 2)}x over the window "
        f"(>= 1.5x required): {'met' if growth_ok else 'NOT met'}"
    )

    # (b) The shortfall is a working-capital story
    gap = cumulative_pat - cumulative_cfo
    if gap <= 0:
        return None  # only meaningful when there IS a shortfall to explain
    wc_coverage = abs(input_data.cumulative_working_capital_change_5y) / abs(gap)
    wc_ok = wc_coverage >= 0.60
    notes.append(
        f"(b) working-capital change covers {round(wc_coverage * 100, 1)}% of the "
        f"PAT-CFO gap (>= 60% required): {'met' if wc_ok else 'NOT met'}"
    )

    # (c) Not hoarding
    cushion_pct_first = input_data.liquid_cushion_first_year / input_data.revenue_last_5y[0]
    cushion_pct_last = input_data.liquid_cushion_last_year / input_data.revenue_last_5y[-1]
    hoarding_ok = cushion_pct_last <= cushion_pct_first * 1.10
    notes.append(
        f"(c) liquid cushion is {round(cushion_pct_last * 100, 1)}% of revenue in the "
        f"latest year vs {round(cushion_pct_first * 100, 1)}% in the first year "
        f"(must not exceed a 10% rise): {'met' if hoarding_ok else 'NOT met'}"
    )

    return {"verified": bool(growth_ok and wc_ok and hoarding_ok), "notes": notes}
