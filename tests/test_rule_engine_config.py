"""
Unit and Integration tests for the Dynamic Configuration Rule Engine.
Tests decoupled logic thresholds, Excel upload/download, sector resolution, and mutation effects.
Strictly maps to Docs/rule-engine-implementation.md §4 & §5.
"""

import io
import pytest
from starlette.testclient import TestClient

from backend.app.api.main import app
from backend.app.fixtures import make_clean_company_input
from backend.app.models.enums import CheckStatus, Phase2CheckStatus, Phase2Sector, Verdict
from backend.app.engine.orchestrator import run_phase1
from backend.app.engine.phase2.orchestrator import run_phase2
from backend.app.engine.phase2.fixtures import make_saas_company_input
from backend.app.engine.rules.config import (
    Phase1RuleConfig,
    RulesConfiguration,
    create_default_rules_configuration,
)
from backend.app.engine.rules.registry import (
    get_active_rules_config,
    set_active_rules_config,
    reset_to_default_config,
    resolve_sector_from_keyword,
)
from backend.app.engine.rules.excel_io import (
    generate_default_rules_workbook,
    parse_rules_config_workbook,
)
import openpyxl


@pytest.fixture(autouse=True)
def reset_config_after_test():
    """Ensure every test begins and ends with standard calibrated defaults."""
    reset_to_default_config()
    yield
    reset_to_default_config()


def test_generate_default_rules_workbook_structure():
    """Verifies that the generated Rules_Config.xlsx has all 3 required sheets and expected headers."""
    raw_bytes = generate_default_rules_workbook()
    assert len(raw_bytes) > 1000

    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
    assert "Phase1_Thresholds" in wb.sheetnames
    assert "Phase2_Matrix" in wb.sheetnames
    assert "Sector_Mapping" in wb.sheetnames

    # Check Sheet 1 headers
    ws1 = wb["Phase1_Thresholds"]
    assert ws1.cell(row=1, column=1).value == "Check #"
    assert ws1.cell(row=1, column=2).value == "Metric"
    assert ws1.cell(row=1, column=3).value == "Fail_Threshold"

    # Check Sheet 2 headers
    ws2 = wb["Phase2_Matrix"]
    assert ws2.cell(row=1, column=1).value == "Sector Profile"
    assert ws2.cell(row=1, column=2).value == "Metric"

    # Check Sheet 3 headers
    ws3 = wb["Sector_Mapping"]
    assert ws3.cell(row=1, column=1).value == "Industry Keyword"
    assert ws3.cell(row=1, column=2).value == "Sector Profile"


def test_roundtrip_parsing_preserves_rules():
    """Verifies that generating and re-parsing the workbook preserves all thresholds without data loss."""
    raw_bytes = generate_default_rules_workbook()
    cfg = parse_rules_config_workbook(raw_bytes)

    assert cfg.phase1.promoter_pledge_fail_pct == 10.0
    assert cfg.phase1.rpt_sales_purchases_fail_pct == 10.0
    assert cfg.phase1.cfo_pat_ratio_fail_floor == 0.80

    assert Phase2Sector.ASSET_LIGHT.value in cfg.phase2_matrix
    assert cfg.phase2_matrix[Phase2Sector.ASSET_LIGHT.value].roce_pass_floor == 20.0
    assert cfg.phase2_matrix[Phase2Sector.STANDARD.value].roce_pass_floor == 15.0
    assert cfg.phase2_matrix[Phase2Sector.CAP_INTENSIVE.value].roce_pass_floor == 12.0

    assert len(cfg.sector_mappings) >= 20


def test_promoter_pledge_threshold_mutation():
    """
    Definition of Done Check:
    User can change a threshold in Excel and see the verdict change without touching code.
    A company with 8% pledge passes default (10%), but fails when threshold is lowered to 5%.
    """
    inp = make_clean_company_input()
    inp.pledged_pct_of_promoter_holding = 8.0  # 8% pledge
    inp.pledged_pct_history_last_4q = [8.0, 8.0, 8.0, 8.0]  # Stable trend

    # 1. Evaluate with Default Config (10% threshold) -> PASS
    res_default = run_phase1(inp)
    assert res_default.verdict == Verdict.CLEARED_TO_PHASE_2
    assert res_default.checks[1].status == CheckStatus.PASS

    # 2. Mutate Excel workbook: Change Promoter_Pledge threshold to 5%
    raw_bytes = generate_default_rules_workbook()
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes))
    ws1 = wb["Phase1_Thresholds"]

    for row in ws1.iter_rows(min_row=2):
        if row[1].value == "Promoter_Pledge":
            row[2].value = "5%"  # Tightened from 10% to 5%
            break

    buf = io.BytesIO()
    wb.save(buf)
    custom_cfg = parse_rules_config_workbook(buf.getvalue())
    set_active_rules_config(custom_cfg)

    # 3. Evaluate same company with active custom config -> FAIL
    res_custom = run_phase1(inp)
    assert res_custom.verdict == Verdict.REJECT
    assert res_custom.checks[1].status == CheckStatus.FAIL
    assert "vs 5.0% limit" in res_custom.checks[1].finding


def test_phase2_roce_threshold_mutation():
    """
    Mutating Phase 2 boundary matrix via Excel dynamically changes the Check 7 outcome.
    """
    p2_inp = make_saas_company_input()
    # SaaS company has RoCE = ~28-30% across years
    # Let's mutate the Asset-Light RoCE pass floor to 35% in Excel
    raw_bytes = generate_default_rules_workbook()
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes))
    ws2 = wb["Phase2_Matrix"]

    for row in ws2.iter_rows(min_row=2):
        if row[0].value == Phase2Sector.ASSET_LIGHT.value and row[1].value == "RoCE":
            row[2].value = "40%"  # Pass floor raised from 20% to 40%
            row[3].value = "30%"  # Fail ceiling raised from 15% to 30%
            break

    buf = io.BytesIO()
    wb.save(buf)
    custom_cfg = parse_rules_config_workbook(buf.getvalue())
    set_active_rules_config(custom_cfg)

    # Median RoCE is ~28.0%. Under standard rules (floor 20%), it's PASS.
    # Under mutated rules (fail ceiling 30%), 28.0% breaches the fail ceiling -> FAIL!
    p2_res = run_phase2(p2_inp)
    check7 = [c for c in p2_res.checks if c.check_id == "check7_return_on_capital"][0]
    assert check7.status == Phase2CheckStatus.FAIL


def test_sector_keyword_resolution():
    """Verifies that keywords map to correct sector profiles per Sheet 3."""
    cfg = get_active_rules_config()

    sec, note = resolve_sector_from_keyword("Modern SaaS Enterprise", cfg)
    assert sec == Phase2Sector.ASSET_LIGHT
    assert "SaaS" in note

    sec, note = resolve_sector_from_keyword("JSW Steel Works", cfg)
    assert sec == Phase2Sector.CAP_INTENSIVE
    assert "Steel" in note

    sec, note = resolve_sector_from_keyword("GAIL Gas Pipeline Ltd", cfg)
    assert sec == Phase2Sector.REGULATED_INFRA
    assert "Gas Pipeline" in note

    sec, note = resolve_sector_from_keyword("Random Unknown Enterprise", cfg)
    assert sec == Phase2Sector.STANDARD


def test_api_config_endpoints():
    """Tests the REST API endpoints for config retrieval, download, upload, and reset."""
    client = TestClient(app)

    # 1. GET /api/rules/config
    res = client.get("/api/rules/config")
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "DEFAULT"
    assert data["phase1"]["promoter_pledge_fail_pct"] == 10.0

    # 2. GET /api/rules/config/download
    res_dl = client.get("/api/rules/config/download")
    assert res_dl.status_code == 200
    assert res_dl.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    raw_excel = res_dl.content
    assert len(raw_excel) > 1000

    # 3. POST /api/rules/config/upload
    # Create modified Excel with 6% promoter pledge limit
    wb = openpyxl.load_workbook(io.BytesIO(raw_excel))
    ws1 = wb["Phase1_Thresholds"]
    for row in ws1.iter_rows(min_row=2):
        if row[1].value == "Promoter_Pledge":
            row[2].value = "6%"
            break
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    upload_res = client.post(
        "/api/rules/config/upload",
        files={"file": ("Rules_Config.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert upload_res.status_code == 200
    up_data = upload_res.json()
    assert up_data["status"] == "SUCCESS"
    assert up_data["source"] == "EXCEL_UPLOAD"

    # Verify active config updated
    active = client.get("/api/rules/config").json()
    assert active["source"] == "EXCEL_UPLOAD"
    assert active["phase1"]["promoter_pledge_fail_pct"] == 6.0

    # 4. POST /api/rules/config/reset
    reset_res = client.post("/api/rules/config/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["source"] == "DEFAULT"

    # Verify active config reverted
    active_after = client.get("/api/rules/config").json()
    assert active_after["source"] == "DEFAULT"
    assert active_after["phase1"]["promoter_pledge_fail_pct"] == 10.0


def test_api_resolve_sector_endpoint():
    """Tests the /api/rules/resolve-sector endpoint."""
    client = TestClient(app)
    res = client.post("/api/rules/resolve-sector", json={"keyword": "Toll Road Infra"})
    assert res.status_code == 200
    data = res.json()
    assert data["resolved_sector"] == Phase2Sector.REGULATED_INFRA.value
