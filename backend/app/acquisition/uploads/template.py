"""
Dynamic Workbook Template Generator for Phase 1 Gatekeeper.
Generates an analyst workbook template directly from FIELD_COVERAGE_MATRIX.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §5A.2.
"""

import io
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from backend.app.models.coverage import FIELD_COVERAGE_MATRIX


def generate_workbook_template_bytes() -> bytes:
    """
    Generates Excel bytes for the analyst workbook template.
    Header columns: field_name | value | source | period | basis | notes
    Pre-populated with all CompanyInput fields from FIELD_COVERAGE_MATRIX.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Phase 1 Inputs"

    # Styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    meta_font = Font(name="Calibri", size=10, color="475569")
    bold_font = Font(name="Calibri", size=10, bold=True)

    headers = ["field_name", "value", "source", "period", "basis", "notes"]
    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[1].height = 24

    # Populate rows from FIELD_COVERAGE_MATRIX
    # Exclude synthetic / purely orchestrator fields (as_of_date, ticker, provenance, company_type)
    excluded = {"as_of_date", "ticker", "provenance", "company_type"}

    row_num = 2
    for field_name, meta in FIELD_COVERAGE_MATRIX.items():
        if field_name in excluded:
            continue

        check_str = f"Check {meta['check']}" if meta.get("check") else "Structural"
        basis_req = "CONSOLIDATED / STANDALONE" if meta.get("basis_required") else "NOT_APPLICABLE"
        notes = f"{check_str} | Sourced from: {meta['source']}"

        ws.append([
            field_name,
            "",  # value left empty for user
            "",  # source left empty for user
            "FY24" if meta.get("basis_required") else "",
            basis_req,
            notes,
        ])

        ws.cell(row=row_num, column=1).font = bold_font
        ws.cell(row=row_num, column=5).font = meta_font
        ws.cell(row=row_num, column=6).font = meta_font
        row_num += 1

    # Adjust column widths
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 24
    ws.column_dimensions["F"].width = 45

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
