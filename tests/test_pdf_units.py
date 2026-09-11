"""
Unit-declaration detection, carry-forward, and normalization.
Strictly maps to chunkrule-v3.md §3d.
"""

from dataclasses import replace

from backend.app.acquisition.adapters.pdf.units import (
    apply_unit_normalization,
    build_unit_map,
    detect_unit_declaration,
    normalize_to_lakh,
)
from backend.app.acquisition.types import ExtractedField
from backend.app.models.enums import Confidence, ExtractionMethod, ReportingBasis


def test_detect_unit_declaration_variants():
    assert detect_unit_declaration("(All amounts are in ₹ in Millions, unless otherwise stated)") == "MILLION"
    assert detect_unit_declaration("(Amount in Lakhs)") == "LAKH"
    assert detect_unit_declaration("Figures are stated in Rs. Crore") == "CRORE"
    assert detect_unit_declaration("Just some narrative text with no declaration") is None


def test_build_unit_map_carries_forward():
    # Declared on page 0 (Minda-style: declared on some pages, not page 3).
    pages = [
        "(All amounts are in ₹ in Millions, unless otherwise stated)",
        "some narrative",
        "(Amount in Lakhs)",
        "audit fees note with no declaration on this page",
    ]
    unit_map = build_unit_map(pages)
    assert unit_map[0] == "MILLION"
    assert unit_map[1] == "MILLION"  # carried forward
    assert unit_map[2] == "LAKH"
    assert unit_map[3] == "LAKH"  # carried forward from page 2, not reset


def test_build_unit_map_undeclared_before_first_declaration():
    pages = ["no declaration here", "(Amount in Lakhs)"]
    unit_map = build_unit_map(pages)
    assert unit_map[0] is None
    assert unit_map[1] == "LAKH"


def test_normalize_to_lakh_conversions():
    assert normalize_to_lakh(3.07, "LAKH") == 3.07
    assert normalize_to_lakh(4.74, "MILLION") == 47.4
    assert normalize_to_lakh(1.0, "CRORE") == 100.0
    assert normalize_to_lakh(100.0, "THOUSAND") == 1.0
    assert normalize_to_lakh(5.0, None) is None


def _field(**overrides):
    base = dict(
        field_name="audit_fees",
        value=4.74,
        confidence=Confidence.HIGH,
        extraction_method=ExtractionMethod.TABLE_PARSE,
        source="mock.pdf",
        period="FY26",
        basis=ReportingBasis.CONSOLIDATED,
        raw_snippet="Statutory audit fee: 4.74",
        page=5,
    )
    base.update(overrides)
    return ExtractedField(**base)


def test_apply_unit_normalization_million_to_lakh():
    f = _field()
    unit_map = {4: "MILLION"}  # page 5 is 0-indexed 4
    normalized = apply_unit_normalization(f, unit_map)
    assert normalized.value == 47.4
    assert normalized.confidence == Confidence.HIGH
    assert "47.4 lakh" in normalized.raw_snippet


def test_apply_unit_normalization_undeclared_caps_confidence():
    f = _field()
    unit_map = {4: None}
    normalized = apply_unit_normalization(f, unit_map)
    assert normalized.value == 4.74  # unchanged — never guess
    assert normalized.confidence == Confidence.MEDIUM  # capped from HIGH
    assert "NOT normalized" in normalized.raw_snippet


def test_apply_unit_normalization_skips_non_monetary_fields():
    f = replace(_field(), field_name="years_of_track_record_available", value=5)
    unit_map = {4: "MILLION"}
    normalized = apply_unit_normalization(f, unit_map)
    assert normalized.value == 5  # untouched
