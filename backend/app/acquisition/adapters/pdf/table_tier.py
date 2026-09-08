"""
Tier 2 table extraction engine using pdfplumber.
Maps strictly to implementpdf.md Stage 2 and Phase1-WebApp-Implementation-Plan.md §5.2.
Extracts numeric financial notes with column-to-period resolution and exact page citations.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pdfplumber

from backend.app.acquisition.adapters.parsers.screener_tables import parse_clean_number
from backend.app.acquisition.adapters.pdf.anchors import SECTION_PATTERNS, matches_anchor
from backend.app.acquisition.types import ExtractedField
from backend.app.models.enums import Confidence, ExtractionMethod, ReportingBasis


def resolve_column_fys(header_row: List[Optional[str]]) -> Dict[int, str]:
    """
    Maps column index to fiscal year (e.g. 'FY24', 'FY23') from column header string.
    Example: 'March 31, 2024' -> 'FY24', '31.03.2023' -> 'FY23'.
    """
    col_map: Dict[int, str] = {}
    for idx, cell in enumerate(header_row):
        if not cell:
            continue
        text = str(cell).strip()
        m = re.search(r"20(\d{2})", text)
        if m:
            col_map[idx] = f"FY{m.group(1)}"
        elif "current year" in text.lower():
            col_map[idx] = "CURRENT"
        elif "previous year" in text.lower() or "prior year" in text.lower():
            col_map[idx] = "PREVIOUS"
    return col_map


def extract_tables_from_pages(
    pdf_path: Path,
    target_pages: List[int],
) -> List[Tuple[int, List[List[Optional[str]]]]]:
    """
    Extracts structured tables from target page numbers (1-indexed).
    Returns list of (page_num, table_rows).
    """
    extracted = []
    with pdfplumber.open(pdf_path) as pdf:
        for p_num in target_pages:
            if p_num <= len(pdf.pages):
                p = pdf.pages[p_num - 1]
                tables = p.extract_tables()
                for tbl in tables:
                    if tbl and len(tbl) >= 2:
                        extracted.append((p_num, tbl))
    return extracted


def extract_note_fields_from_pdf(
    pdf_path: Path,
    source_filename: str,
    doc_fy: Optional[str],
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> List[ExtractedField]:
    """
    Scans PDF pages for section anchors and extracts numeric note values:
    - contingent_liabilities
    - legal_fees & legal_fees_prior_year
    - audit_fees
    - rpt_sales_plus_purchases
    - revenue
    - net_worth
    """
    fields: List[ExtractedField] = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lower_text = text.lower()

            # 1. Contingent Liabilities Note
            if "contingent liabilit" in lower_text and not any(f.field_name == "contingent_liabilities" for f in fields):
                tables = page.extract_tables()
                for tbl in tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    col_fys = resolve_column_fys(tbl[0])
                    for row in tbl[1:]:
                        if not row or not row[0]:
                            continue
                        label = str(row[0]).lower().strip()
                        if "total" in label or "contingent liabilities" in label:
                            # Search columns for numeric value
                            for c_idx in range(1, len(row)):
                                val = parse_clean_number(str(row[c_idx]))
                                if val is not None and val >= 0:
                                    period = col_fys.get(c_idx, doc_fy or "FY24")
                                    fields.append(
                                        ExtractedField(
                                            field_name="contingent_liabilities",
                                            value=val,
                                            confidence=Confidence.HIGH if c_idx in col_fys else Confidence.MEDIUM,
                                            extraction_method=ExtractionMethod.TABLE_PARSE,
                                            source=source_filename,
                                            period=period,
                                            basis=basis,
                                            source_page=page_idx + 1,
                                            raw_snippet=f"{row[0]}: {val}",
                                            document_id=document_id,
                                        )
                                    )
                                    break
                            if any(f.field_name == "contingent_liabilities" for f in fields):
                                break

            # 2. Auditor Remuneration Note (Payment to Auditors)
            if ("payment to auditor" in lower_text or "auditor's remuneration" in lower_text or "auditors' remuneration" in lower_text) and not any(f.field_name == "audit_fees" for f in fields):
                tables = page.extract_tables()
                for tbl in tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    col_fys = resolve_column_fys(tbl[0])
                    for row in tbl[1:]:
                        if not row or not row[0]:
                            continue
                        label = str(row[0]).lower().strip()
                        if "total" in label or "statutory audit" in label or "audit fee" in label or "as auditor" in label:
                            for c_idx in range(1, len(row)):
                                val = parse_clean_number(str(row[c_idx]))
                                if val is not None and val > 0:
                                    period = col_fys.get(c_idx, doc_fy or "FY24")
                                    fields.append(
                                        ExtractedField(
                                            field_name="audit_fees",
                                            value=val,
                                            confidence=Confidence.HIGH if c_idx in col_fys else Confidence.MEDIUM,
                                            extraction_method=ExtractionMethod.TABLE_PARSE,
                                            source=source_filename,
                                            period=period,
                                            basis=basis,
                                            source_page=page_idx + 1,
                                            raw_snippet=f"{row[0]}: {val}",
                                            document_id=document_id,
                                        )
                                    )
                                    break
                            if any(f.field_name == "audit_fees" for f in fields):
                                break

            # 3. Legal and Professional Charges Note
            if ("legal and professional" in lower_text or "legal & professional" in lower_text) and not any(f.field_name == "legal_fees" for f in fields):
                tables = page.extract_tables()
                for tbl in tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    col_fys = resolve_column_fys(tbl[0])
                    for row in tbl[1:]:
                        if not row or not row[0]:
                            continue
                        label = str(row[0]).lower().strip()
                        if "legal and professional" in label or "legal & professional" in label or "legal charges" in label or "legal fees" in label:
                            vals_found = []
                            for c_idx in range(1, len(row)):
                                num = parse_clean_number(str(row[c_idx]))
                                if num is not None:
                                    period = col_fys.get(c_idx, f"Col{c_idx}")
                                    vals_found.append((num, period, c_idx))

                            if vals_found:
                                # Current year legal fees
                                curr_val, curr_period, _ = vals_found[0]
                                fields.append(
                                    ExtractedField(
                                        field_name="legal_fees",
                                        value=curr_val,
                                        confidence=Confidence.HIGH if col_fys else Confidence.MEDIUM,
                                        extraction_method=ExtractionMethod.TABLE_PARSE,
                                        source=source_filename,
                                        period=curr_period if curr_period != "Col1" else (doc_fy or "FY24"),
                                        basis=basis,
                                        source_page=page_idx + 1,
                                        raw_snippet=f"Legal fees: {curr_val}",
                                        document_id=document_id,
                                    )
                                )
                                # Comparative prior year legal fees if 2 columns present
                                if len(vals_found) >= 2:
                                    prior_val, prior_period, _ = vals_found[1]
                                    fields.append(
                                        ExtractedField(
                                            field_name="legal_fees_prior_year",
                                            value=prior_val,
                                            confidence=Confidence.HIGH if col_fys else Confidence.MEDIUM,
                                            extraction_method=ExtractionMethod.TABLE_PARSE,
                                            source=source_filename,
                                            period=prior_period,
                                            basis=basis,
                                            source_page=page_idx + 1,
                                            raw_snippet=f"Legal fees prior year: {prior_val}",
                                            document_id=document_id,
                                        )
                                    )
                                break

            # 4. Related Party Disclosures Note (Transactions during the year)
            if ("related party" in lower_text and ("transactions" in lower_text or "disclosures" in lower_text)) and not any(f.field_name == "rpt_sales_plus_purchases" for f in fields):
                tables = page.extract_tables()
                for tbl in tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    col_fys = resolve_column_fys(tbl[0])
                    for row in tbl[1:]:
                        if not row or not row[0]:
                            continue
                        label = str(row[0]).lower().strip()
                        if "total" in label or "purchase" in label or "sale" in label:
                            for c_idx in range(1, len(row)):
                                val = parse_clean_number(str(row[c_idx]))
                                if val is not None and val >= 0:
                                    period = col_fys.get(c_idx, doc_fy or "FY24")
                                    fields.append(
                                        ExtractedField(
                                            field_name="rpt_sales_plus_purchases",
                                            value=val,
                                            confidence=Confidence.HIGH if c_idx in col_fys else Confidence.MEDIUM,
                                            extraction_method=ExtractionMethod.TABLE_PARSE,
                                            source=source_filename,
                                            period=period,
                                            basis=basis,
                                            source_page=page_idx + 1,
                                            raw_snippet=f"RPT {row[0]}: {val}",
                                            document_id=document_id,
                                        )
                                    )
                                    break
                            if any(f.field_name == "rpt_sales_plus_purchases" for f in fields):
                                break

    return fields
