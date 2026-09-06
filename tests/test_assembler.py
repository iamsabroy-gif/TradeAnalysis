"""
Assembler pipeline and precedence tests.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §6 & §7.3.
"""

from pathlib import Path
import pytest

from backend.app.acquisition.adapters.parsers.screener_tables import parse_screener_html
from backend.app.acquisition.assembler import assemble
from backend.app.acquisition.types import CompanyIdentity
from backend.app.engine.orchestrator import run_phase1
from backend.app.models.enums import (
    AuditOpinion,
    Confidence,
    ExtractionMethod,
    RegulatoryNature,
    ReportingBasis,
    Verdict,
)
from backend.app.models.schemas import RegulatoryActionInput


def test_assembler_pipeline_to_decision_engine():
    fixture_path = Path(__file__).parent / "fixtures" / "screener" / "tatamotors.html"
    html = fixture_path.read_text(encoding="utf-8")

    # 1. Parse HTML
    screener_res = parse_screener_html(
        html,
        source_url="https://www.screener.in/company/TATAMOTORS/consolidated/",
        basis=ReportingBasis.CONSOLIDATED,
    )

    ident = CompanyIdentity(
        ticker="TATAMOTORS",
        screener_code="TATAMOTORS",
        company_name="Tata Motors Ltd",
    )

    # 2. Provide manual overrides for the PDF-owned fields (Phase D)
    manual_fields = {
        "auditor_resigned_mid_tenure_last_3y": False,
        "audit_opinion": AuditOpinion.CLEAN,
        "regulatory_action": RegulatoryActionInput(active_or_past_5y=False, nature=RegulatoryNature.NONE),
        "legal_fees": 50.0,
        "audit_fees": 30.0,
        "legal_fees_prior_year": 45.0,
        "rpt_sales_plus_purchases": 40.0,
        "unusual_affiliate_dealings": False,
        "contingent_liabilities": 100.0,
        "cfo_changes_last_3y": 0,
        "restatement_of_past_accounts": False,
    }

    # 3. Assemble
    company_input, review_items = assemble(
        identity=ident,
        as_of_date="2024-03-31",
        basis=ReportingBasis.CONSOLIDATED,
        results=[screener_res],
        manual_overrides=manual_fields,
        uploader="lead_analyst",
    )

    assert len(review_items) == 0
    assert company_input.ticker == "TATAMOTORS"
    assert company_input.cfo_last_5y == [100.0, 110.0, 120.0, 130.0, 140.0]
    assert company_input.promoter_holding_pct_of_company == 60.0
    assert company_input.pledged_pct_of_promoter_holding == 2.0

    # 4. Run through Decision Engine
    res = run_phase1(company_input)
    assert res.verdict == Verdict.CLEARED_TO_PHASE_2
    assert len(res.failing_checks) == 0
    assert len(res.inconclusive_checks) == 0
    # Every field used in pass verdict must have provenance, no gaps!
    assert res.citation_gaps == []


def test_assembler_basis_filter():
    fixture_path = Path(__file__).parent / "fixtures" / "screener" / "tatamotors.html"
    html = fixture_path.read_text(encoding="utf-8")

    # Scraped as STANDALONE
    res = parse_screener_html(
        html,
        source_url="https://www.screener.in/company/TATAMOTORS/",
        basis=ReportingBasis.STANDALONE,
    )

    ident = CompanyIdentity(ticker="TATAMOTORS", screener_code="TATAMOTORS")

    # Run declared as CONSOLIDATED
    company_input, review_items = assemble(
        identity=ident,
        as_of_date="2024-03-31",
        basis=ReportingBasis.CONSOLIDATED,
        results=[res],
    )

    # Financial fields requiring basis (cfo_last_5y, revenue, net_worth) should be dropped to review_items
    review_field_names = [item.field_name for item in review_items]
    assert "cfo_last_5y" in review_field_names
    assert company_input.cfo_last_5y is None
