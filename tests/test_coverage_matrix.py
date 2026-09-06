"""
Phase 0 — Field Coverage Matrix Reflection Test.
Implements Phase1-WebApp-Implementation-Plan.md §3 & §11 (Phase 0).
Asserts that every field of CompanyInput is registered in the matrix with an owner,
source, basis requirement, confidence floor, and owner_phase.
"""

import pytest
from backend.app.models.coverage import FIELD_COVERAGE_MATRIX
from backend.app.models.schemas import CompanyInput


def test_field_coverage_matrix_complete():
    """
    Reflect over CompanyInput fields.
    Fails if ANY field in CompanyInput has no owner/entry in the field coverage matrix.
    """
    model_fields = set(CompanyInput.model_fields.keys())
    matrix_fields = set(FIELD_COVERAGE_MATRIX.keys())

    unowned_fields = model_fields - matrix_fields
    assert not unowned_fields, f"The following CompanyInput fields have no owner in the coverage matrix: {unowned_fields}"

    # Verify all matrix entries have non-empty owner, source, and owner_phase
    for field_name, meta in FIELD_COVERAGE_MATRIX.items():
        assert meta["owner"], f"Field '{field_name}' must have an assigned owner"
        assert meta["source"], f"Field '{field_name}' must have an assigned source"
        assert meta["owner_phase"], f"Field '{field_name}' must have an owner_phase"
        assert meta["confidence_floor"] in {"HIGH", "MEDIUM", "LOW", "MANUAL", "DERIVED"}
