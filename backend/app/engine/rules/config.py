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
    description: str = "Baseline Calibrated Rules Configuration"
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    phase1: Phase1RuleConfig = Field(default_factory=Phase1RuleConfig)
    phase2_matrix: Dict[str, SectorThresholdConfig] = Field(default_factory=dict)
    sector_mappings: List[SectorKeywordItem] = Field(default_factory=list)


def create_default_rules_configuration() -> RulesConfiguration:
    """
    Constructs the standard, canonically calibrated configuration matching
    Phase 1 Rules (§1-§8) and Phase 2 Rules (§2.5).
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

    return RulesConfiguration(
        version="1.0.0",
        source="DEFAULT",
        description="Standard Calibrated Rules Configuration (Phase 1 & Phase 2)",
        phase1=Phase1RuleConfig(),
        phase2_matrix=matrix,
        sector_mappings=mappings,
    )
