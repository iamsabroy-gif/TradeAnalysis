"""
PDF document classifier for Phase 1 Gatekeeper.
Maps strictly to Phase1-WebApp-Implementation-Plan.md §5.1.
Evaluates extractable text density to classify as NATIVE_TEXT, HYBRID, or SCANNED_IMAGE_ONLY.
"""

from pathlib import Path
from typing import Optional, Tuple, Union
import pymupdf as fitz

from backend.app.acquisition.adapters.pdf.anchors import detect_fiscal_year_from_text
from backend.app.models.enums import PdfClass


def classify_pdf(pdf_input: Union[Path, str, bytes]) -> Tuple[PdfClass, int, Optional[str]]:
    """
    Classifies the PDF into NATIVE_TEXT, HYBRID, or SCANNED_IMAGE_ONLY.
    Returns (pdf_class, page_count, detected_fiscal_year).
    """
    if isinstance(pdf_input, (bytes, bytearray)):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_input))

    page_count = len(doc)
    if page_count == 0:
        doc.close()
        return PdfClass.SCANNED_IMAGE_ONLY, 0, None

    total_chars = 0
    pages_with_text = 0
    sample_text = ""

    # Check up to first 30 pages and sample evenly if large document
    sample_limit = min(page_count, 30)
    for i in range(sample_limit):
        page = doc[i]
        text = page.get_text("text")
        char_count = len(text.strip())
        total_chars += char_count
        if char_count > 100:
            pages_with_text += 1
        if i < 10:
            sample_text += " " + text

    # Try detecting fiscal year from cover / introductory pages
    detected_fy = detect_fiscal_year_from_text(sample_text)

    doc.close()

    avg_chars_per_sampled_page = total_chars / sample_limit
    has_partial = pages_with_text > 0 and pages_with_text < (sample_limit * 0.7)

    if avg_chars_per_sampled_page >= 300 and pages_with_text >= (sample_limit * 0.7):
        pdf_class = PdfClass.NATIVE_TEXT
    elif has_partial or avg_chars_per_sampled_page >= 50:
        pdf_class = PdfClass.HYBRID
    else:
        pdf_class = PdfClass.SCANNED_IMAGE_ONLY

    return pdf_class, page_count, detected_fy
