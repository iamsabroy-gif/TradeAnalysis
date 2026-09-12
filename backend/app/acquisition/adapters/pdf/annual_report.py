"""
AnnualReportAdapter for Phase 1 Gatekeeper.
Implements SourceAdapter for Annual Report PDFs.
Extracts audit opinion, notes, and financial statement fields with page citations.
Maps strictly to implementpdf.md Stage 3 and Phase1-WebApp-Implementation-Plan.md §5.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import pymupdf as fitz
import pdfplumber

from backend.app.acquisition.adapters.pdf.classify import classify_pdf
from backend.app.acquisition.adapters.pdf.table_tier import extract_note_fields_from_pdf
from backend.app.acquisition.adapters.pdf.text_tier import (
    extract_audit_opinion_from_doc,
    extract_auditor_resignation_from_doc,
    extract_cfo_changes_from_doc,
    extract_regulatory_action_from_doc,
    extract_restatement_from_doc,
)
from backend.app.acquisition.base import SourceAdapter
from backend.app.acquisition.types import (
    AdapterError,
    AdapterResult,
    CompanyIdentity,
    ExtractedField,
    NotFoundField,
    RawPage,
    SourceDocument,
)
from backend.app.models.coverage import FIELD_COVERAGE_MATRIX
from backend.app.models.enums import PdfClass, ReportingBasis
from backend.app.acquisition.adapters.pdf.units import build_unit_map, apply_unit_normalization

# Explicit, code-verified field coverage
_OWNED_FIELDS = frozenset(
    {
        "audit_opinion",
        "contingent_liabilities",
        "audit_fees",
        "legal_fees",
        "legal_fees_prior_year",
        "rpt_sales_plus_purchases",
        "auditor_resigned_mid_tenure_last_3y",
        "cfo_changes_last_3y",
        "restatement_of_past_accounts",
        "regulatory_action",
        "revenue",
        "net_worth",
    }
)


class AnnualReportAdapter(SourceAdapter):
    """Adapter for extracting structured data from Annual Report PDFs."""

    name = "AnnualReportAdapter"

    def __init__(self):
        self.owned_fields = _OWNED_FIELDS

    def owns_field(self, field_name: str) -> bool:
        return field_name in self.owned_fields

    def fetch(self, identity: CompanyIdentity, basis: ReportingBasis) -> List[RawPage]:
        return []

    def parse(self, pages: List[RawPage]) -> AdapterResult:
        return AdapterResult(adapter=self.name)

    def _extract_statement_fields(self, pdf_path: Path, source_filename: str, doc_fy: Optional[str], basis: ReportingBasis, document_id: Optional[str]) -> List[ExtractedField]:
        """
        Statement Tier: Extracts high-level aggregates (Revenue, Net Worth) from primary financial statements.
        Maps to chunkrule-v3.md §2.
        """
        from backend.app.acquisition.adapters.parsers.screener_tables import parse_clean_number
        from backend.app.acquisition.adapters.pdf.anchors import SECTION_PATTERNS
        
        _STATEMENT_LABELS = {
            "revenue": ["Revenue from operations", "Total income", "Total revenue"],
            "net_worth": ["Total equity", "Shareholders' funds", "Net worth", "Total equity attributable to owners"],
        }
        
        def _extract_from_table(table, labels):
            for row in table:
                if not row or not row[0]: continue
                label = str(row[0]).strip()
                if any(pat.lower() in label.lower() for pat in labels):
                    for col_idx in range(1, len(row)):
                        val = parse_clean_number(str(row[col_idx]))
                        if val is not None: return val
            return None

        fields = []
        with pdfplumber.open(pdf_path) as pdf:
            page_texts = [p.extract_text() or "" for p in pdf.pages]
            unit_map = build_unit_map(page_texts)
            
            # Revenue (P&L)
            for idx, text in enumerate(page_texts):
                if any(pat.lower() in text.lower() for pat in SECTION_PATTERNS["revenue_from_operations"]):
                    for tbl in pdf.pages[idx].extract_tables():
                        val = _extract_from_table(tbl, _STATEMENT_LABELS["revenue"])
                        if val is not None:
                            fields.append(ExtractedField(
                                field_name="revenue", value=val, confidence=Confidence.HIGH,
                                extraction_method=ExtractionMethod.TABLE_PARSE, source=source_filename,
                                period=doc_fy or "FY24", basis=basis, page=idx+1,
                                raw_snippet=f"Revenue found on p.{idx+1}: {val}", document_id=document_id))
                            break
                    if any(f.field_name == "revenue" for f in fields): break

            # Net Worth (BS)
            for idx, text in enumerate(page_texts):
                if any(pat.lower() in text.lower() for pat in SECTION_PATTERNS["balance_sheet_equity"]):
                    for tbl in pdf.pages[idx].extract_tables():
                        val = _extract_from_table(tbl, _STATEMENT_LABELS["net_worth"])
                        if val is not None:
                            fields.append(ExtractedField(
                                field_name="net_worth", value=val, confidence=Confidence.HIGH,
                                extraction_method=ExtractionMethod.TABLE_PARSE, source=source_filename,
                                period=doc_//fy or "FY24", basis=basis, page=idx+1,
                                raw_snippet=f"Net worth found on p.{idx+1}: {val}", document_id=document_id))
                            break
                    if any(f.field_name == "net_worth" for f in fields): break
                    
        return [apply_unit_normalization(f, unit_map) for f in fields]

    def parse_document(self, doc: SourceDocument) -> AdapterResult:
        pdf_path = Path(doc.stored_path)
        if not pdf_path.exists():
            return AdapterResult(
                adapter=self.name,
                errors=[AdapterError(field_name=None, message=f"Document file not found: {doc.stored_path}", fatal=True)],
            )

        fields: List[ExtractedField] = []
        errors: List[AdapterError] = []
        period = doc.fiscal_year or "FY24"

        # 0. Statement Tier: High-level aggregates from BS/P&L
        if doc.pdf_class in {PdfClass.NATIVE_TEXT, PdfClass.HYBRID}:
            try:
                fields.extend(self._extract_statement_fields(pdf_path, doc.filename, doc.fiscal_year, doc.basis, doc.doc_id))
            except Exception as e:
                errors.append(AdapterError(field_name=None, message=f"Statement tier extraction error: {str(e)}"))

        # 1. Tier 1: Narrative text extraction with PyMuPDF
        try:
            pdf_doc = fitz.open(str(pdf_path))
            try:
                audit_op_field = extract_audit_opinion_from_doc(
                    doc=pdf_doc,
                    source_filename=doc.filename,
                    period=period,
                    basis=doc.basis,
                    document_id=doc.doc_id,
                )
                if audit_op_field:
                    fields.append(audit_op_field)
            except Exception as e:
                errors.append(AdapterError(field_name="audit_opinion", message=f"Tier 1 audit opinion extraction error: {str(e)}"))

            try:
                resignation_field = extract_auditor_resignation_from_doc(
                    doc=pdf_doc,
                    source_filename=doc.filename,
                    period=period,
                    basis=doc.basis,
                    document_id=doc.doc_id,
                )
                if resignation_field:
                    fields.append(resignation_field)
            except Exception as e:
                errors.append(AdapterError(field_name="auditor_resigned_mid_tenure_last_3y", message=f"Tier 1 auditor resignation extraction error: {str(e)}"))

            try:
                cfo_field = extract_cfo_changes_from_doc(
                    doc=pdf_doc,
                    source_filename=doc.filename,
                    period=period,
                    basis=doc.basis,
                    document_id=doc.doc_id,
                )
                if cfo_field:
                    fields.append(cfo_field)
            except Exception as e:
                errors.append(AdapterError(field_name="cfo_changes_last_3y", message=f"Tier 1 CFO changes extraction error: {str(e)}"))

            try:
                fields.extend(
                    extract_restatement_from_doc(
                        doc=pdf_doc,
                        source_filename=doc.filename,
                        period=period,
                        basis=doc.basis,
                        document_id=doc.doc_id,
                    )
                )
            except Exception as e:
                errors.append(AdapterError(field_name="restatement_of_past_accounts", message=f"Tier 1 restatement extraction error: {str(e)}"))

            try:
                regulatory_field = extract_regulatory_action_from_doc(
                    doc=pdf_doc,
                    source_filename=doc.filename,
                    period=period,
                    basis=doc.basis,
                    document_id=doc.doc_id,
                )
                if regulatory_field:
                    fields.append(regulatory_field)
            except Exception as e:
                errors.append(AdapterError(field_name="regulatory_action", message=f"Tier 1 regulatory action extraction error: {str(e)}"))

            pdf_doc.close()
        except Exception as e:
            errors.append(AdapterError(field_name=None, message=f"Tier 1 text extraction error: {str(e)}"))

        # 2. Tier 2: Table note extraction with pdfplumber
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

        found_field_names = {f.field_name for f in fields}
        not_found = [
            NotFoundField(
                field_name=fname,
                reason=(
                    f"No matching disclosure located in this document. Expected source: "
                    f"{FIELD_COVERAGE_MATRIX.get(fname, {}).get('source', 'unknown')}"
                ),
            )
            for fname in sorted(self.owned_fields - found_field_names)
            if not (
                doc.pdf_class not in {PdfClass.NATIVE_TEXT, PdfClass.HYBRID}
                and fname in {"contingent_liabilities", "audit_fees", "legal_fees", "legal_fees_prior_year", "rpt_sales_plus_purchases", "revenue", "net_worth"}
            )
        ]

        return AdapterResult(
            adapter=self.name,
            fields=fields,
            errors=errors,
            not_found=not_found,
        )

    def parse_documents(self, docs: List[SourceDocument]) -> AdapterResult:
        all_fields: List[ExtractedField] = []
        all_errors: List[AdapterError] = []
        per_doc_not_found: List[set] = []
        for doc in docs:
            res = self.parse_document(doc)
            all_fields.extend(res.fields)
            all_errors.extend(res.errors)
            per_doc_not_found.append({nf.field_name for nf in res.not_found})

        found_anywhere = {f.field_name for f in all_fields}
        always_missing = set.intersection(*per_doc_not_found) if per_doc_not_found else set()
        merged_not_found = [
            NotFoundField(
                field_name=fname,
                reason=(
                    f"No matching disclosure located in any of the {len(docs)} document(s) scanned. "
                    f"Expected source: {FIELD_COVERAGE_MATRIX.get(fname, {}).get('source', 'unknown')}"
                ),
            )
            for fname in sorted(always_missing - found_anywhere)
        ]

        return AdapterResult(
            adapter=self.name,
            fields=all_fields,
            errors=all_errors,
            not_found=merged_not_found,
        )

    def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "adapter": self.name}
