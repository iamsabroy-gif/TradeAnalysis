"""
Pure HTML Parser for Screener.in tables.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §5.2.
Zero I/O. Extracts fields with structural assertions, resolving column-to-period.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from backend.app.acquisition.types import (
    AdapterError,
    AdapterResult,
    DocumentRef,
    ExtractedField,
    LayoutChangedError,
    RawPage,
)
from backend.app.models.enums import Confidence, ExtractionMethod, ReportingBasis


_NIL_TOKENS = {"", "-", "--", "—", "–", "−", "n/a", "na", "nil", "none"}
_CURRENCY_AND_MARKERS = re.compile(r"[`\u20b9$*#†‡^~]|(?:\bRs\.?|\bINR)", re.IGNORECASE)
_NUMERIC = re.compile(r"^-?\d+(?:\.\d+)?$")


def parse_clean_number(text: str) -> Optional[float]:
    """
    Parses a numeric cell from a Screener table or an Annual Report line.

    Handles the notations these sources actually use: thousands separators,
    accounting negatives in parentheses, the rupee symbol and the backtick that
    PDF extraction leaves in its place, footnote markers, and the several dash
    characters that stand for nil.
    """
    if text is None:
        return None

    cleaned = _CURRENCY_AND_MARKERS.sub(" ", str(text))
    cleaned = cleaned.replace("\u00a0", " ").replace("\u2009", " ").replace("%", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned.lower() in _NIL_TOKENS:
        return None

    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1].strip()

    cleaned = cleaned.replace("−", "-").replace("–", "-").replace("—", "-")
    cleaned = cleaned.replace(",", "")
    # An interior space means two adjacent columns were merged, not a single
    # number - refuse it rather than concatenating unrelated digits.
    if " " in cleaned or not _NUMERIC.match(cleaned):
        return None

    value = float(cleaned)
    return -value if negative else value


def normalize_period_to_fy(text: str) -> str:
    """Normalizes 'Mar 2024', '2024-03-31', or 'FY2024' to 'FY24'."""
    if not text:
        return "FY24"
    m = re.search(r"20(\d{2})", text)
    if m:
        return f"FY{m.group(1)}"
    return text.strip()


def parse_screener_html(
    html_content: str,
    source_url: str,
    basis: ReportingBasis,
) -> AdapterResult:
    """
    Pure parser from HTML string to AdapterResult.
    Raises LayoutChangedError on structural violations.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    fields: List[ExtractedField] = []
    errors: List[AdapterError] = []
    documents: List[DocumentRef] = []

    # 1. Parse Financial Tables (Cash Flow, P&L, Balance Sheet)
    # Helper to find a table and parse rows into dict: label -> (header_cols, value_cols)
    tables = soup.find_all("table")

    table_data: Dict[str, Tuple[List[str], List[str]]] = {}
    for tbl in tables:
        # Get headers
        header_row = tbl.find("thead")
        headers = []
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all("th")]

        tbody = tbl.find("tbody") or tbl
        for tr in tbody.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if not tds:
                continue
            row_label = tds[0].get_text(strip=True).lower()
            vals = [td.get_text(strip=True) for td in tds[1:]]
            if vals:
                hdrs = headers[1:] if len(headers) > 1 else []
                # Strip trailing TTM column if present so only closed fiscal years remain
                if hdrs and hdrs[-1].strip().upper() == "TTM":
                    hdrs = hdrs[:-1]
                    vals = vals[:-1] if len(vals) > len(hdrs) else vals
                table_data[row_label] = (hdrs, vals)

    # 1A. CFO row: Cash from Operating Activity
    cfo_headers = []
    cfo_row = None
    for label, (hdrs, vals) in table_data.items():
        if any(k in label for k in ["cash from operating activity", "operating cash flow", "cfo/op", "cash flow from operating activities"]):
            cfo_headers = hdrs
            cfo_row = vals
            break

    # 1B. PAT row: Net Profit
    pat_headers = []
    pat_row = None
    for label, (hdrs, vals) in table_data.items():
        if any(k in label for k in ["net profit", "profit after tax", "net income"]):
            pat_headers = hdrs
            pat_row = vals
            break

    # Structural assertion on Cash Flow & PAT
    if cfo_row is not None and pat_row is not None:
        # If one table has >= 5 years but the other has fewer, layout drift / column drop occurred
        if (len(cfo_row) < 5 and len(pat_row) >= 5) or (len(pat_row) < 5 and len(cfo_row) >= 5):
            raise LayoutChangedError(
                f"Expected >= 5 fiscal years in Cash Flow & P&L tables; found {len(cfo_row)} and {len(pat_row)}"
            )
        if len(cfo_row) < 1 or len(pat_row) < 1:
            raise LayoutChangedError("Expected >= 1 fiscal year in Cash Flow & P&L tables")
        if len(cfo_row) < 5 and len(cfo_row) != len(pat_row):
            raise LayoutChangedError(
                f"Cash Flow and P&L table rows have mismatched column counts: {len(cfo_row)} vs {len(pat_row)}"
            )

        take_n = min(5, len(cfo_row), len(pat_row))
        # Ensure column headers align before taking the series
        if cfo_headers and pat_headers and len(cfo_headers) >= take_n and len(pat_headers) >= take_n:
            if cfo_headers[-take_n:] != pat_headers[-take_n:]:
                raise LayoutChangedError(
                    f"Cash Flow and P&L table headers do not align: {cfo_headers[-take_n:]} vs {pat_headers[-take_n:]}"
                )

        cfo_nums = [parse_clean_number(v) for v in cfo_row[-take_n:]]
        pat_nums = [parse_clean_number(v) for v in pat_row[-take_n:]]

        if any(v is None for v in cfo_nums) or any(v is None for v in pat_nums):
            raise LayoutChangedError("Non-numeric entries found in CFO or PAT series")

        # Period resolution from headers
        period_span = f"FY{take_n}"
        if cfo_headers and len(cfo_headers) >= take_n:
            period_span = f"{cfo_headers[-take_n]}-{cfo_headers[-1]}"

        fields.append(
            ExtractedField(
                field_name="cfo_last_5y",
                value=cfo_nums,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.HTML_SCRAPE,
                source=source_url,
                period=period_span,
                basis=basis,
                raw_snippet=f"CFO: {cfo_nums}",
            )
        )

        fields.append(
            ExtractedField(
                field_name="pat_last_5y",
                value=pat_nums,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.HTML_SCRAPE,
                source=source_url,
                period=period_span,
                basis=basis,
                raw_snippet=f"Net Profit: {pat_nums}",
            )
        )

        # Count track record from length of financial years
        years_available = min(len(cfo_row), len(pat_row))
        if years_available > 0:
            fields.append(
                ExtractedField(
                    field_name="years_of_track_record_available",
                    value=years_available,
                    confidence=Confidence.HIGH,
                    extraction_method=ExtractionMethod.HTML_SCRAPE,
                    source=source_url,
                    period=f"{years_available}y",
                    basis=ReportingBasis.NOT_APPLICABLE,
                    raw_snippet=f"Financial history: {years_available} years",
                )
            )
    else:
        errors.append(AdapterError(field_name="cfo_last_5y", message="CFO row not found in HTML tables"))
        errors.append(AdapterError(field_name="pat_last_5y", message="Net profit row not found in HTML tables"))

    # 1C. Revenue row: Sales or Revenue from operations
    for label, (hdrs, vals) in table_data.items():
        if "sales" in label or "revenue" in label:
            rev_val = parse_clean_number(vals[-1])
            if rev_val is not None:
                rev_period = normalize_period_to_fy(hdrs[-1]) if hdrs else "FY24"
                fields.append(
                    ExtractedField(
                        field_name="revenue",
                        value=rev_val,
                        confidence=Confidence.HIGH,
                        extraction_method=ExtractionMethod.HTML_SCRAPE,
                        source=source_url,
                        period=rev_period,
                        basis=basis,
                        raw_snippet=f"{label}: {vals[-1]}",
                    )
                )
                break

    # 1D. Net Worth: Equity Capital + Reserves
    equity_val = None
    reserves_val = None
    bs_headers = []
    for label, (hdrs, vals) in table_data.items():
        if "equity capital" in label or "share capital" in label:
            equity_val = parse_clean_number(vals[-1])
            bs_headers = hdrs
        elif "reserves" in label:
            reserves_val = parse_clean_number(vals[-1])
            if not bs_headers:
                bs_headers = hdrs

    if equity_val is not None and reserves_val is not None:
        net_worth = equity_val + reserves_val
        nw_period = normalize_period_to_fy(bs_headers[-1]) if bs_headers else "FY24"
        fields.append(
            ExtractedField(
                field_name="net_worth",
                value=net_worth,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.HTML_SCRAPE,
                source=source_url,
                period=nw_period,
                basis=basis,
                raw_snippet=f"Equity ({equity_val}) + Reserves ({reserves_val})",
            )
        )

    # 2. Shareholding Pattern
    # Look for Promoters, Government, Pledged percentage
    for label, (hdrs, vals) in table_data.items():
        if label == "promoters" or label.startswith("promoter"):
            num = parse_clean_number(vals[-1])
            if num is not None and 0.0 <= num <= 100.0:
                fields.append(
                    ExtractedField(
                        field_name="promoter_holding_pct_of_company",
                        value=num,
                        confidence=Confidence.HIGH,
                        extraction_method=ExtractionMethod.HTML_SCRAPE,
                        source=source_url,
                        period=hdrs[-1] if hdrs else "Latest Quarter",
                        basis=ReportingBasis.NOT_APPLICABLE,
                        raw_snippet=f"Promoters: {num}%",
                    )
                )

        if "government" in label or "president of india" in label:
            num = parse_clean_number(vals[-1])
            if num is not None and 0.0 <= num <= 100.0:
                fields.append(
                    ExtractedField(
                        field_name="govt_shareholding_pct",
                        value=num,
                        confidence=Confidence.HIGH,
                        extraction_method=ExtractionMethod.HTML_SCRAPE,
                        source=source_url,
                        period=hdrs[-1] if hdrs else "Latest Quarter",
                        basis=ReportingBasis.NOT_APPLICABLE,
                        raw_snippet=f"Government: {num}%",
                    )
                )

        if "pledged" in label:
            # Pledged percentage row
            if len(vals) < 4:
                raise LayoutChangedError(f"Pledge row expected >= 4 quarters, found {len(vals)}")
            history_nums = [parse_clean_number(v) or 0.0 for v in vals[-4:]]
            latest_pledge = history_nums[-1]

            fields.append(
                ExtractedField(
                    field_name="pledged_pct_of_promoter_holding",
                    value=latest_pledge,
                    confidence=Confidence.HIGH,
                    extraction_method=ExtractionMethod.HTML_SCRAPE,
                    source=source_url,
                    period=hdrs[-1] if hdrs else "Latest Quarter",
                    basis=ReportingBasis.NOT_APPLICABLE,
                    raw_snippet=f"Pledged: {latest_pledge}%",
                )
            )

            fields.append(
                ExtractedField(
                    field_name="pledged_pct_history_last_4q",
                    value=history_nums,
                    confidence=Confidence.HIGH,
                    extraction_method=ExtractionMethod.HTML_SCRAPE,
                    source=source_url,
                    period="Trailing 4Q",
                    basis=ReportingBasis.NOT_APPLICABLE,
                    raw_snippet=f"Pledge 4Q: {history_nums}",
                )
            )

    # If government row was absent, set govt_shareholding_pct to 0.0 if promoters exist
    has_promoters = any(f.field_name == "promoter_holding_pct_of_company" for f in fields)
    has_govt = any(f.field_name == "govt_shareholding_pct" for f in fields)
    if has_promoters and not has_govt:
        fields.append(
            ExtractedField(
                field_name="govt_shareholding_pct",
                value=0.0,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.HTML_SCRAPE,
                source=source_url,
                period="Latest",
                basis=ReportingBasis.NOT_APPLICABLE,
                raw_snippet="Government row absent from shareholding pattern -> 0.0%",
            )
        )

    # If pledge row was absent but promoters exist, default pledge to 0.0% (common for companies with zero pledge)
    has_pledge = any(f.field_name == "pledged_pct_of_promoter_holding" for f in fields)
    if has_promoters and not has_pledge:
        fields.append(
            ExtractedField(
                field_name="pledged_pct_of_promoter_holding",
                value=0.0,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.HTML_SCRAPE,
                source=source_url,
                period="Latest",
                basis=ReportingBasis.NOT_APPLICABLE,
                raw_snippet="Pledge row absent -> 0.0% unpledged",
            )
        )
        fields.append(
            ExtractedField(
                field_name="pledged_pct_history_last_4q",
                value=[0.0, 0.0, 0.0, 0.0],
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.HTML_SCRAPE,
                source=source_url,
                period="Trailing 4Q",
                basis=ReportingBasis.NOT_APPLICABLE,
                raw_snippet="Pledge row absent -> [0.0, 0.0, 0.0, 0.0]",
            )
        )

    # 3. Documents section (Annual Reports links captured as DocumentRef, §5.4)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if ".pdf" in href.lower() or "annual report" in text.lower():
            # Try matching year
            year_match = re.search(r"20\d{2}", text) or re.search(r"20\d{2}", href)
            year_str = year_match.group(0) if year_match else "Unknown"
            documents.append(
                DocumentRef(
                    fiscal_year=year_str,
                    url=href,
                    title=text or "Annual Report",
                )
            )

    return AdapterResult(
        adapter="ScreenerAdapter",
        fields=fields,
        documents=documents,
        errors=errors,
    )
