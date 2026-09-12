"""
Canonical Phase 2 fixtures covering the 5 core test cases defined in phase2implementation.md §4.
"""

from backend.app.models.enums import (
    MoatType,
    Phase2Sector,
    ReportingBasis,
)
from backend.app.models.phase2_schemas import (
    AnnualFinancials,
    CompanyPhase2Input,
    CompetitivePositionInput,
    CreditAndCovenantInput,
    DebtRefinancingInput,
    GuaranteesOffBalanceSheetInput,
    LoansGivenInput,
    MoatInput,
    PestleContext,
    SegmentItem,
    SegmentYearData,
    WorkingCapitalYearData,
)


def make_saas_company_input() -> CompanyPhase2Input:
    """
    Case 1: The 'SaaS' Case (Asset-Light)
    High RoCE (~28%), zero debt (net cash), low absolute gross margins.
    Should Pass Asset-Light benchmarks -> CLEARED TO PHASE 3.
    """
    financials = [
        AnnualFinancials(period="FY20", revenue=100.0, ebitda=25.0, ebit=22.0, pat=18.0, total_equity=80.0, gross_debt=0.0, cash_and_equivalents=40.0, roce_pct=26.0, gross_margin_pct=65.0, ebitda_margin_pct=25.0, net_margin_pct=18.0, finance_cost=0.5, cfo=24.0),
        AnnualFinancials(period="FY21", revenue=125.0, ebitda=32.0, ebit=28.0, pat=22.0, total_equity=100.0, gross_debt=0.0, cash_and_equivalents=55.0, roce_pct=27.5, gross_margin_pct=66.0, ebitda_margin_pct=25.6, net_margin_pct=17.6, finance_cost=0.5, cfo=30.0),
        AnnualFinancials(period="FY22", revenue=160.0, ebitda=42.0, ebit=38.0, pat=30.0, total_equity=130.0, gross_debt=0.0, cash_and_equivalents=75.0, roce_pct=28.0, gross_margin_pct=67.0, ebitda_margin_pct=26.2, net_margin_pct=18.8, finance_cost=0.5, cfo=40.0),
        AnnualFinancials(period="FY23", revenue=210.0, ebitda=56.0, ebit=50.0, pat=40.0, total_equity=170.0, gross_debt=0.0, cash_and_equivalents=105.0, roce_pct=29.0, gross_margin_pct=67.5, ebitda_margin_pct=26.7, net_margin_pct=19.0, finance_cost=0.5, cfo=52.0),
        AnnualFinancials(period="FY24", revenue=270.0, ebitda=74.0, ebit=66.0, pat=52.0, total_equity=220.0, gross_debt=0.0, cash_and_equivalents=145.0, roce_pct=30.0, gross_margin_pct=68.0, ebitda_margin_pct=27.4, net_margin_pct=19.3, finance_cost=0.5, cfo=70.0),
    ]
    working_capital = [
        WorkingCapitalYearData(period="FY22", receivable_days=45.0, inventory_days=0.0, payable_days=25.0),
        WorkingCapitalYearData(period="FY23", receivable_days=44.0, inventory_days=0.0, payable_days=26.0),
        WorkingCapitalYearData(period="FY24", receivable_days=42.0, inventory_days=0.0, payable_days=27.0),
    ]
    return CompanyPhase2Input(
        ticker="SAASTECH",
        company_name="CloudScale Software Ltd",
        sector=Phase2Sector.ASSET_LIGHT,
        financials=financials,
        working_capital=working_capital,
        debt_refinancing=DebtRefinancingInput(short_term_borrowings=0.0, principal_due_next_12m=0.0),
        credit_covenants=CreditAndCovenantInput(credit_rating="AAA"),
        loans_given=LoansGivenInput(total_loans_advances_to_entities=5.0, pct_of_net_worth=2.2),
        guarantees=GuaranteesOffBalanceSheetInput(total_guarantees=0.0),
        moat=MoatInput(claimed_moat_type=MoatType.SWITCHING_COSTS, realisation_rising_vs_inflation=True),
        competition=CompetitivePositionInput(market_share_history={"FY22": 18.0, "FY23": 20.0, "FY24": 22.0}),
    )


def make_utility_company_input() -> CompanyPhase2Input:
    """
    Case 2: The 'Utility' Case (Regulated/Infra)
    Low RoCE (11%), high leverage (3.8x Net Debt/EBITDA), but >=70% regulated contracts.
    Should Pass Regulated/Infra benchmarks -> CLEARED TO PHASE 3.
    """
    financials = [
        AnnualFinancials(period="FY20", revenue=800.0, ebitda=400.0, ebit=240.0, pat=110.0, total_equity=1200.0, gross_debt=1700.0, cash_and_equivalents=100.0, roce_pct=10.5, gross_margin_pct=55.0, ebitda_margin_pct=50.0, net_margin_pct=13.8, finance_cost=95.0, cfo=320.0),
        AnnualFinancials(period="FY21", revenue=840.0, ebitda=420.0, ebit=250.0, pat=115.0, total_equity=1250.0, gross_debt=1750.0, cash_and_equivalents=120.0, roce_pct=10.8, gross_margin_pct=55.2, ebitda_margin_pct=50.0, net_margin_pct=13.7, finance_cost=100.0, cfo=340.0),
        AnnualFinancials(period="FY22", revenue=900.0, ebitda=450.0, ebit=270.0, pat=125.0, total_equity=1320.0, gross_debt=1800.0, cash_and_equivalents=140.0, roce_pct=11.0, gross_margin_pct=55.5, ebitda_margin_pct=50.0, net_margin_pct=13.9, finance_cost=105.0, cfo=370.0),
        AnnualFinancials(period="FY23", revenue=950.0, ebitda=480.0, ebit=290.0, pat=135.0, total_equity=1400.0, gross_debt=1850.0, cash_and_equivalents=160.0, roce_pct=11.2, gross_margin_pct=55.8, ebitda_margin_pct=50.5, net_margin_pct=14.2, finance_cost=110.0, cfo=400.0),
        AnnualFinancials(period="FY24", revenue=1020.0, ebitda=520.0, ebit=315.0, pat=150.0, total_equity=1500.0, gross_debt=1900.0, cash_and_equivalents=180.0, roce_pct=11.4, gross_margin_pct=56.0, ebitda_margin_pct=51.0, net_margin_pct=14.7, finance_cost=115.0, cfo=440.0),
    ]
    working_capital = [
        WorkingCapitalYearData(period="FY22", receivable_days=58.0, inventory_days=25.0, payable_days=40.0),
        WorkingCapitalYearData(period="FY23", receivable_days=60.0, inventory_days=24.0, payable_days=42.0),
        WorkingCapitalYearData(period="FY24", receivable_days=62.0, inventory_days=25.0, payable_days=43.0),
    ]
    return CompanyPhase2Input(
        ticker="POWERTOGETHER",
        company_name="National Grid Power Infra Ltd",
        sector=Phase2Sector.REGULATED_INFRA,
        regulated_contract_revenue_pct=85.0,  # Qualifies for Regulated/Infra (>70%)
        financials=financials,
        working_capital=working_capital,
        debt_refinancing=DebtRefinancingInput(short_term_borrowings=150.0, principal_due_next_12m=200.0, undrawn_committed_lines=300.0),
        credit_covenants=CreditAndCovenantInput(credit_rating="AA+"),
        loans_given=LoansGivenInput(total_loans_advances_to_entities=50.0, pct_of_net_worth=3.3),
        guarantees=GuaranteesOffBalanceSheetInput(total_guarantees=120.0, pct_of_net_worth=8.0),
        moat=MoatInput(claimed_moat_type=MoatType.LICENCE_REGULATORY, realisation_rising_vs_inflation=True),
        competition=CompetitivePositionInput(market_share_history={"FY22": 42.0, "FY23": 43.0, "FY24": 44.0}),
    )


def make_red_flag_company_input() -> CompanyPhase2Input:
    """
    Case 3: The 'Red Flag' Case (Disqualification)
    RoCE is 18%, but a financial covenant breach is disclosed.
    Should trigger immediate FAIL on Check 13 -> REJECT AT PHASE 2.
    """
    c = make_saas_company_input()
    c.ticker = "REDFLAG"
    c.credit_covenants.covenant_breach_disclosed = True
    c.credit_covenants.covenant_waiver_obtained = True
    return c


def make_cash_hoarder_company_input() -> CompanyPhase2Input:
    """
    Case 4: The 'Cash Hoarder' Case (Tightened Net-Cash Limit)
    Net-cash company with inter-corporate loans = 18% of net worth (> 15% limit).
    Should trigger FAIL on Check 14 -> REJECT AT PHASE 2.
    """
    c = make_saas_company_input()
    c.ticker = "CASHHOARD"
    c.loans_given.total_loans_advances_to_entities = 40.0
    c.loans_given.pct_of_net_worth = 18.2  # Exceeds tightened 15% net-cash limit
    return c


def make_deteriorating_company_input() -> CompanyPhase2Input:
    """
    Case 5: The 'Deterioration' Case (Trend Modifier)
    Leverage in PASS zone (<2.0x), but debt has risen for 3 consecutive years.
    Should be downgraded from PASS to CONCERN via Trend Modifier on Check 10.
    """
    c = make_saas_company_input()
    c.ticker = "DETERIORATING"
    c.sector = Phase2Sector.STANDARD
    # Provide 3 years with rising debt
    c.financials[-3].gross_debt = 40.0
    c.financials[-3].cash_and_equivalents = 10.0 # Net debt = 30.0 / EBITDA 42.0 = 0.71x
    c.financials[-2].gross_debt = 80.0
    c.financials[-2].cash_and_equivalents = 10.0 # Net debt = 70.0 / EBITDA 56.0 = 1.25x
    c.financials[-1].gross_debt = 130.0
    c.financials[-1].cash_and_equivalents = 10.0 # Net debt = 120.0 / EBITDA 74.0 = 1.62x (below 2.0x pass ceiling, but 3y rising!)
    return c
