"""
Tier 2 table extraction engine using pdfplumber.
Implements chunkrule-v3.md §3b (Note-Unit Chunking) and §3c (Row/Column Selection).
Optimized for v4: Support for party-wise RPT summing and detailed contingent liability breakdown.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, NamedTuple
import pdfplumber

from backend.app.acquisition.adapters.parsers.screener_tables import parse_clean_number
from backend.app.acquisition.adapters.pdf.anchors import (
    locate_basis_page_range,
    normalize_quotes,
)
from backend.app.acquisition.adapters.pdf.units import apply_unit_normalization, build_unit_map
from backend.app.acquisition.types import ExtractedField
from backend.app.models.enums import Confidence, ExtractionMethod, ReportingBasis

class LineInfo(NamedTuple):
    page_num: int
    text: str

class NoteUnit(NamedTuple):
    key: Tuple[int, int]
    title: str
    start_line_idx: int
    end_line_idx: int
    start_page: int

# Regex for Note headers: "37 OTHER EXPENSES", "39.2 : Contingent Liabilities", "2.33 Other expenses"
_NOTE_HEADER_RE = re.compile(r"^\s*(\d{1,3})(?:\.(\d{1,3}))?\s*[:.]?\s+([A-Z].*)$")
_FOOTNOTE_MARKERS = {"*", "$", "^", "#", "†", "‡"}

def resolve_column_fys(header_row: List[Optional[str]]) -> Dict[int, str]:
    col_map: Dict[int, str] = {}
    for idx, cell in enumerate(header_row):
        if not cell: continue
        text = str(cell).strip()
        m = re.search(r"20(\d{2})", text)
        if m:
            col_map[idx] = f"FY{m.group(1)}"
        elif "current year" in text.lower():
            col_map[idx] = "CURRENT"
        elif "previous year" in text.lower() or "prior year" in text.lower():
            col_map[idx] = "PREVIOUS"
    return col_map

def segment_notes(flattened_lines: List[LineInfo]) -> List[NoteUnit]:
    """
    Implements chunkrule-v3.md §3b: Note-Unit Chunking.
    """
    candidates = []
    for idx, line in enumerate(flattened_lines):
        m = _NOTE_HEADER_RE.match(line.text)
        if m:
            major = int(m.group(1))
            minor = int(m.group(2)) if m.group(2) else 0
            candidates.append({
                "key": (major, minor),
                "title": m.group(3),
                "idx": idx,
                "page": line.page_num
            })

    if not candidates:
        return []

    best_run = []
    current_run = []
    for c in candidates:
        if not current_run or c["key"] >= current_run[-1]["key"]:
            current_run.append(c)
        else:
            if len(current_run) > len(best_run):
                best_run = current_run
            current_run = [c]
    if len(current_run) > len(best_run):
        best_run = current_run

    collapsed = []
    for c in best_run:
        if collapsed and collapsed[-1].key == c["key"]:
            continue
        collapsed.append(NoteUnit(
            key=c["key"],
            title=c["title"],
            start_line_idx=c["idx"],
            end_line_idx=0,
            start_page=c["page"]
        ))

    result = []
    for i in range(len(collapsed)):
        start = collapsed[i].start_line_idx
        end = len(flattened_lines) if i == len(collapsed) - 1 else collapsed[i+1].start_line_idx
        result.append(collapsed[i]._replace(end_line_idx=end))

    return result

def _get_trailing_numbers(text: str) -> List[float]:
    """Helper to extract trailing numbers from a line."""
    tokens = text.split()
    nums = []
    for token in reversed(tokens):
        if token in {"-", "--", "—", "–", "−"}:
            nums.append(0.0)
        else:
            p = parse_clean_number(token)
            if p is None: break
            nums.append(p)
    return list(reversed(nums))

def extract_value_from_note(
    note_unit: NoteUnit,
    flattened_lines: List[LineInfo],
    anchor_text: str,
    field_name: str,
    doc_fy: Optional[str],
    basis: ReportingBasis,
    source_filename: str,
    document_id: Optional[str],
) -> List[ExtractedField]:
    """
    Implements chunkrule-v3.md §3c: Row and Column Selection.
    Optimized for v4: Support for party-wise RPT summing and contingent liability breakdowns.
    """
    lines = flattened_lines[note_unit.start_line_idx : note_unit.end_line_idx]
    is_header = anchor_text.lower() in note_unit.title.lower()
    
    target_row_idx = -1
    for idx, line in enumerate(lines):
        if anchor_text.lower() in line.text.lower():
            target_row_idx = idx
            break
    
    if target_row_idx == -1:
        return []

    search_lines = lines[target_row_idx:]
    value_row = None
    for idx, line in enumerate(search_lines):
        txt = line.text.strip()
        if not txt: continue
        if any(txt.startswith(m) for m in _FOOTNOTE_MARKERS):
            break
        
        if is_header:
            if "total" in txt.lower():
                value_row = line
                break
        else:
            nums = _get_trailing_numbers(txt)
            if nums:
                value_row = line
                break
    
    # --- v4 Optimization: Party-wise RPT Summing ---
    if field_name == "rpt_sales_plus_purchases" and not value_row:
        sum_val = 0.0
        found_any = False
        for line in lines:
            nums = _get_trailing_numbers(line.text)
            if nums:
                sum_val += nums[0]
                found_any = True
        if found_any:
            return [ExtractedField(
                field_name=field_name,
                value=sum_val,
                confidence=Confidence.MEDIUM,
                extraction_method=ExtractionMethod.TABLE_PARSE,
                source=source_filename,
                period=doc_fy or "FY24",
                basis=basis,
                page=note_unit.start_page,
                raw_snippet=f"Sum of party-wise rows: {sum_val}",
                document_id=document_id,
            )]

    if not value_row:
        return []

    nums = _get_trailing_numbers(value_row.text)
    if not nums:
        return []

    val = nums[0]
    period = doc_fy or "FY24"
    
    return [ExtractedField(
        field_name=field_name,
        value=val,
        confidence=Confidence.HIGH if is_header else Confidence.MEDIUM,
        extraction_method=ExtractionMethod.TABLE_PARSE,
        source=source_filename,
        period=period,
        basis=basis,
        page=value_row.page_num,
        raw_snippet=f"{value_row.text}: {val}",
        document_id=document_id,
    )]

def extract_contingent_breakdown(
    note_unit: NoteUnit,
    flattened_lines: List[LineInfo],
    doc_fy: Optional[str],
    basis: ReportingBasis,
    source_filename: str,
    document_id: Optional[str],
) -> List[ExtractedField]:
    """
    Implements chunkrule-v3.md §2 for litigation_claims_exposure and routine_guarantee_exposure.
    """
    lines = flattened_lines[note_unit.start_line_idx : note_unit.end_line_idx]
    
    litigation_sum = 0.0
    routine_sum = 0.0
    
    litigation_patterns = ["claims against the company not acknowledged", "disputed", "demand raised", "contested"]
    routine_patterns = ["bank guarantee", "letter of credit", "bills discounted"]
    
    for line in lines:
        nums = _get_trailing_numbers(line.text)
        if not nums: continue
        val = nums[0]
        txt = line.text.lower()
        
        if any(p in txt for p in litigation_patterns):
            litigation_sum += val
        elif any(p in txt for p in routine_patterns):
            routine_sum += val
            
    return [
        ExtractedField(
            field_name="litigation_claims_exposure",
            value=litigation_sum,
            confidence=Confidence.MEDIUM,
            extraction_method=ExtractionMethod.TABLE_PARSE,
            source=source_filename,
            period=doc_fy or "FY24",
            basis=basis,
            page=note_unit.start_page,
            raw_snippet=f"Sum of litigation claims: {litigation_sum}",
            document_id=document_id,
        ),
        ExtractedField(
            field_name="routine_guarantee_exposure",
            value=routine_sum,
            confidence=Confidence.MEDIUM,
            extraction_method=ExtractionMethod.TABLE_PARSE,
            source=source_filename,
            period=doc_fy or "FY24",
            basis=basis,
            page=note_unit.start_page,
            raw_snippet=f"Sum of routine guarantees: {routine_sum}",
            document_id=document_id,
        ),
    ]

def extract_note_fields_from_pdf(
    pdf_path: Path,
    source_filename: str,
    doc_fy: Optional[str],
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> List[ExtractedField]:
    """
    Scans PDF using Note-Unit chunking (chunkrule-v3.md).
    """
    fields: List[ExtractedField] = []
    TARGETS = {
        "contingent_liabilities": ["contingent liabilit", "claims against the company not acknowledged"],
        "audit_fees": ["payment to auditors", "auditor's remuneration", "remuneration to auditors", "auditor remuneration", "statutory audit"],
        "legal_fees": ["legal and professional", "legal fees", "legal charges"],
        "rpt_sales_plus_purchases": ["related party transactions", "related party disclosures", "Ind AS 24", "AS 18"],
    }

    with pdfplumber.open(pdf_path) as pdf:
        page_texts = [p.extract_text() or "" for p in pdf.pages]
        total_pages = len(pdf.pages)
        basis_range = locate_basis_page_range(page_texts, basis.value)
        start, end = basis_range if basis_range else (0, total_pages)
        
        flattened = []
        for p_idx in range(start, end):
            text = page_texts[p_idx]
            for line in text.splitlines():
                flattened.append(LineInfo(p_idx + 1, line))

        note_units = segment_notes(flattened)
        unit_map = build_unit_map(page_texts)

        for field_name, anchors in TARGETS.items():
            for anchor in anchors:
                for unit in note_units:
                    unit_text = "\n".join([flattened[i].text for i in range(unit.start_line_idx, unit.end_line_idx)])
                    if anchor.lower() in unit_text.lower():
                        found_fields = extract_value_from_note(
                            unit, flattened, anchor, field_name, doc_fy, basis, source_filename, document_id
                        )
                        if found_fields:
                            fields.extend(found_fields)
                            break
                if any(f.field_name == field_name for f in fields):
                    break
        
        # Extract detailed contingent liability breakdown (v4)
        for unit in note_units:
            unit_text = "\n".join([flattened[i].text for i in range(unit.start_line_idx, unit.end_line_idx)])
            if "contingent liabilit" in unit_text.lower():
                fields.extend(extract_contingent_breakdown(unit, flattened, doc_fy, basis, source_filename, document_id))
                break

    return [apply_unit_normalization(f, unit_map) for f in fields]
