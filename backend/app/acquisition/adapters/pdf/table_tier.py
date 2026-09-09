"""
Tier 2 table extraction engine using pdfplumber.
Maps strictly to implementpdf.md Stage 2 and Phase1-WebApp-Implementation-Plan.md §5.2.
Extracts numeric financial notes with column-to-period resolution and exact page citations.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import pdfplumber

from backend.app.acquisition.adapters.parsers.screener_tables import parse_clean_number
from backend.app.acquisition.adapters.pdf.anchors import (
    SECTION_PATTERNS,
    locate_basis_page_range,
    matches_anchor,
    normalize_quotes,
)
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
    line_tier_fields = {
        "contingent_liabilities",
        "audit_fees",
        "legal_fees",
    }

    with pdfplumber.open(pdf_path) as pdf:
        page_texts = [p.extract_text() or "" for p in pdf.pages]
        total_pages = len(pdf.pages)

        # Annual reports repeat every note for both bases. Scan only the section
        # matching the document's declared basis, so a consolidated document does
        # not silently return standalone numbers.
        basis_range = locate_basis_page_range(page_texts, basis.value)
        start, end = basis_range if basis_range else (0, total_pages)

        for page_idx in range(start, end):
            page = pdf.pages[page_idx]
            text = page_texts[page_idx]
            lower_text = normalize_quotes(text).lower()

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
                                            page=page_idx + 1,
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
                                            page=page_idx + 1,
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
                                        page=page_idx + 1,
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
                                            page=page_idx + 1,
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
                                            page=page_idx + 1,
                                            raw_snippet=f"RPT {row[0]}: {val}",
                                            document_id=document_id,
                                        )
                                    )
                                    break
                            if any(f.field_name == "rpt_sales_plus_purchases" for f in fields):
                                break

            # 5. Line tier: notes typeset without ruling lines yield no usable
            #    tables above, so read their values straight from the text.
            still_missing = line_tier_fields - {f.field_name for f in fields}
            if still_missing:
                fields.extend(
                    extract_line_fields_from_page(
                        page_text=text,
                        page_no=page_idx + 1,
                        wanted=still_missing,
                        source_filename=source_filename,
                        doc_fy=doc_fy,
                        basis=basis,
                        document_id=document_id,
                    )
                )

    return fields

# ---------------------------------------------------------------------------
# Line tier
#
# Indian annual report notes are typeset without ruling lines, so pdfplumber's
# table detection returns either nothing or a single mangled column for them.
# The values are however perfectly legible in the extracted text: a period
# header row, then one label per line with its columns as trailing numbers.
# This tier reads that shape directly and backs up the table tier above.
# ---------------------------------------------------------------------------

_YEAR_TOKEN = re.compile(r"(?<!\d)20(\d{2})(?!\d)")
_PERIOD_HINT = re.compile(
    r"as at|year ended|period ended|march|january|february|april|may|june|july|"
    r"august|september|october|november|december",
    re.IGNORECASE,
)
_NEW_NOTE = re.compile(r"^\s*(?:note\s+)?\d+(?:\.\d+)+[A-Za-z]?[.\s]")
_FOOTNOTE = re.compile(r"^\s*[*#†‡]")

# Ordered label patterns per field: the first pattern that yields numbers wins,
# so a note total is preferred over one of its components.
_LINE_LABELS: Dict[str, List[str]] = {
    "audit_fees": [
        r"auditor'?s'? remuneration",
        r"auditor remuneration",
        r"remuneration to auditors?",
        r"payment to auditors?",
        r"statutory audit",
    ],
    "legal_fees": [
        r"legal (?:and|&) professional",
        r"legal charges",
        r"legal fees",
    ],
}


def _period_columns(lines: List[str], anchor_idx: int) -> List[str]:
    """
    Reads the column period labels ('March 31, 2026  March 31, 2025') from the
    header row governing `anchor_idx`. Returns ordered FY labels, e.g. FY26, FY25.
    """
    best: List[str] = []
    for idx, line in enumerate(lines):
        years = _YEAR_TOKEN.findall(line)
        if len(years) < 2 or not _PERIOD_HINT.search(line):
            continue
        labels = [f"FY{y}" for y in years]
        if idx <= anchor_idx or not best:
            best = labels
    return best


def _is_period_header(line: str) -> bool:
    return bool(_YEAR_TOKEN.search(line) and _PERIOD_HINT.search(line))


def _trailing_numbers(line: str, max_count: int) -> List[float]:
    """
    Reads the numeric columns off the end of a note line, stopping at the first
    token that is not a number so prose and footnote markers are excluded.
    A bare dash is the reports' notation for nil.
    """
    if max_count <= 0 or _is_period_header(line):
        return []
    values: List[float] = []
    for token in reversed(line.split()):
        if token in {"-", "--", "—", "–", "−"}:
            values.append(0.0)
        else:
            parsed = parse_clean_number(token)
            if parsed is None:
                break
            values.append(parsed)
        if len(values) >= max_count:
            break
    return list(reversed(values))


def _label_of(line: str, values: List[float]) -> str:
    tokens = line.split()
    label = " ".join(tokens[: len(tokens) - len(values)]).strip()
    return label


def _note_block(lines: List[str], anchor_idx: int, max_lines: int = 40) -> List[str]:
    """Returns the lines belonging to the note starting at `anchor_idx`."""
    block = []
    for line in lines[anchor_idx + 1 : anchor_idx + 1 + max_lines]:
        if _NEW_NOTE.match(line) or _FOOTNOTE.match(line):
            break
        block.append(line)
    return block


def _make_field(
    field_name: str,
    value: float,
    period: str,
    confidence: Confidence,
    snippet: str,
    page_no: int,
    source_filename: str,
    basis: ReportingBasis,
    document_id: Optional[str],
) -> ExtractedField:
    return ExtractedField(
        field_name=field_name,
        value=value,
        confidence=confidence,
        extraction_method=ExtractionMethod.TABLE_PARSE,
        source=source_filename,
        period=period,
        basis=basis,
        page=page_no,
        raw_snippet=snippet,
        document_id=document_id,
    )


def extract_line_fields_from_page(
    page_text: str,
    page_no: int,
    wanted: Set[str],
    source_filename: str,
    doc_fy: Optional[str],
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> List[ExtractedField]:
    """
    Extracts the requested note fields from one page of borderless note text.
    """
    text = normalize_quotes(page_text or "")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    fields: List[ExtractedField] = []
    lower_lines = [ln.lower() for ln in lines]

    def periods_for(idx: int) -> List[str]:
        cols = _period_columns(lines, idx)
        return cols or [doc_fy or "FY24"]

    # 1. Single-label notes: audit fees and legal & professional charges.
    for field_name in ("audit_fees", "legal_fees"):
        if field_name not in wanted:
            continue
        for pattern in _LINE_LABELS[field_name]:
            hit = next((i for i, ln in enumerate(lower_lines) if re.search(pattern, ln)), None)
            if hit is None:
                continue
            cols = periods_for(hit)
            values = _trailing_numbers(lines[hit], len(cols))
            if not values or not _label_of(lines[hit], values):
                continue
            confidence = Confidence.HIGH if len(cols) >= 2 else Confidence.MEDIUM
            fields.append(
                _make_field(
                    field_name, values[0], cols[0], confidence,
                    f"{_label_of(lines[hit], values)}: {values[0]}",
                    page_no, source_filename, basis, document_id,
                )
            )
            if field_name == "legal_fees" and len(values) >= 2 and len(cols) >= 2:
                fields.append(
                    _make_field(
                        "legal_fees_prior_year", values[1], cols[1], confidence,
                        f"{_label_of(lines[hit], values)} (prior year): {values[1]}",
                        page_no, source_filename, basis, document_id,
                    )
                )
            break

    # 2. Contingent liabilities: use the note's total row, or sum its claim rows
    #    when the note only lists components (the common case).
    if "contingent_liabilities" in wanted:
        anchor = next(
            (i for i, ln in enumerate(lower_lines) if "contingent liabilit" in ln),
            None,
        )
        if anchor is not None:
            cols = periods_for(anchor)
            rows: List[Tuple[str, List[float]]] = []
            total_row: Optional[Tuple[str, List[float]]] = None
            for line in _note_block(lines, anchor):
                values = _trailing_numbers(line, len(cols))
                if len(values) != len(cols):
                    continue
                label = _label_of(line, values)
                if not label or not re.search(r"[A-Za-z]", label):
                    continue
                if re.match(r"^\s*total\b", label, re.IGNORECASE):
                    total_row = (label, values)
                    break
                rows.append((label, values))

            if total_row:
                label, values = total_row
                fields.append(
                    _make_field(
                        "contingent_liabilities", values[0], cols[0], Confidence.HIGH,
                        f"{label}: {values[0]}", page_no, source_filename, basis, document_id,
                    )
                )
            elif rows:
                total = sum(v[0] for _, v in rows)
                detail = "; ".join(f"{label}: {v[0]}" for label, v in rows)
                fields.append(
                    _make_field(
                        "contingent_liabilities", total, cols[0], Confidence.MEDIUM,
                        f"Sum of {len(rows)} claim lines = {total} ({detail})"[:300],
                        page_no, source_filename, basis, document_id,
                    )
                )

    return fields
