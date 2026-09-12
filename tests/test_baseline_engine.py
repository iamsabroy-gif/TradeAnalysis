"""
Unit tests for the Baseline Engine Implementation (Docs/Rules/baseline-engine-implementation.md).
Validates:
1. Canonical 18-check Master Rule Definitions schema & catalog completeness.
2. Dual Excel I/O compatibility (Master_Rule_Definitions sheet vs legacy sheets).
3. Linear sequence: Phase 1 Binary Stop-on-Fail Gate -> Phase 2 Quality Screen.
4. Sector resolution & Boundary calibration.
5. API endpoints for Master Rule Definitions.
"""

import io
import pytest
from openpyxl import load_workbook
from starlette.testclient import TestClient

from backend.app.api.main import app
from backend.app.fixtures import make_clean_company_input
from backend.app.engine.phase2 import (
    make_saas_company_input,
    make_red_flag_company_input,
)
from backend.app.models.enums import (
    AuditOpinion,
    CheckStatus,
    Phase2Sector,
    Phase2Verdict,
    Verdict,
)
from backend.app.models.phase2_schemas import CompanyPhase2Input
from backend.app.engine.rules.config import (
    RulesConfiguration,
    create_default_rules_configuration,
)
from backend.app.engine.rules.excel_io import (
    generate_default_rules_workbook,
    parse_rules_config_workbook,
)
from backend.app.engine.rules.baseline_engine import (
    BaselineEngine,
    BaselineEvaluationResult,
)


@pytest.fixture
def clean_config() -> RulesConfiguration:
    return create_default_rules_configuration()


@pytest.fixture
def clean_engine(clean_config: RulesConfiguration) -> BaselineEngine:
    return BaselineEngine(config=clean_config)


# ---------------------------------------------------------------------------
# 1. Master Rule Definitions Schema & Catalog Completeness
# ---------------------------------------------------------------------------

def test_master_rules_catalog_completeness(clean_config: RulesConfiguration):
    """Verify Master Rule Definitions contains all 18 checks as specified in Table 1.1."""
    rules = clean_config.master_rules
    assert len(rules) == 18

    # Phase 1: Checks 1 to 6
    p1_rules = [r for r in rules if r.phase == 1]
    assert len(p1_rules) == 6
    assert [r.check_num for r in p1_rules] == [1, 2, 3, 4, 5, 6]

    # Phase 2: Checks 7 to 18
    p2_rules = [r for r in rules if r.phase == 2]
    assert len(p2_rules) == 12
    assert [r.check_num for r in p2_rules] == list(range(7, 19))

    # Verify sector-awareness flags per Table 1.1 (Checks 4, 7, 10, 11, 16 are Sector-Aware)
    sector_aware_checks = {4, 7, 10, 11, 16}
    for r in rules:
        if r.check_num in sector_aware_checks:
            assert r.sector_aware is True, f"Check {r.check_num} should be sector_aware"
        else:
            assert r.sector_aware is False, f"Check {r.check_num} should NOT be sector_aware"


# ---------------------------------------------------------------------------
# 2. Dual Excel Workbook I/O
# ---------------------------------------------------------------------------

def test_dual_workbook_generation_and_parsing(clean_config: RulesConfiguration):
    """Verify workbook contains Master_Rule_Definitions, Sector_Boundary_Matrix, and Company_Sector_Map."""
    raw_excel = generate_default_rules_workbook(clean_config)
    wb = load_workbook(io.BytesIO(raw_excel), data_only=True)

    # Required baseline specification sheets
    assert "Master_Rule_Definitions" in wb.sheetnames
    assert "Sector_Boundary_Matrix" in wb.sheetnames
    assert "Company_Sector_Map" in wb.sheetnames

    # Legacy sheets for backwards compatibility
    assert "Phase1_Thresholds" in wb.sheetnames
    assert "Phase2_Matrix" in wb.sheetnames

    # Check Master_Rule_Definitions row count (Header + 18 checks = 19 rows)
    master_ws = wb["Master_Rule_Definitions"]
    rows = list(master_ws.iter_rows(values_only=True))
    assert len(rows) == 19
    header = rows[0]
    assert "Check #" in header
    assert "Phase" in header
    assert "Default Op" in header

    # Round-trip parsing
    parsed_config = parse_rules_config_workbook(raw_excel)
    assert len(parsed_config.master_rules) == 18
    assert parsed_config.phase1.promoter_pledge_fail_pct == 10.0


def test_excel_master_rules_override_propagation():
    """Verify modifying Master_Rule_Definitions cell overrides thresholds in parsed config."""
    config = create_default_rules_configuration()
    raw_excel = generate_default_rules_workbook(config)
    wb = load_workbook(io.BytesIO(raw_excel))

    # Change Check 2 Fail Value (Promoter Pledge) in Master_Rule_Definitions to 15.0
    ws = wb["Master_Rule_Definitions"]
    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=2).value == 2:  # Check #2 (Promoter Pledge)
            ws.cell(row=row, column=7, value="15.0")  # Col 7: Default Fail Value
            break

    out = io.BytesIO()
    wb.save(out)
    updated_excel = out.getvalue()

    parsed = parse_rules_config_workbook(updated_excel)
    assert parsed.phase1.promoter_pledge_fail_pct == 15.0
    r2 = next(r for r in parsed.master_rules if r.check_num == 2)
    assert r2.default_fail_value == "15.0"


# ---------------------------------------------------------------------------
# 3. Linear Sequence: Phase 1 Binary Stop-on-Fail Gate
# ---------------------------------------------------------------------------

def test_baseline_engine_stop_on_fail_stops_immediately(clean_engine: BaselineEngine):
    """When Phase 1 fails (e.g. Check 3 pledge = 34% > 10%), Phase 2 MUST NOT be executed."""
    p1_inp = make_clean_company_input()
    p1_inp.pledged_pct_of_promoter_holding = 34.0
    p1_inp.pledged_pct_history_last_4q = [25.0, 28.0, 30.0, 34.0]

    p2_inp = make_saas_company_input()

    result: BaselineEvaluationResult = clean_engine.execute(
        phase1_input=p1_inp,
        phase2_input=p2_inp,
    )

    # Verification of linear Stop-on-Fail gate
    assert result.phase1_cleared is False
    assert result.phase1_result.verdict == Verdict.REJECT
    assert result.phase2_result is None, "Phase 2 must NOT run when Phase 1 fails!"
    assert "REJECT" in result.final_verdict
    assert result.checks_evaluated_count == 6  # Only Phase 1 checks were evaluated

    # Reports
    assert "Phase 1 Forensic Safety Gate Table" not in result.analyst_table_markdown or "Phase 2" not in result.analyst_table_markdown


def test_baseline_engine_audit_disqualification(clean_engine: BaselineEngine):
    """When Phase 1 fails on Check 1 (Qualified audit opinion), execution halts immediately."""
    p1_inp = make_clean_company_input()
    p1_inp.audit_opinion = AuditOpinion.QUALIFIED
    p2_inp = make_saas_company_input()

    result = clean_engine.execute(phase1_input=p1_inp, phase2_input=p2_inp)

    assert result.phase1_cleared is False
    assert result.phase2_result is None
    assert "REJECT" in result.final_verdict
    assert result.checks_evaluated_count == 6


def test_baseline_engine_full_clearance(clean_engine: BaselineEngine):
    """When Phase 1 clears, Phase 2 evaluates all 12 quality checks and synthesizes verdict."""
    p1_inp = make_clean_company_input()
    p2_inp = make_saas_company_input()

    result: BaselineEvaluationResult = clean_engine.execute(
        phase1_input=p1_inp,
        phase2_input=p2_inp,
    )

    assert result.phase1_cleared is True
    assert result.phase1_result.verdict == Verdict.CLEARED_TO_PHASE_2
    assert result.phase2_result is not None
    assert result.phase2_result.verdict == Phase2Verdict.CLEARED_TO_PHASE_3
    assert result.checks_evaluated_count == 18  # 6 Phase 1 + 12 Phase 2 = 18 total checks!
    assert "CLEARED" in result.final_verdict

    # Verify combined tables
    assert "Phase 1 Forensic Safety Gate Table" in result.analyst_table_markdown
    assert "Phase 2 Business Quality & Moat Table" in result.analyst_table_markdown
    assert "Phase 1: Forensic Integrity" in result.investor_report_markdown
    assert "Phase 2: Quality, Moat & Capital Allocation" in result.investor_report_markdown


# ---------------------------------------------------------------------------
# 4. Auto Sector Resolution
# ---------------------------------------------------------------------------

def test_baseline_engine_auto_sector_resolution(clean_engine: BaselineEngine):
    """Baseline engine resolves sector from keyword tags if not explicitly set."""
    p1_inp = make_clean_company_input()
    p1_inp.ticker = "TCS"
    p2_inp = make_saas_company_input()
    p2_inp.sector = Phase2Sector.STANDARD
    p2_inp.company_name = "Tata Consultancy Services Software"

    result = clean_engine.execute(
        phase1_input=p1_inp,
        phase2_input=p2_inp,
    )

    assert result.phase2_result is not None
    # 'software' in company name resolves to ASSET_LIGHT
    assert result.phase2_result.sector == Phase2Sector.ASSET_LIGHT


# ---------------------------------------------------------------------------
# 5. REST API Integration
# ---------------------------------------------------------------------------

def test_api_master_definitions_endpoint():
    """Verify GET /api/rules/master-definitions returns all 18 rules."""
    client = TestClient(app)
    response = client.get("/api/rules/master-definitions")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 18
    assert len(data["master_rules"]) == 18
    assert data["master_rules"][0]["check_num"] == 1
    assert data["master_rules"][17]["check_num"] == 18


def test_api_config_download_attachment_filename():
    """Verify GET /api/rules/config/download provides Master_Rule_Definitions.xlsx."""
    client = TestClient(app)
    response = client.get("/api/rules/config/download")
    assert response.status_code == 200
    assert "Master_Rule_Definitions.xlsx" in response.headers.get("content-disposition", "")
    content = response.content
    wb = load_workbook(io.BytesIO(content), data_only=True)
    assert "Master_Rule_Definitions" in wb.sheetnames
    assert "Sector_Boundary_Matrix" in wb.sheetnames
