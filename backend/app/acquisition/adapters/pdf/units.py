"""
Reporting-unit detection and normalization for Annual Report PDF extraction.
Maps strictly to chunkrule-v3.md §3d.

No annual report states its unit next to the number — it is declared once in a
header band ("All amounts are in ₹ in Millions, unless otherwise stated") and
the declaration is not repeated on every page. Carrying the wrong (or no)
unit forward silently corrupts every downstream ratio by 10x or 100x, so this
module is a dedicated, independently testable layer rather than inline logic
scattered across the extraction tiers.
"""

import re
from dataclasses import replace as dataclass_replace
from typing import Dict, List, Optional

from backend.app.acquisition.adapters.pdf.anchors import normalize_quotes
from backend.app.acquisition.types import ExtractedField
from backend.app.models.enums import Confidence

# The note-derived monetary fields this pipeline extracts from Annual Report
# PDFs — every one of them can be denominated in lakh/million/crore depending
# on the report, per chunkrule-v3.md §3d. Fields sourced from Screener.in
# (cfo_last_5y, pat_last_5y, revenue, net_worth, ...) are excluded: Screener
# renders in a fixed unit and carries its own comparability guarantees.
MONETARY_NOTE_FIELDS = {
    "contingent_liabilities",
    "audit_fees",
    "legal_fees",
    "legal_fees_prior_year",
    "rpt_sales_plus_purchases",
}

# §3d.1 — capture the declaration. Tolerant of "Rs.", "INR", "₹", "Rupees",
# and the three units observed in the field validation (chunkrule-v3.md §11):
# lakh, million, crore. "Thousand" and "Crore" included for completeness even
# though not observed in the three validation reports.
_UNIT_DECLARATION_RE = re.compile(
    r"(?:all\s+)?(?:amounts?|figures?|values?)\s+(?:are\s+)?(?:stated\s+)?in\b"
    r".{0,20}?\b(lakh|lac|million|crore|thousand)s?\b",
    re.IGNORECASE | re.DOTALL,
)

# Canonical unit -> multiplier to convert into lakh (the canonical storage unit).
_TO_LAKH: Dict[str, float] = {
    "THOUSAND": 0.01,
    "LAKH": 1.0,
    "MILLION": 10.0,
    "CRORE": 100.0,
}

_UNIT_ALIASES = {
    "lakh": "LAKH",
    "lac": "LAKH",
    "million": "MILLION",
    "crore": "CRORE",
    "thousand": "THOUSAND",
}


def detect_unit_declaration(text: str) -> Optional[str]:
    """
    §3d.1 — returns the canonical unit ("LAKH"/"MILLION"/"CRORE"/"THOUSAND")
    declared on this page's text, or None if no declaration is present.
    If more than one declaration appears on a page, the last one wins (a
    report occasionally repeats the declaration verbatim; a differing one
    would mean a genuine mid-page unit change, which the last-wins rule
    handles correctly either way).
    """
    if not text:
        return None
    normalized = normalize_quotes(text)
    matches = list(_UNIT_DECLARATION_RE.finditer(normalized))
    if not matches:
        return None
    return _UNIT_ALIASES[matches[-1].group(1).lower()]


def build_unit_map(page_texts: List[str]) -> Dict[int, Optional[str]]:
    """
    §3d.2 — carries the most recent declaration forward across pages that do
    not repeat it. page_idx -> unit ("LAKH"/"MILLION"/"CRORE"/"THOUSAND"), or
    None for any page before the first declaration anywhere in the document
    (§3d.3 — an undeclared unit is unknown, never assumed to be lakh).
    """
    unit_map: Dict[int, Optional[str]] = {}
    current: Optional[str] = None
    for page_idx, text in enumerate(page_texts):
        declared = detect_unit_declaration(text)
        if declared is not None:
            current = declared
        unit_map[page_idx] = current
    return unit_map


def normalize_to_lakh(value: float, unit: Optional[str]) -> Optional[float]:
    """
    §3d.4 — normalizes a value into the canonical lakh unit. Returns None
    (never a guessed value) when the unit is unresolved — the caller must
    treat this as "unit unknown", capping confidence and skipping
    normalization rather than defaulting to lakh, per §3d.3.
    """
    if unit is None or unit not in _TO_LAKH:
        return None
    return round(value * _TO_LAKH[unit], 6)


def apply_unit_normalization(
    f: ExtractedField,
    unit_map: Dict[int, Optional[str]],
) -> ExtractedField:
    """
    §3d.4 — normalizes a monetary note field's value into lakh using the unit
    declared at (or carried forward to) its source page. Non-monetary fields
    and fields with no page citation pass through unchanged.

    An unresolved unit (§3d.3) is not normalized and is not silently trusted
    at HIGH confidence: the printed value is kept as-is, the field is flagged
    in its own raw_snippet so a reviewer can see normalization did not run,
    and confidence is capped at MEDIUM.
    """
    if f.field_name not in MONETARY_NOTE_FIELDS or f.page is None:
        return f

    unit = unit_map.get(f.page - 1)
    normalized = normalize_to_lakh(f.value, unit)

    if normalized is None:
        capped_confidence = (
            Confidence.MEDIUM if f.confidence in (Confidence.HIGH,) else f.confidence
        )
        return dataclass_replace(
            f,
            confidence=capped_confidence,
            raw_snippet=f"{f.raw_snippet} [unit not declared on or before p.{f.page} — value NOT normalized]",
        )

    unit_label = (unit or "").lower()
    return dataclass_replace(
        f,
        value=normalized,
        raw_snippet=f"{f.raw_snippet} [{f.value} {unit_label} -> {normalized} lakh]",
    )
