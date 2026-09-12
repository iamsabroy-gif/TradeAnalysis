"""
Excel Import / Export service for the Dynamic Configuration Rule Engine.
Reads and writes `Rules_Config.xlsx` using openpyxl.
Strictly maps to Docs/rule-engine-implementation.md §1.
"""

import io
import re
from typing import Any, Dict, List, Optional, Union
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from backend.app.models.enums import Phase2Sector
from backend.app.engine.rules.config import (
    MasterRuleDefinition,
    Phase1RuleConfig,
    Phase2MatrixConfig,
    Phase2RuleConfig,
    Phase3RuleConfig,
    RulesConfiguration,
    SectorKeywordItem,
    SectorThresholdConfig,
    create_default_rules_configuration,
)


# Styles for Excel Generation
HEADER_FILL = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
HEADER_FONT = Font(name="Arial", size=11, bold=True, color="FFFFFF")
ROW_FONT = Font(name="Arial", size=10)
BOLD_FONT = Font(name="Arial", size=10, bold=True)
NOTE_FONT = Font(name="Arial", size=9, italic=True, color="64748B")
THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)
ALT_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")


def _clean_num(val: Any) -> Optional[float]:
    """Parses float from number, string, or percentage representation."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "")
    if not s:
        return None
    # Strip trailing multiplier 'x' (e.g. '3.0x' -> 3.0)
    if s.lower().endswith("x"):
        s = s[:-1].strip()
    # Strip percentage '%' (e.g. '10%' -> 10.0)
    if s.endswith("%"):
        try:
            return float(s[:-1].strip())
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def generate_default_rules_workbook(config: Optional[RulesConfiguration] = None) -> bytes:
    """
    Generates the canonical 3-sheet `Master_Rule_Definitions.xlsx` workbook template
    as specified in Docs/Rules/baseline-engine-implementation.md §1.
    Sheets:
      1. Master_Rule_Definitions (All 18 Checks across Phase 1 and Phase 2)
      2. Sector_Boundary_Matrix (Industry boundary hurdles across 4 sectors)
      3. Company_Sector_Map (Taxonomy keyword to Sector profile mapping)
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default blank sheet

    if config is None:
        config = create_default_rules_configuration()

    # ----------------------------------------------------
    # Sheet 1: Master_Rule_Definitions (All 18 Checks)
    # ----------------------------------------------------
    ws1: Any = wb.create_sheet(title="Master_Rule_Definitions")
    ws1.views.sheetView[0].showGridLines = True

    headers1 = [
        "Phase", "Check #", "Check Name", "Input Metric", "Logic Type",
        "Default Op", "Default Fail Value", "Sector-Aware?", "Description"
    ]
    ws1.append(headers1)

    for rule in config.master_rules:
        ws1.append([
            rule.phase,
            rule.check_num,
            rule.check_name,
            rule.input_metric,
            rule.logic_type,
            rule.default_op,
            rule.default_fail_value,
            "Yes" if rule.sector_aware else "No",
            rule.description
        ])

    for col in range(1, len(headers1) + 1):
        cell = ws1.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx in range(2, len(config.master_rules) + 2):
        is_alt = (r_idx % 2 == 0)
        for col_idx in range(1, len(headers1) + 1):
            cell = ws1.cell(row=r_idx, column=col_idx)
            cell.font = ROW_FONT
            cell.border = THIN_BORDER
            if is_alt:
                cell.fill = ALT_FILL
            if col_idx in [1, 2, 5, 6, 7, 8]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 9:
                cell.font = NOTE_FONT

    # ----------------------------------------------------
    # Sheet 2: Sector_Boundary_Matrix
    # ----------------------------------------------------
    ws2: Any = wb.create_sheet(title="Sector_Boundary_Matrix")
    ws2.views.sheetView[0].showGridLines = True

    headers2 = ["Sector Profile", "Metric", "Pass_Threshold", "Fail_Threshold", "Critical_Cap", "Operator", "Unit", "Note"]
    ws2.append(headers2)

    rows2 = []
    for sector_key, thresh in config.phase2_matrix.items():
        rows2.extend([
            [thresh.sector.value, "RoCE", f"{thresh.roce_pass_floor}%", f"{thresh.roce_fail_ceiling}%", "N/A", "Range", "%", "Return on Capital Employed (5-yr median)"],
            [thresh.sector.value, "NetDebt_EBITDA", f"{thresh.net_debt_ebitda_pass_ceiling:.1f}x", f"{thresh.net_debt_ebitda_fail_floor:.1f}x", "N/A", "Range", "x", "Net Debt to EBITDA (pass <= ceiling, fail > floor)"],
            [thresh.sector.value, "Interest_Coverage", f"{thresh.interest_coverage_pass_floor:.1f}x", f"{thresh.interest_coverage_fail_ceiling:.1f}x", "N/A", "Range", "x", "EBIT to Finance Cost coverage floor"],
            [thresh.sector.value, "Max_ST_Debt_Pct", f"{thresh.max_st_debt_concern_pct}%", f"{thresh.max_st_debt_concern_pct}%", "N/A", ">", "%", "Short-term debt % of total debt concern threshold"],
            [thresh.sector.value, "CCC_Det", f"{thresh.ccc_deterioration_fail_days:.0f} days", f"{thresh.ccc_deterioration_fail_days:.0f} days", f"{thresh.max_receivable_days_critical_cap:.0f} days", ">", "days", "3-year rise in Cash Conversion Cycle"],
            [thresh.sector.value, "Receivable_Days", f"{thresh.max_receivable_days_critical_cap:.0f} days", f"{thresh.max_receivable_days_critical_cap:.0f} days", f"{thresh.max_receivable_days_critical_cap:.0f} days", ">", "days", "Critical receivable days ceiling"],
        ])

    for row in rows2:
        ws2.append(row)

    for col in range(1, len(headers2) + 1):
        cell = ws2.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx in range(2, len(rows2) + 2):
        is_alt = (r_idx % 2 == 0)
        for col_idx in range(1, len(headers2) + 1):
            cell = ws2.cell(row=r_idx, column=col_idx)
            cell.font = ROW_FONT
            cell.border = THIN_BORDER
            if is_alt:
                cell.fill = ALT_FILL
            if col_idx in [1, 3, 4, 5, 6, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 8:
                cell.font = NOTE_FONT

    # ----------------------------------------------------
    # Sheet 3: Company_Sector_Map
    # ----------------------------------------------------
    ws3: Any = wb.create_sheet(title="Company_Sector_Map")
    ws3.views.sheetView[0].showGridLines = True

    headers3 = ["Industry Keyword", "Sector Profile", "Notes"]
    ws3.append(headers3)

    for item in config.sector_mappings:
        ws3.append([item.keyword, item.sector.value, item.notes or ""])

    for col in range(1, len(headers3) + 1):
        cell = ws3.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx in range(2, len(config.sector_mappings) + 2):
        is_alt = (r_idx % 2 == 0)
        for col_idx in range(1, len(headers3) + 1):
            cell = ws3.cell(row=r_idx, column=col_idx)
            cell.font = ROW_FONT
            cell.border = THIN_BORDER
            if is_alt:
                cell.fill = ALT_FILL
            if col_idx == 2:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 3:
                cell.font = NOTE_FONT

    # ----------------------------------------------------
    # Sheet 4: Phase1_Thresholds (Compatibility Alias)
    # ----------------------------------------------------
    ws4: Any = wb.create_sheet(title="Phase1_Thresholds")
    ws4.views.sheetView[0].showGridLines = True
    headers4 = ["Check #", "Metric", "Fail_Threshold", "Operator", "Sector_Aware?", "Note"]
    ws4.append(headers4)
    rows4 = [
        [2, "Promoter_Pledge", f"{config.phase1.promoter_pledge_fail_pct}%", ">", "No", "Pledge % of promoter holding triggering FAIL"],
        [2, "Promoter_Pledge_Low_Holding_Floor", f"{config.phase1.promoter_pledge_low_holding_floor_pct}%", "<", "No", "Promoter holding floor triggering tighter pledge rule"],
        [2, "Promoter_Pledge_Low_Holding_Fail", f"{config.phase1.promoter_pledge_low_holding_fail_pct}%", ">", "No", "Tighter pledge ceiling when promoter holding < 35%"],
        [2, "Promoter_Pledge_Total_Shares", f"{config.phase1.promoter_pledge_total_shares_fail_pct}%", ">", "No", "Pledged shares as % of total shares triggering FAIL"],
        [3, "RPT_Sales_Purchases", f"{config.phase1.rpt_sales_purchases_fail_pct}%", ">", "No", "RPT sales + purchases as % of revenue"],
        [4, "Contingent_Liabilities", f"{config.phase1.contingent_liabilities_net_worth_fail_pct}%", ">", "Yes", "Total contingent liabilities as % of net worth"],
        [4, "Litigation_Claims", f"{config.phase1.litigation_claims_net_worth_fail_pct}%", ">", "No", "Tax & litigation claims as % of net worth"],
        [5, "CFO_PAT_Ratio", f"{config.phase1.cfo_pat_ratio_fail_floor:.2f}", "<", "No", "5-year cumulative CFO / PAT conversion floor"],
        [6, "Legal_Fee_Surge", f"{config.phase1.legal_fee_surge_fail_pct}%", ">", "No", "YoY legal fee surge triggering FAIL if unexplained"],
        [6, "Legal_Audit_Fee_Multiplier", f"{config.phase1.legal_to_audit_fee_multiplier:.1f}x", ">", "No", "Ratio of legal fees to audit fees triggering FAIL"],
    ]
    for r in rows4:
        ws4.append(r)
    for col in range(1, len(headers4) + 1):
        cell = ws4.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # ----------------------------------------------------
    # Sheet 5: Phase2_Matrix (Compatibility Alias)
    # ----------------------------------------------------
    ws5: Any = wb.create_sheet(title="Phase2_Matrix")
    ws5.views.sheetView[0].showGridLines = True
    ws5.append(headers2)
    for r in rows2:
        ws5.append(r)
    for col in range(1, len(headers2) + 1):
        cell = ws5.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # ----------------------------------------------------
    # Sheet 6: Sector_Mapping (Compatibility Alias)
    # ----------------------------------------------------
    ws6: Any = wb.create_sheet(title="Sector_Mapping")
    ws6.views.sheetView[0].showGridLines = True
    ws6.append(headers3)
    for item in config.sector_mappings:
        ws6.append([item.keyword, item.sector.value, item.notes or ""])
    for col in range(1, len(headers3) + 1):
        cell = ws6.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # ----------------------------------------------------
    # Sheet 7: Phase3_Thresholds
    # ----------------------------------------------------
    ws7: Any = wb.create_sheet(title="Phase3_Thresholds")
    ws7.views.sheetView[0].showGridLines = True
    headers7 = ["Parameter", "Value", "Type", "Description"]
    ws7.append(headers7)

    p3 = config.phase3
    rows7 = [
        ["target_cagr", p3.target_cagr, "float", "Target annualised return hurdle (%)"],
        ["growth_prob_multiplier", p3.growth_prob_multiplier, "float", "Multiplier of historical EPS growth for Miraculous classification"],
        ["growth_probable_margin", p3.growth_probable_margin, "float", "Buffer above historical growth (pp) for Probable classification"],
        ["pe_rerate_miraculous_ceiling", p3.pe_rerate_miraculous_ceiling, "float", "Annual P/E re-rating (%) classified as Miraculous"],
        ["valuation_fair_variance_pct", p3.valuation_fair_variance_pct, "float", "Allowed premium (%) above 5-yr avg to still be FAIR"],
        ["guidance_miss_fatal_years", p3.guidance_miss_fatal_years, "int", "Consecutive guidance misses triggering fatal contradiction"],
        ["single_source_dependency_ceiling_pct", p3.single_source_dependency_ceiling_pct, "float", "Single-source vendor (%) ceiling for Vendor Risk"],
        ["outsourcing_ceiling_pct", p3.outsourcing_ceiling_pct, "float", "Product outsourcing (%) ceiling for Vendor Risk"],
        ["contradiction_fatal_list", ", ".join(p3.contradiction_fatal_list), "list", "Comma-separated contradiction types treated as fatal"],
    ]
    for r in rows7:
        ws7.append(r)

    for col in range(1, len(headers7) + 1):
        cell = ws7.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx in range(2, len(rows7) + 2):
        is_alt = (r_idx % 2 == 0)
        for col_idx in range(1, len(headers7) + 1):
            cell = ws7.cell(row=r_idx, column=col_idx)
            cell.font = ROW_FONT
            cell.border = THIN_BORDER
            if is_alt:
                cell.fill = ALT_FILL
            if col_idx == 4:
                cell.font = NOTE_FONT

    # Auto-fit columns
    for ws in [ws1, ws2, ws3, ws4, ws5, ws6, ws7]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _find_sheet(wb: openpyxl.Workbook, candidates: List[str]) -> Optional[Any]:
    """Finds a worksheet matching any of the candidate names (case-insensitive)."""
    for c in candidates:
        if c in wb.sheetnames:
            return wb[c]
    for name in wb.sheetnames:
        for c in candidates:
            if name.strip().lower() == c.strip().lower():
                return wb[name]
    return None


def parse_rules_config_workbook(
    file_bytes_or_stream: Union[bytes, io.BytesIO, str]
) -> RulesConfiguration:
    """
    Parses an uploaded rules configuration workbook into a strongly typed RulesConfiguration.
    Supports both official baseline schema (Docs/Rules/baseline-engine-implementation.md §1)
    and previous generation schemas for full backwards compatibility:
      - Sheet 1: `Master_Rule_Definitions` or `Phase1_Thresholds`
      - Sheet 2: `Sector_Boundary_Matrix` or `Phase2_Matrix`
      - Sheet 3: `Company_Sector_Map` or `Sector_Mapping`
    """
    if isinstance(file_bytes_or_stream, bytes):
        stream = io.BytesIO(file_bytes_or_stream)
    elif isinstance(file_bytes_or_stream, str):
        stream = open(file_bytes_or_stream, "rb")
    else:
        stream = file_bytes_or_stream

    wb = openpyxl.load_workbook(stream, data_only=True)

    default_cfg = create_default_rules_configuration()

    def _normalize_sector(sec_str: str) -> Optional[Phase2Sector]:
        norm = sec_str.strip().upper().replace(" ", "_").replace("-", "_")
        for s in Phase2Sector:
            if s.value == norm or s.name == norm:
                return s
        if "ASSET" in norm:
            return Phase2Sector.ASSET_LIGHT
        if "CAP" in norm:
            return Phase2Sector.CAP_INTENSIVE
        if "REGULAT" in norm or "INFRA" in norm or "UTILITY" in norm:
            return Phase2Sector.REGULATED_INFRA
        if "STAND" in norm:
            return Phase2Sector.STANDARD
        return None

    # ----------------------------------------------------
    # 1. Parse Sheet 1: Master_Rule_Definitions / Phase1_Thresholds
    # ----------------------------------------------------
    ws1 = _find_sheet(wb, ["Master_Rule_Definitions", "Phase1_Thresholds"])
    if ws1 is None:
        raise ValueError("Invalid Rules Workbook: Missing sheet 'Master_Rule_Definitions' (or 'Phase1_Thresholds')")

    p1_cfg = Phase1RuleConfig()
    p2_rules_cfg = Phase2RuleConfig()
    master_rules_list: List[MasterRuleDefinition] = []

    # Detect header structure of Sheet 1
    header_row = [str(cell.value or '').strip() for cell in ws1[1]]
    is_master_schema = any("Check Name" in h or "Logic Type" in h for h in header_row)

    if is_master_schema:
        # Schema: Phase | Check # | Check Name | Input Metric | Logic Type | Default Op | Default Fail Value | Sector-Aware? | Description
        for row in ws1.iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None or row[1] is None:
                continue
            try:
                phase_num = int(row[0])
                chk_num = int(row[1])
            except (ValueError, TypeError):
                continue

            chk_name = str(row[2] or f"Check {chk_num}").strip()
            metric_name = str(row[3] or "").strip()
            logic_type = str(row[4] or "Numeric").strip()
            default_op = str(row[5] or ">").strip()
            fail_val_str = str(row[6] or "").strip()
            sector_aware_str = str(row[7] or "No").strip().lower()
            sector_aware = sector_aware_str in ["yes", "true", "1"]
            desc = str(row[8]).strip() if len(row) > 8 and row[8] else None

            val_float = _clean_num(fail_val_str)

            # Map to Phase 1 thresholds
            if chk_num == 2 and val_float is not None:
                p1_cfg.promoter_pledge_fail_pct = val_float
            elif chk_num == 3 and val_float is not None:
                p1_cfg.rpt_sales_purchases_fail_pct = val_float
            elif chk_num == 4 and val_float is not None:
                p1_cfg.contingent_liabilities_net_worth_fail_pct = val_float
            elif chk_num == 5 and val_float is not None:
                # CFO/PAT ratio (e.g. 0.80)
                p1_cfg.cfo_pat_ratio_fail_floor = val_float if val_float <= 1.0 else val_float / 100.0
            elif chk_num == 6 and val_float is not None:
                # Exec Stability
                pass
            # Map to Phase 2 non-sector thresholds
            elif chk_num == 8 and val_float is not None:
                p2_rules_cfg.ebitda_margin_var_fail_pct = val_float
            elif chk_num == 13 and fail_val_str:
                p2_rules_cfg.credit_rating_fail_floor = fail_val_str.replace('"', '').replace("'", "")
            elif chk_num == 14 and val_float is not None:
                p2_rules_cfg.loans_advances_net_worth_fail_pct = val_float
            elif chk_num == 15 and val_float is not None:
                p2_rules_cfg.guarantees_net_worth_fail_pct = val_float
            elif chk_num == 17 and val_float is not None:
                p2_rules_cfg.moat_evidence_count_fail_floor = int(val_float)

            master_rules_list.append(MasterRuleDefinition(
                phase=phase_num,
                check_num=chk_num,
                check_name=chk_name,
                input_metric=metric_name,
                logic_type=logic_type,
                default_op=default_op,
                default_fail_value=fail_val_str,
                sector_aware=sector_aware,
                description=desc,
            ))
    else:
        # Legacy key-value Phase1_Thresholds schema
        p1_dict: Dict[str, float] = {}
        for row in ws1.iter_rows(min_row=2, values_only=True):
            if not row or not row[1]:
                continue
            m_name = str(row[1]).strip().lower()
            val = _clean_num(row[2])
            if val is not None:
                p1_dict[m_name] = val

        p1_cfg = Phase1RuleConfig(
            promoter_pledge_fail_pct=p1_dict.get("promoter_pledge", 10.0),
            promoter_pledge_low_holding_floor_pct=p1_dict.get("promoter_pledge_low_holding_floor", 35.0),
            promoter_pledge_low_holding_fail_pct=p1_dict.get("promoter_pledge_low_holding_fail", 5.0),
            promoter_pledge_total_shares_fail_pct=p1_dict.get("promoter_pledge_total_shares", 5.0),
            rpt_sales_purchases_fail_pct=p1_dict.get("rpt_sales_purchases", 10.0),
            contingent_liabilities_net_worth_fail_pct=p1_dict.get("contingent_liabilities", 15.0),
            litigation_claims_net_worth_fail_pct=p1_dict.get("litigation_claims", 10.0),
            cfo_pat_ratio_fail_floor=p1_dict.get("cfo_pat_ratio", 0.80),
            legal_fee_surge_fail_pct=p1_dict.get("legal_fee_surge", 100.0),
            legal_to_audit_fee_multiplier=p1_dict.get("legal_audit_fee_multiplier", 3.0),
        )
    # If Phase1_Thresholds sheet is also present, allow non-default mutations to propagate
    ws_p1_legacy = _find_sheet(wb, ["Phase1_Thresholds"])
    if ws_p1_legacy is not None and ws_p1_legacy != ws1:
        for row in ws_p1_legacy.iter_rows(min_row=2, values_only=True):
            if not row or not row[1]:
                continue
            m_name = str(row[1]).strip().lower()
            val = _clean_num(row[2])
            if val is not None:
                if m_name == "promoter_pledge" and val != 10.0:
                    p1_cfg.promoter_pledge_fail_pct = val
                elif m_name == "promoter_pledge_low_holding_floor" and val != 35.0:
                    p1_cfg.promoter_pledge_low_holding_floor_pct = val
                elif m_name == "promoter_pledge_low_holding_fail" and val != 5.0:
                    p1_cfg.promoter_pledge_low_holding_fail_pct = val
                elif m_name == "promoter_pledge_total_shares" and val != 5.0:
                    p1_cfg.promoter_pledge_total_shares_fail_pct = val
                elif m_name == "rpt_sales_purchases" and val != 10.0:
                    p1_cfg.rpt_sales_purchases_fail_pct = val
                elif m_name == "contingent_liabilities" and val != 15.0:
                    p1_cfg.contingent_liabilities_net_worth_fail_pct = val
                elif m_name == "litigation_claims" and val != 10.0:
                    p1_cfg.litigation_claims_net_worth_fail_pct = val
                elif m_name == "cfo_pat_ratio" and val != 0.80:
                    p1_cfg.cfo_pat_ratio_fail_floor = val if val <= 1.0 else val / 100.0
                elif m_name == "legal_fee_surge" and val != 100.0:
                    p1_cfg.legal_fee_surge_fail_pct = val
                elif m_name == "legal_audit_fee_multiplier" and val != 3.0:
                    p1_cfg.legal_to_audit_fee_multiplier = val

    if not master_rules_list:
        master_rules_list = default_cfg.master_rules

    # ----------------------------------------------------
    # 2. Parse Sheet 2: Sector_Boundary_Matrix / Phase2_Matrix
    # ----------------------------------------------------
    ws2 = _find_sheet(wb, ["Sector_Boundary_Matrix", "Phase2_Matrix"])
    if ws2 is None:
        raise ValueError("Invalid Rules Workbook: Missing sheet 'Sector_Boundary_Matrix' (or 'Phase2_Matrix')")

    matrix_raw: Dict[str, Dict[str, Dict[str, float]]] = {}

    for row in ws2.iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        sec_enum = _normalize_sector(str(row[0]))
        if not sec_enum:
            continue
        metric = str(row[1]).strip().lower().replace(" ", "_")
        pass_val = _clean_num(row[2])
        fail_val = _clean_num(row[3])

        sec_key = sec_enum.value
        if sec_key not in matrix_raw:
            matrix_raw[sec_key] = {}
        matrix_raw[sec_key][metric] = {
            "pass": pass_val if pass_val is not None else 0.0,
            "fail": fail_val if fail_val is not None else 0.0,
        }

    # If Phase2_Matrix sheet is also present, allow it to override Phase 2 metrics
    ws_p2_legacy = _find_sheet(wb, ["Phase2_Matrix"])
    if ws_p2_legacy is not None and ws_p2_legacy != ws2:
        for row in ws_p2_legacy.iter_rows(min_row=2, values_only=True):
            if not row or not row[0] or not row[1]:
                continue
            sec_enum = _normalize_sector(str(row[0]))
            if not sec_enum:
                continue
            metric = str(row[1]).strip().lower().replace(" ", "_")
            pass_val = _clean_num(row[2])
            fail_val = _clean_num(row[3])

            sec_key = sec_enum.value
            if sec_key not in matrix_raw:
                matrix_raw[sec_key] = {}
            matrix_raw[sec_key][metric] = {
                "pass": pass_val if pass_val is not None else 0.0,
                "fail": fail_val if fail_val is not None else 0.0,
            }

    matrix_final: Dict[str, SectorThresholdConfig] = {}

    for sec in Phase2Sector:
        sec_key = sec.value
        def_sec = default_cfg.phase2_matrix.get(sec_key)
        sec_data = matrix_raw.get(sec_key, {})

        roce_d = sec_data.get("roce", {})
        debt_d = sec_data.get("netdebt_ebitda", {}) or sec_data.get("net_debt_ebitda", {})
        int_d = sec_data.get("interest_coverage", {})
        st_d = sec_data.get("max_st_debt_pct", {}) or sec_data.get("st_debt", {})
        ccc_d = sec_data.get("ccc_det", {}) or sec_data.get("ccc_deterioration_days", {}) or sec_data.get("ccc_deterioration", {})
        rec_d = sec_data.get("receivable_days", {}) or sec_data.get("max_receivable_days", {})

        matrix_final[sec_key] = SectorThresholdConfig(
            sector=sec,
            roce_pass_floor=roce_d.get("pass", def_sec.roce_pass_floor if def_sec else 15.0),
            roce_fail_ceiling=roce_d.get("fail", def_sec.roce_fail_ceiling if def_sec else 10.0),
            net_debt_ebitda_pass_ceiling=debt_d.get("pass", def_sec.net_debt_ebitda_pass_ceiling if def_sec else 2.0),
            net_debt_ebitda_fail_floor=debt_d.get("fail", def_sec.net_debt_ebitda_fail_floor if def_sec else 3.0),
            interest_coverage_pass_floor=int_d.get("pass", def_sec.interest_coverage_pass_floor if def_sec else 4.0),
            interest_coverage_fail_ceiling=int_d.get("fail", def_sec.interest_coverage_fail_ceiling if def_sec else 2.0),
            max_st_debt_concern_pct=st_d.get("fail", def_sec.max_st_debt_concern_pct if def_sec else 20.0),
            ccc_deterioration_fail_days=ccc_d.get("fail", def_sec.ccc_deterioration_fail_days if def_sec else 60.0),
            max_receivable_days_critical_cap=rec_d.get("fail", def_sec.max_receivable_days_critical_cap if def_sec else 90.0),
        )

    # ----------------------------------------------------
    # 3. Parse Sheet 3: Company_Sector_Map / Sector_Mapping
    # ----------------------------------------------------
    ws3 = _find_sheet(wb, ["Company_Sector_Map", "Sector_Mapping"])
    if ws3 is None:
        raise ValueError("Invalid Rules Workbook: Missing sheet 'Company_Sector_Map' (or 'Sector_Mapping')")

    mappings: List[SectorKeywordItem] = []

    for row in ws3.iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        kw = str(row[0]).strip()
        sec_enum = _normalize_sector(str(row[1]))
        notes = str(row[2]).strip() if len(row) > 2 and row[2] else None
        if kw and sec_enum:
            mappings.append(SectorKeywordItem(keyword=kw, sector=sec_enum, notes=notes))

    if not mappings:
        mappings = default_cfg.sector_mappings

    # ----------------------------------------------------
    # 4. Parse Sheet 7: Phase3_Thresholds (optional)
    # ----------------------------------------------------
    p3_cfg = Phase3RuleConfig()
    ws_p3 = _find_sheet(wb, ["Phase3_Thresholds"])
    if ws_p3 is not None:
        p3_data: Dict[str, Any] = {}
        for row in ws_p3.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            param_name = str(row[0]).strip()
            param_val = row[1] if len(row) > 1 else None
            if param_val is not None:
                p3_data[param_name] = param_val

        def _get_float(key: str, default: float) -> float:
            v = p3_data.get(key)
            if v is None:
                return default
            parsed = _clean_num(v)
            return parsed if parsed is not None else default

        def _get_int(key: str, default: int) -> int:
            v = p3_data.get(key)
            if v is None:
                return default
            parsed = _clean_num(v)
            return int(parsed) if parsed is not None else default

        fatal_list_raw = p3_data.get("contradiction_fatal_list", "")
        if isinstance(fatal_list_raw, str) and fatal_list_raw.strip():
            fatal_list = [s.strip().upper() for s in fatal_list_raw.split(",") if s.strip()]
        else:
            fatal_list = p3_cfg.contradiction_fatal_list

        p3_cfg = Phase3RuleConfig(
            target_cagr=_get_float("target_cagr", p3_cfg.target_cagr),
            growth_prob_multiplier=_get_float("growth_prob_multiplier", p3_cfg.growth_prob_multiplier),
            growth_probable_margin=_get_float("growth_probable_margin", p3_cfg.growth_probable_margin),
            pe_rerate_miraculous_ceiling=_get_float("pe_rerate_miraculous_ceiling", p3_cfg.pe_rerate_miraculous_ceiling),
            valuation_fair_variance_pct=_get_float("valuation_fair_variance_pct", p3_cfg.valuation_fair_variance_pct),
            guidance_miss_fatal_years=_get_int("guidance_miss_fatal_years", p3_cfg.guidance_miss_fatal_years),
            single_source_dependency_ceiling_pct=_get_float("single_source_dependency_ceiling_pct", p3_cfg.single_source_dependency_ceiling_pct),
            outsourcing_ceiling_pct=_get_float("outsourcing_ceiling_pct", p3_cfg.outsourcing_ceiling_pct),
            contradiction_fatal_list=fatal_list,
        )

    return RulesConfiguration(
        version="1.0.0",
        source="EXCEL_UPLOAD",
        description="Master Rules Configuration loaded via Excel upload",
        master_rules=master_rules_list,
        phase1=p1_cfg,
        phase2_rules=p2_rules_cfg,
        phase2_matrix=matrix_final,
        sector_mappings=mappings,
        phase3=p3_cfg,
    )
