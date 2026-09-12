"""
Data models for the Dynamic Configuration Rule Engine.
Decouples thresholds and sector boundary matrices from hardcoded execution logic.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.models.enums import Phase2Sector


class Phase1RuleConfig(BaseModel):
    """
    User-configurable thresholds for Phase 1 Forensic Safety Checks (Checks 1–6).
    """
    # Check 2: Promoter Pledging
    promoter_pledge_fail_pct: float = Field(
        default=10.0,
        description="Threshold where promoter pledge % of promoter holding triggers FAIL (> 10%)"
    )
    promoter_pledge_low_holding_floor_pct: float = Field(
        default=35.0,
        description="Promoter holding floor below which tighter pledge threshold applies (< 35%)"
    )
    promoter_pledge_low_holding_fail_pct: float = Field(
        default=5.0,
        description="Tighter pledge threshold if promoter holding is below floor (> 5%)"
    )
    promoter_pledge_total_shares_fail_pct: float = Field(
        default=5.0,
        description="Pledged shares as % of total shares triggering FAIL (> 5%)"
    )

    # Check 3: Related Party Transactions
    rpt_sales_purchases_fail_pct: float = Field(
        default=10.0,
        description="RPT sales + purchases as % of revenue triggering FAIL (> 10%)"
    )

    # Check 4: Contingent Liabilities
    contingent_liabilities_net_worth_fail_pct: float = Field(
        default=15.0,
        description="Total contingent liabilities as % of net worth triggering FAIL (> 15%)"
    )
    litigation_claims_net_worth_fail_pct: float = Field(
        default=10.0,
        description="Litigation and tax claims as % of net worth triggering FAIL (> 10%)"
    )

    # Check 5: Cash Conversion (CFO vs PAT)
    cfo_pat_ratio_fail_floor: float = Field(
        default=0.80,
        description="5-year cumulative CFO / PAT ratio floor below which FAIL triggers (< 0.80)"
    )

    # Check 6: Regulatory & Legal Fees
    legal_fee_surge_fail_pct: float = Field(
        default=100.0,
        description="YoY surge in legal fees triggering FAIL if unexplained (> 100%)"
    )
    legal_to_audit_fee_multiplier: float = Field(
        default=3.0,
        description="Ratio of legal fees to audit fees triggering FAIL (> 3.0x)"
    )


class SectorThresholdConfig(BaseModel):
    """
    Industry boundary thresholds for a specific Phase 2 sector profile.
    """
    sector: Phase2Sector
    # Check 7: RoCE (5-yr median)
    roce_pass_floor: float = Field(description="RoCE >= this value passes")
    roce_fail_ceiling: float = Field(description="RoCE < this value fails")

    # Check 10: Leverage Quantum (Net Debt / EBITDA)
    net_debt_ebitda_pass_ceiling: float = Field(description="Net Debt/EBITDA <= this value passes")
    net_debt_ebitda_fail_floor: float = Field(description="Net Debt/EBITDA > this value fails")

    # Check 11: Interest Coverage (EBIT / Finance Cost)
    interest_coverage_pass_floor: float = Field(description="Interest Coverage >= this value passes")
    interest_coverage_fail_ceiling: float = Field(description="Interest Coverage < this value fails")

    # Check 12: Max Short-Term Debt % of Total Debt
    max_st_debt_concern_pct: float = Field(description="ST debt > this % of total triggers CONCERN")

    # Check 16: Working Capital Deterioration (days)
    ccc_deterioration_fail_days: float = Field(description="3-yr CCC rise > this triggers FAIL/CONCERN")

    # Check 16: Critical Cap on Receivable Days
    max_receivable_days_critical_cap: float = Field(description="Receivable days ceiling")


# Type alias for the Phase 2 industry matrix dictionary
Phase2MatrixConfig = Dict[str, SectorThresholdConfig]


class Phase2RuleConfig(BaseModel):
    """
    User-configurable thresholds for non-sector Phase 2 quality checks (Checks 7–18).
    """
    ebitda_margin_var_fail_pct: float = Field(
        default=-25.0,
        description="EBITDA margin deterioration relative variance fail ceiling (< -25%)"
    )
    credit_rating_fail_floor: str = Field(
        default="BBB-",
        description="Minimum investment-grade credit rating floor (< BBB- triggers concern/fail)"
    )
    loans_advances_net_worth_fail_pct: float = Field(
        default=25.0,
        description="Loans and advances as % of Net Worth triggering concern/fail (> 25%)"
    )
    guarantees_net_worth_fail_pct: float = Field(
        default=50.0,
        description="Corporate guarantees as % of Net Worth triggering concern/fail (> 50%)"
    )
    moat_evidence_count_fail_floor: int = Field(
        default=2,
        description="Minimum independent moat evidence items required (< 2 triggers concern)"
    )


class MasterRuleDefinition(BaseModel):
    """
    Specification of a check in the Master Rule Definitions schema (Docs/Rules/baseline-engine-implementation.md §1.1).
    Covers all 18 checks across Phase 1 and Phase 2.
    """
    phase: int = Field(description="Evaluation phase (1 or 2)")
    check_num: int = Field(description="Check number (1 to 18)")
    check_name: str = Field(description="Descriptive check title")
    input_metric: str = Field(description="Primary input metric name")
    logic_type: str = Field(description="Categorical, Numeric, Ratio, Count, Relative, Trend, Boolean")
    default_op: str = Field(description="Comparison operator (!=, >, <, Deteriorate, Decline)")
    default_fail_value: str = Field(description="Default value triggering FAIL")
    sector_aware: bool = Field(description="True if threshold varies by industry sector matrix")
    description: Optional[str] = Field(default=None, description="Detailed check rationale and trigger condition")


class SectorKeywordItem(BaseModel):
    """
    Mapping an industry keyword / sub-sector to its Sector Profile.
    """
    keyword: str
    sector: Phase2Sector
    notes: Optional[str] = None


class RulesConfiguration(BaseModel):
    """
    Complete configuration container for both Phase 1 and Phase 2.
    Decoupled from execution code and dynamically updatable via Excel.
    """
    version: str = "1.0.0"
    source: str = "DEFAULT"  # "DEFAULT" | "EXCEL_UPLOAD" | "CUSTOM"
    description: str = "Baseline Calibrated Rules Configuration (Full 18-Check Engine)"
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    master_rules: List[MasterRuleDefinition] = Field(default_factory=list)
    phase1: Phase1RuleConfig = Field(default_factory=Phase1RuleConfig)
    phase2_rules: Phase2RuleConfig = Field(default_factory=Phase2RuleConfig)
    phase2_matrix: Dict[str, SectorThresholdConfig] = Field(default_factory=dict)
    sector_mappings: List[SectorKeywordItem] = Field(default_factory=list)


def create_default_rules_configuration() -> RulesConfiguration:
    """
    Constructs the standard, canonically calibrated configuration matching
    Phase 1 Rules (§1-§8), Phase 2 Rules (§2.5), and Master Rule Definitions (§1.1).
    """
    matrix: Dict[str, SectorThresholdConfig] = {
        Phase2Sector.ASSET_LIGHT.value: SectorThresholdConfig(
            sector=Phase2Sector.ASSET_LIGHT,
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
        Phase2Sector.STANDARD.value: SectorThresholdConfig(
            sector=Phase2Sector.STANDARD,
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
        Phase2Sector.CAP_INTENSIVE.value: SectorThresholdConfig(
            sector=Phase2Sector.CAP_INTENSIVE,
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
        Phase2Sector.REGULATED_INFRA.value: SectorThresholdConfig(
            sector=Phase2Sector.REGULATED_INFRA,
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

    mappings: List[SectorKeywordItem] = [
        # Asset Light
        SectorKeywordItem(keyword="SaaS", sector=Phase2Sector.ASSET_LIGHT, notes="Software as a Service"),
        SectorKeywordItem(keyword="IT Services", sector=Phase2Sector.ASSET_LIGHT, notes="Software and tech services"),
        SectorKeywordItem(keyword="Software", sector=Phase2Sector.ASSET_LIGHT, notes="Packaged software"),
        SectorKeywordItem(keyword="FMCG Asset-Light", sector=Phase2Sector.ASSET_LIGHT, notes="Contract manufactured consumer brands"),
        SectorKeywordItem(keyword="Platform", sector=Phase2Sector.ASSET_LIGHT, notes="Digital marketplace/platform"),
        
        # Standard
        SectorKeywordItem(keyword="Auto", sector=Phase2Sector.STANDARD, notes="Automobiles and components"),
        SectorKeywordItem(keyword="Auto Ancillary", sector=Phase2Sector.STANDARD, notes="Automotive parts"),
        SectorKeywordItem(keyword="General Manufacturing", sector=Phase2Sector.STANDARD, notes="Standard engineered goods"),
        SectorKeywordItem(keyword="Consumer Durables", sector=Phase2Sector.STANDARD, notes="Appliances and electronics"),
        SectorKeywordItem(keyword="Retail", sector=Phase2Sector.STANDARD, notes="Retail chains"),
        SectorKeywordItem(keyword="Pharma Formulations", sector=Phase2Sector.STANDARD, notes="Finished pharmaceutical dosage"),
        SectorKeywordItem(keyword="Textiles", sector=Phase2Sector.STANDARD, notes="Apparel and garments"),
        
        # Capital Intensive
        SectorKeywordItem(keyword="Cement", sector=Phase2Sector.CAP_INTENSIVE, notes="Heavy cement plants"),
        SectorKeywordItem(keyword="Steel", sector=Phase2Sector.CAP_INTENSIVE, notes="Blast furnaces and rolling mills"),
        SectorKeywordItem(keyword="Metals", sector=Phase2Sector.CAP_INTENSIVE, notes="Non-ferrous and ferrous metals"),
        SectorKeywordItem(keyword="Chemicals", sector=Phase2Sector.CAP_INTENSIVE, notes="Bulk & specialty chemical plants"),
        SectorKeywordItem(keyword="Real Estate", sector=Phase2Sector.CAP_INTENSIVE, notes="Property development"),
        SectorKeywordItem(keyword="Infrastructure EPC", sector=Phase2Sector.CAP_INTENSIVE, notes="Heavy construction & EPC"),
        SectorKeywordItem(keyword="Mining", sector=Phase2Sector.CAP_INTENSIVE, notes="Mineral extraction"),
        SectorKeywordItem(keyword="Paper", sector=Phase2Sector.CAP_INTENSIVE, notes="Pulp and paper manufacturing"),
        
        # Regulated Utility / Concessions
        SectorKeywordItem(keyword="Power Transmission", sector=Phase2Sector.REGULATED_INFRA, notes="Regulated return on equity transmission"),
        SectorKeywordItem(keyword="Power Distribution", sector=Phase2Sector.REGULATED_INFRA, notes="Regulated discoms"),
        SectorKeywordItem(keyword="Gas Pipeline", sector=Phase2Sector.REGULATED_INFRA, notes="City gas and trunk pipelines"),
        SectorKeywordItem(keyword="Toll Road", sector=Phase2Sector.REGULATED_INFRA, notes="BOT/TOT annuity road concessions"),
        SectorKeywordItem(keyword="Port Concession", sector=Phase2Sector.REGULATED_INFRA, notes="Long-term regulated tariff ports"),
        SectorKeywordItem(keyword="Airport Concession", sector=Phase2Sector.REGULATED_INFRA, notes="AERA regulated aeronautical tariffs"),
    ]

    master_rules: List[MasterRuleDefinition] = [
        # Phase 1 Checks (Forensic Safety Gate)
        MasterRuleDefinition(
            phase=1, check_num=1, check_name="Auditor Integrity", input_metric="Audit_Opinion",
            logic_type="Categorical", default_op="!=", default_fail_value="Clean", sector_aware=False,
            description="Audit opinion must be unqualified/clean; mid-tenure auditor resignations trigger FAIL"
        ),
        MasterRuleDefinition(
            phase=1, check_num=2, check_name="Promoter Pledge", input_metric="Pledge_Pct",
            logic_type="Numeric", default_op=">", default_fail_value="10%", sector_aware=False,
            description="Promoter pledged shares must not exceed 10% of holding (stricter 5% if holding < 35%)"
        ),
        MasterRuleDefinition(
            phase=1, check_num=3, check_name="RPT Leakage", input_metric="RPT_Revenue_Pct",
            logic_type="Numeric", default_op=">", default_fail_value="10%", sector_aware=False,
            description="Related Party Transactions must not exceed 10% of revenue without structural justification"
        ),
        MasterRuleDefinition(
            phase=1, check_num=4, check_name="Contingent Liab", input_metric="Cont_Liab_NW_Pct",
            logic_type="Numeric", default_op=">", default_fail_value="15%", sector_aware=True,
            description="Total contingent liabilities must not exceed 15% of net worth; tax/legal claims capped at 10%"
        ),
        MasterRuleDefinition(
            phase=1, check_num=5, check_name="Cash Conversion", input_metric="CFO_PAT_Ratio",
            logic_type="Ratio", default_op="<", default_fail_value="0.80", sector_aware=False,
            description="5-year cumulative CFO / PAT ratio must meet or exceed 0.80 conversion floor"
        ),
        MasterRuleDefinition(
            phase=1, check_num=6, check_name="Exec Stability", input_metric="CFO_Changes",
            logic_type="Count", default_op=">", default_fail_value="1", sector_aware=False,
            description="No more than 1 mid-tenure CFO resignation allowed within rolling 3 years"
        ),

        # Phase 2 Checks (Business Quality & Capital Allocation)
        MasterRuleDefinition(
            phase=2, check_num=7, check_name="RoCE", input_metric="Median_RoCE",
            logic_type="Numeric", default_op="<", default_fail_value="10%", sector_aware=True,
            description="5-year median Return on Capital Employed hurdle calibrated to industry capital intensity"
        ),
        MasterRuleDefinition(
            phase=2, check_num=8, check_name="Margin Trend", input_metric="EBITDA_Margin_Var",
            logic_type="Relative", default_op="<", default_fail_value="-25%", sector_aware=False,
            description="EBITDA margin trend must not deteriorate by more than 25% relative to historical mean"
        ),
        MasterRuleDefinition(
            phase=2, check_num=9, check_name="Seg Economics", input_metric="Seg_Rev_Margin_Trend",
            logic_type="Trend", default_op="Deteriorate", default_fail_value="N/A", sector_aware=False,
            description="Core operating segment margin and revenue trajectory across 3-year lookback"
        ),
        MasterRuleDefinition(
            phase=2, check_num=10, check_name="Leverage", input_metric="NetDebt_EBITDA",
            logic_type="Numeric", default_op=">", default_fail_value="3.0x", sector_aware=True,
            description="Net Debt to EBITDA quantum hurdle calibrated to sector profile"
        ),
        MasterRuleDefinition(
            phase=2, check_num=11, check_name="Int Coverage", input_metric="Interest_Coverage",
            logic_type="Numeric", default_op="<", default_fail_value="2.0x", sector_aware=True,
            description="EBIT to Finance Cost coverage floor calibrated to sector debt capacity"
        ),
        MasterRuleDefinition(
            phase=2, check_num=12, check_name="Maturity", input_metric="ST_Debt_Coverage",
            logic_type="Boolean", default_op="!=", default_fail_value="True", sector_aware=False,
            description="Short-term debt maturity profile and liquid refinancing cushion"
        ),
        MasterRuleDefinition(
            phase=2, check_num=13, check_name="Credit Rating", input_metric="Credit_Rating",
            logic_type="Categorical", default_op="<", default_fail_value="BBB-", sector_aware=False,
            description="Investment-grade domestic credit rating from registered CRA"
        ),
        MasterRuleDefinition(
            phase=2, check_num=14, check_name="Loans Given", input_metric="Loan_NW_Pct",
            logic_type="Numeric", default_op=">", default_fail_value="25%", sector_aware=False,
            description="Loans and advances extended to third parties or related entities as % of Net Worth"
        ),
        MasterRuleDefinition(
            phase=2, check_num=15, check_name="Guarantees", input_metric="Guar_NW_Pct",
            logic_type="Numeric", default_op=">", default_fail_value="50%", sector_aware=False,
            description="Corporate guarantees and off-balance sheet exposures as % of Net Worth"
        ),
        MasterRuleDefinition(
            phase=2, check_num=16, check_name="WC Cycle", input_metric="CCC_Deterioration",
            logic_type="Numeric", default_op=">", default_fail_value="60 days", sector_aware=True,
            description="Cash conversion cycle 3-year expansion and debtor days critical ceiling"
        ),
        MasterRuleDefinition(
            phase=2, check_num=17, check_name="Moat Corrob", input_metric="Moat_Evidence_Count",
            logic_type="Count", default_op="<", default_fail_value="2", sector_aware=False,
            description="Independent corroboration of structural competitive moat factors"
        ),
        MasterRuleDefinition(
            phase=2, check_num=18, check_name="Comp Position", input_metric="Market_Share_Trend",
            logic_type="Trend", default_op="Decline", default_fail_value="N/A", sector_aware=False,
            description="Market share trajectory and competitive positioning in core market"
        ),
    ]

    return RulesConfiguration(
        version="1.0.0",
        source="DEFAULT",
        description="Standard Baseline Engine Master Configuration (All 18 Checks)",
        master_rules=master_rules,
        phase1=Phase1RuleConfig(),
        phase2_rules=Phase2RuleConfig(),
        phase2_matrix=matrix,
        sector_mappings=mappings,
    )

