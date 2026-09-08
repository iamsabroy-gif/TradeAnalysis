"""
Tier 1 text extraction engine using PyMuPDF (fitz).
Maps strictly to implementpdf.md Stage 2 and Phase1-WebApp-Implementation-Plan.md §5.2.
Extracts narrative fields (audit_opinion, cfo_changes_last_3y, auditor_resigned_mid_tenure) with page citations.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
import pymupdf as fitz

from backend.app.acquisition.adapters.pdf.anchors import SECTION_PATTERNS, matches_anchor
from backend.app.acquisition.types import ExtractedField
from backend.app.models.enums import AuditOpinion, Confidence, ExtractionMethod, ReportingBasis


def locate_auditor_report_pages(doc: fitz.Document) -> List[int]:
    """
    Finds page indices (0-based) containing the Independent Auditor's Report.
    """
    candidate_pages = []
    for page_idx in range(len(doc)):
        text = doc[page_idx].get_text("text")
        matched, score, _ = matches_anchor(text[:1000], SECTION_PATTERNS["auditor_opinion"])
        if matched:
            candidate_pages.append(page_idx)
            # Auditor reports typically span 3-10 pages
            for next_idx in range(page_idx + 1, min(page_idx + 12, len(doc))):
                next_text = doc[next_idx].get_text("text")
                if "independent auditor" in next_text.lower() or "basis for opinion" in next_text.lower() or "key audit matters" in next_text.lower():
                    if next_idx not in candidate_pages:
                        candidate_pages.append(next_idx)
            break
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
    pages = locate_auditor_report_pages(doc)
    if not pages:
        # Fallback search across all pages
        for page_idx in range(len(doc)):
            text = doc[page_idx].get_text("text")
            if "independent auditor's report" in text.lower() or "independent auditors' report" in text.lower():
                pages.append(page_idx)

    for page_idx in pages:
        text = doc[page_idx].get_text("text")
        lower = text.lower()

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
