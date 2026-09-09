"""
Tier 1 text extraction engine using PyMuPDF (fitz).
Maps strictly to implementpdf.md Stage 2 and Phase1-WebApp-Implementation-Plan.md §5.2.
Extracts narrative fields (audit_opinion, cfo_changes_last_3y, auditor_resigned_mid_tenure) with page citations.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
import pymupdf as fitz

from backend.app.acquisition.adapters.pdf.anchors import (
    SECTION_PATTERNS,
    locate_basis_page_range,
    matches_anchor,
    normalize_quotes,
)
from backend.app.acquisition.types import ExtractedField
from backend.app.models.enums import AuditOpinion, Confidence, ExtractionMethod, ReportingBasis


# The bare word "Opinion" appears in board reports and accounting policies all
# through an annual report, so the report's opening page is identified by its
# masthead plus the addressee line that only the statutory report carries.
_AUDITOR_REPORT_HEADINGS = [
    r"independent auditor'?s'? report",
    r"report on the audit of the (?:standalone|consolidated) financial statements",
]
_AUDITOR_REPORT_CONFIRMERS = ["to the members", "we have audited"]


def locate_auditor_report_pages(
    doc: fitz.Document,
    basis: Optional[ReportingBasis] = None,
) -> List[int]:
    """
    Finds page indices (0-based) containing the Independent Auditor's Report.
    When `basis` is given and the document separates its standalone and
    consolidated sections, only that basis's report is returned.
    """
    page_texts = [doc[i].get_text("text") for i in range(len(doc))]
    start, end = 0, len(page_texts)
    if basis is not None:
        page_range = locate_basis_page_range(page_texts, basis.value)
        if page_range:
            start, end = page_range

    first_page: Optional[int] = None
    for page_idx in range(start, end):
        text = re.sub(r"\s+", " ", normalize_quotes(page_texts[page_idx]).lower())
        head = text[:1500]
        if not any(re.search(pat, head) for pat in _AUDITOR_REPORT_HEADINGS):
            continue
        if not any(marker in head for marker in _AUDITOR_REPORT_CONFIRMERS):
            # A contents entry or a cross-reference, not the report itself.
            continue
        first_page = page_idx
        break

    if first_page is None:
        return []

    # Auditor reports typically span 3-10 pages.
    candidate_pages = [first_page]
    for next_idx in range(first_page + 1, min(first_page + 12, end)):
        next_text = normalize_quotes(page_texts[next_idx]).lower()
        if (
            "independent auditor" in next_text
            or "basis for opinion" in next_text
            or "key audit matters" in next_text
        ):
            candidate_pages.append(next_idx)
    return candidate_pages


def extract_audit_opinion_from_doc(
    doc: fitz.Document,
    source_filename: str,
    period: str,
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> Optional[ExtractedField]:
    """
    Extracts and classifies the statutory audit opinion into CLEAN, QUALIFIED, ADVERSE, or DISCLAIMER.
    Returns ExtractedField with exact page citation and raw text snippet.
    """
    pages = locate_auditor_report_pages(doc, basis=basis)
    if not pages:
        # Fallback search across all pages, ignoring the basis split.
        pages = locate_auditor_report_pages(doc)
    if not pages:
        for page_idx in range(len(doc)):
            text = normalize_quotes(doc[page_idx].get_text("text")).lower()
            if "independent auditor's report" in text:
                pages.append(page_idx)

    for page_idx in pages:
        text = doc[page_idx].get_text("text")
        # Opinion wording wraps across lines in the PDF, so match against text
        # with its line breaks collapsed.
        lower = re.sub(r"\s+", " ", normalize_quotes(text).lower())

        # Check for Adverse Opinion
        if "adverse opinion" in lower:
            snippet_match = re.search(r"(?:adverse opinion.*?\.{1,2})", text, re.IGNORECASE | re.DOTALL)
            snippet = snippet_match.group(0)[:300] if snippet_match else text[:300]
            return ExtractedField(
                field_name="audit_opinion",
                value=AuditOpinion.ADVERSE,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"Adverse opinion on page {page_idx + 1}: {snippet.strip()}",
                document_id=document_id,
            )

        # Check for Disclaimer of Opinion
        if "disclaimer of opinion" in lower:
            snippet_match = re.search(r"(?:disclaimer of opinion.*?\.{1,2})", text, re.IGNORECASE | re.DOTALL)
            snippet = snippet_match.group(0)[:300] if snippet_match else text[:300]
            return ExtractedField(
                field_name="audit_opinion",
                value=AuditOpinion.DISCLAIMER,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"Disclaimer of opinion on page {page_idx + 1}: {snippet.strip()}",
                document_id=document_id,
            )

        # Check for Qualified Opinion
        if "qualified opinion" in lower or "basis for qualified opinion" in lower:
            snippet_match = re.search(r"(?:qualified opinion.*?\.{1,2})", text, re.IGNORECASE | re.DOTALL)
            snippet = snippet_match.group(0)[:300] if snippet_match else text[:300]
            return ExtractedField(
                field_name="audit_opinion",
                value=AuditOpinion.QUALIFIED,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"Qualified opinion on page {page_idx + 1}: {snippet.strip()}",
                document_id=document_id,
            )

        # Check for Clean / Unmodified Opinion
        clean_indicators = [
            "give a true and fair view",
            "gives a true and fair view",
            "unmodified opinion",
            "opinion on the financial statements",
        ]
        for ind in clean_indicators:
            if ind in lower:
                # Ensure it's inside an opinion context
                m = re.search(r"(?:in our opinion|our opinion).*?(?:true and fair view|unmodified).*?\.", text, re.IGNORECASE | re.DOTALL)
                snippet = m.group(0)[:300] if m else text[:300]
                return ExtractedField(
                    field_name="audit_opinion",
                    value=AuditOpinion.CLEAN,
                    confidence=Confidence.HIGH,
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                    source=source_filename,
                    period=period,
                    basis=basis,
                    page=page_idx + 1,
                    raw_snippet=f"Clean opinion on page {page_idx + 1}: {snippet.strip()}",
                    document_id=document_id,
                )

    return None
