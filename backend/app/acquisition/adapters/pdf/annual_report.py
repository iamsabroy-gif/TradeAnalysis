"""
AnnualReportAdapter for Phase 1 Gatekeeper.
Implements SourceAdapter for Annual Report PDFs.
Extracts audit opinion, notes, and financial statement fields with page citations.
Maps strictly to implementpdf.md Stage 3 and Phase1-WebApp-Implementation-Plan.md §5.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import pymupdf as fitz

from backend.app.acquisition.adapters.pdf.classify import classify_pdf
from backend.app.acquisition.adapters.pdf.table_tier import extract_note_fields_from_pdf
from backend.app.acquisition.adapters.pdf.text_tier import extract_audit_opinion_from_doc
from backend.app.acquisition.base import SourceAdapter
from backend.app.acquisition.types import AdapterError, AdapterResult, CompanyIdentity, ExtractedField, RawPage, SourceDocument
from backend.app.models.coverage import FIELD_COVERAGE_MATRIX
from backend.app.models.enums import PdfClass, ReportingBasis


class AnnualReportAdapter(SourceAdapter):
    """Adapter for extracting structured data from Annual Report PDFs."""

    name = "AnnualReportAdapter"

    def __init__(self):
        # Derive owned fields dynamically from coverage matrix
        self.owned_fields = frozenset(
            fname for fname, meta in FIELD_COVERAGE_MATRIX.items()
            if meta.get("owner", "").startswith("PDF tier")
        )

    def owns_field(self, field_name: str) -> bool:
        return field_name in self.owned_fields

    def fetch(self, identity: CompanyIdentity, basis: ReportingBasis) -> List[RawPage]:
        # Annual report PDFs arrive via user upload, not direct scrape
        return []

    def parse(self, pages: List[RawPage]) -> AdapterResult:
        return AdapterResult(adapter=self.name)

    def parse_document(self, doc: SourceDocument) -> AdapterResult:
        """
        Parses an uploaded SourceDocument and extracts structured ExtractedField instances.
        """
        pdf_path = Path(doc.stored_path)
        if not pdf_path.exists():
            return AdapterResult(
                adapter=self.name,
                errors=[AdapterError(field_name=None, message=f"Document file not found: {doc.stored_path}", fatal=True)],
            )

        fields: List[ExtractedField] = []
        errors: List[AdapterError] = []

        # 1. Tier 1: Narrative text extraction with PyMuPDF
        try:
            pdf_doc = fitz.open(str(pdf_path))
            audit_op_field = extract_audit_opinion_from_doc(
                doc=pdf_doc,
                source_filename=doc.filename,
                period=doc.fiscal_year or "FY24",
                basis=doc.basis,
                document_id=doc.doc_id,
            )
            if audit_op_field:
                fields.append(audit_op_field)
            pdf_doc.close()
        except Exception as e:
            errors.append(AdapterError(field_name="audit_opinion", message=f"Tier 1 text extraction error: {str(e)}"))

        # 2. Tier 2: Table note extraction with pdfplumber (for native & hybrid PDFs)
        if doc.pdf_class in {PdfClass.NATIVE_TEXT, PdfClass.HYBRID}:
            try:
                table_fields = extract_note_fields_from_pdf(
                    pdf_path=pdf_path,
                    source_filename=doc.filename,
                    doc_fy=doc.fiscal_year,
                    basis=doc.basis,
                    document_id=doc.doc_id,
                )
                fields.extend(table_fields)
            except Exception as e:
                errors.append(AdapterError(field_name=None, message=f"Tier 2 table extraction error: {str(e)}"))

        return AdapterResult(
            adapter=self.name,
            fields=fields,
            errors=errors,
        )

    def parse_documents(self, docs: List[SourceDocument]) -> AdapterResult:
        """Parses multiple documents and returns a merged AdapterResult."""
        all_fields: List[ExtractedField] = []
        all_errors: List[AdapterError] = []
        for doc in docs:
            res = self.parse_document(doc)
            all_fields.extend(res.fields)
            all_errors.extend(res.errors)
        return AdapterResult(
            adapter=self.name,
            fields=all_fields,
            errors=all_errors,
        )

    def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "adapter": self.name}
