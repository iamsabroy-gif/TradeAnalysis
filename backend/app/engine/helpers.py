"""
Pure helper functions for the Phase 1 Decision Engine.
Strictly maps to Phase1-Algorithms.md §1, §2, §2a, §2b, §2c.
Pure functions — zero network or disk I/O.
"""

from typing import List, Optional, Tuple

from backend.app.models.enums import (
    CheckStatus,
    CompanyType,
    ReportingBasis,
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
