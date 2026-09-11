"""
Sample company inputs used by the API (`/api/fixtures`) and the test suite.

This lives in the application package (not under ``tests/``) so production code
never imports test-only modules — importing ``tests`` would pull in ``pytest``
and would fail in deployments that do not bundle the test directory.
"""

from backend.app.models.enums import (
    AuditOpinion,
    Confidence,
    IndustrySector,
    RegulatoryNature,
    ReportingBasis,
    WorkingCapitalCycleTier,
)
from backend.app.models.schemas import (
    CompanyInput,
    FieldProvenance,
    RegulatoryActionInput,
)


def make_clean_company_input() -> CompanyInput:
    """Creates a base clean company input that passes all 6 checks."""
    provenance = {
        "audit_opinion": FieldProvenance(
            field_name="audit_opinion",
            source="AR FY24 Independent Auditor Report",
            period="FY24",
            confidence=Confidence.HIGH,
        ),
        "auditor_resigned_mid_tenure_last_3y": FieldProvenance(
            field_name="auditor_resigned_mid_tenure_last_3y",
            source="BSE Filings Reg 30",
            period="FY22-FY24",
            confidence=Confidence.HIGH,
        ),
        "regulatory_action": FieldProvenance(
            field_name="regulatory_action",
            source="SEBI Enforcement Archive",
            period="FY19-FY24",
            confidence=Confidence.MANUAL,
        ),
        "legal_fees": FieldProvenance(
            field_name="legal_fees",
            source="AR FY24 Note 28",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "audit_fees": FieldProvenance(
            field_name="audit_fees",
            source="AR FY24 Note 28",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "legal_fees_prior_year": FieldProvenance(
            field_name="legal_fees_prior_year",
            source="AR FY24 Note 28 Comparative",
            period="FY23",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "govt_shareholding_pct": FieldProvenance(
            field_name="govt_shareholding_pct",
            source="Screener.in Shareholding",
            period="Q4FY24",
            confidence=Confidence.HIGH,
        ),
        "promoter_holding_pct_of_company": FieldProvenance(
            field_name="promoter_holding_pct_of_company",
            source="Screener.in Shareholding",
            period="Q4FY24",
            confidence=Confidence.HIGH,
        ),
        "pledged_pct_of_promoter_holding": FieldProvenance(
            field_name="pledged_pct_of_promoter_holding",
            source="Screener.in Shareholding",
            period="Q4FY24",
            confidence=Confidence.HIGH,
        ),
        "pledged_pct_history_last_4q": FieldProvenance(
            field_name="pledged_pct_history_last_4q",
            source="Screener.in Shareholding",
            period="Q1FY24-Q4FY24",
            confidence=Confidence.HIGH,
        ),
        "rpt_sales_plus_purchases": FieldProvenance(
            field_name="rpt_sales_plus_purchases",
            source="AR FY24 Note 34 Related Party",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "revenue": FieldProvenance(
            field_name="revenue",
            source="AR FY24 P&L Statement",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "unusual_affiliate_dealings": FieldProvenance(
            field_name="unusual_affiliate_dealings",
            source="Analyst Review Notes",
            period="FY24",
            confidence=Confidence.MANUAL,
        ),
        "industry_sector": FieldProvenance(
            field_name="industry_sector",
            source="Screener.in company header (NSE/BSE sector tag)",
            period="FY24",
            confidence=Confidence.HIGH,
        ),
        "litigation_claims_exposure": FieldProvenance(
            field_name="litigation_claims_exposure",
            source="AR FY24 Note 31 Contingent Liabilities (sub-category)",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "routine_guarantee_exposure": FieldProvenance(
            field_name="routine_guarantee_exposure",
            source="AR FY24 Note 31 Contingent Liabilities (sub-category)",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "contingent_liabilities": FieldProvenance(
            field_name="contingent_liabilities",
            source="AR FY24 Note 31 Contingent",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "net_worth": FieldProvenance(
            field_name="net_worth",
            source="AR FY24 Balance Sheet",
            period="FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "working_capital_cycle_tier": FieldProvenance(
            field_name="working_capital_cycle_tier",
            source="Screener.in company header (NSE/BSE sector tag)",
            period="FY24",
            confidence=Confidence.HIGH,
        ),
        "cfo_last_5y": FieldProvenance(
            field_name="cfo_last_5y",
            source="Screener.in Cash Flow",
            period="FY20-FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "pat_last_5y": FieldProvenance(
            field_name="pat_last_5y",
            source="Screener.in P&L",
            period="FY20-FY24",
            basis=ReportingBasis.CONSOLIDATED,
            confidence=Confidence.HIGH,
        ),
        "cfo_changes_last_3y": FieldProvenance(
            field_name="cfo_changes_last_3y",
            source="AR Corporate Governance Report",
            period="FY22-FY24",
            confidence=Confidence.HIGH,
        ),
        "restatement_of_past_accounts": FieldProvenance(
            field_name="restatement_of_past_accounts",
            source="AR Note 1 Accounting Policies",
            period="FY24",
            confidence=Confidence.HIGH,
        ),
    }

    return CompanyInput(
        ticker="TATAMOTORS",
        as_of_date="2024-03-31",
        data_basis=ReportingBasis.CONSOLIDATED,
        # Check 1
        auditor_resigned_mid_tenure_last_3y=False,
        audit_opinion=AuditOpinion.CLEAN,
        regulatory_action=RegulatoryActionInput(
            active_or_past_5y=False, nature=RegulatoryNature.NONE
        ),
        legal_fees=3.0,
        audit_fees=30.0,
        legal_fees_prior_year=2.8,
        # Auto & auto components — Tier4 (legal-fee sector) per Rules §8.4-E
        industry_sector=IndustrySector.TIER4_MANUFACTURING_INDUSTRIALS,
        legal_fee_surge_explained=None,
        # Check 2
        govt_shareholding_pct=0.0,
        promoter_holding_pct_of_company=60.0,
        pledged_pct_of_promoter_holding=2.0,
        pledged_pct_history_last_4q=[2.0, 2.0, 2.0, 2.0],
        pledged_pct_of_total_shares=1.2,
        # Check 3
        rpt_sales_plus_purchases=40.0,
        revenue=1000.0,
        unusual_affiliate_dealings=False,
        # Check 4 — Auto & auto components carry meaningful routine
        # guarantee/LC volume; litigation exposure kept small and genuine.
        contingent_liabilities=320.0,
        litigation_claims_exposure=20.0,
        routine_guarantee_exposure=300.0,
        contingent_liabilities_breakdown_available=True,
        net_worth=1000.0,
        # Check 5 — Auto & auto components: Moderate-cycle (0.75 floor / 3yr trigger)
        working_capital_cycle_tier=WorkingCapitalCycleTier.MODERATE_CYCLE,
        cfo_last_5y=[100.0, 110.0, 120.0, 130.0, 140.0],
        pat_last_5y=[90.0, 100.0, 110.0, 120.0, 130.0],
        # Check 6
        cfo_changes_last_3y=0,
        restatement_of_past_accounts=False,
        # Track record
        years_of_track_record_available=5,
        provenance=provenance,
    )
