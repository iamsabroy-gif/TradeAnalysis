"""
Unit and integration tests for PDF Annual Report ingestion pipeline.
Covers:
1. PDF Classification (classify_pdf)
2. Tier 1 Text Extraction (extract_audit_opinion_from_doc)
3. DocumentStore lifecycle (save, list, update, delete)
4. AnnualReportAdapter execution
5. Multi-period candidate resolution and restatement detection in assembler
6. FastAPI endpoints for documents and review queue
"""

from pathlib import Path
import pytest
import pymupdf as fitz
from starlette.testclient import TestClient

from backend.app.acquisition.adapters.pdf.classify import classify_pdf
from backend.app.acquisition.adapters.pdf.text_tier import extract_audit_opinion_from_doc
from backend.app.acquisition.adapters.pdf.annual_report import AnnualReportAdapter
from backend.app.acquisition.documents.store import DocumentStore
from backend.app.acquisition.types import CompanyIdentity, ExtractedField, SourceDocument
from backend.app.acquisition.assembler import assemble
from backend.app.api.main import app
from backend.app.models.enums import AuditOpinion, Confidence, ExtractionMethod, PdfClass, ReportingBasis


def create_mock_pdf_bytes(text: str) -> bytes:
    """Helper to create a valid minimal native-text PDF in memory."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 750), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_classify_pdf_native():
    sample_text = (
        "ANNUAL REPORT 2023-24\n"
        "FINANCIAL STATEMENTS AND DIRECTORS REPORT\n"
        "This is native text with enough paragraphs and words to simulate a realistic report page. "
        "The Company has prepared standalone and consolidated financial statements in accordance with "
        "Indian Accounting Standards (Ind AS) notified under section 133 of the Companies Act 2013, read "
        "together with the Companies (Indian Accounting Standards) Rules, 2015 as amended from time to time. "
        "All figures reported herein are denominated in INR crores unless otherwise specified."
    )
    pdf_bytes = create_mock_pdf_bytes(sample_text)
    pdf_class, page_count, detected_fy = classify_pdf(pdf_bytes)
    assert pdf_class == PdfClass.NATIVE_TEXT
    assert page_count == 1
    assert detected_fy == "FY24"


def test_tier1_audit_opinion_clean():
    clean_text = (
        "INDEPENDENT AUDITOR'S REPORT\n"
        "To the Members of Example Ltd\n"
        "Report on the Audit of the Financial Statements\n"
        "Opinion\n"
        "In our opinion and to the best of our information and according to the explanations given to us, "
        "the aforesaid standalone financial statements give a true and fair view in conformity with the Ind AS."
    )
    pdf_bytes = create_mock_pdf_bytes(clean_text)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    field = extract_audit_opinion_from_doc(doc, source_filename="mock.pdf", period="FY24", basis=ReportingBasis.CONSOLIDATED)
    doc.close()

    assert field is not None
    assert field.field_name == "audit_opinion"
    assert field.value == AuditOpinion.CLEAN
    assert field.confidence == Confidence.HIGH
    assert field.page == 1


def test_tier1_audit_opinion_qualified():
    qualified_text = (
        "INDEPENDENT AUDITOR'S REPORT\n"
        "To the Members of Example Ltd\n"
        "Qualified Opinion\n"
        "In our opinion and to the best of our information and according to the explanations given to us, "
        "except for the effects of the matter described in the Basis for Qualified Opinion section of our report, "
        "the financial statements give a true and fair view."
    )
    pdf_bytes = create_mock_pdf_bytes(qualified_text)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    field = extract_audit_opinion_from_doc(doc, source_filename="mock_q.pdf", period="FY24", basis=ReportingBasis.CONSOLIDATED)
    doc.close()

    assert field is not None
    assert field.field_name == "audit_opinion"
    assert field.value == AuditOpinion.QUALIFIED
    assert field.confidence == Confidence.HIGH


def test_document_store_lifecycle(tmp_path: Path):
    store = DocumentStore(base_dir=tmp_path)
    pdf_bytes = create_mock_pdf_bytes("Sample Annual Report")
    doc = SourceDocument(
        doc_id="testdoc123",
        ticker="TATAMOTORS",
        filename="tatamotors_ar24.pdf",
        fiscal_year="FY24",
        basis=ReportingBasis.CONSOLIDATED,
        pdf_class=PdfClass.NATIVE_TEXT,
        page_count=1,
        stored_path="",
        uploaded_at="2024-03-31T00:00:00Z",
    )

    saved = store.save(doc, pdf_bytes)
    assert Path(saved.stored_path).exists()
    assert store.get_content("TATAMOTORS", "testdoc123") == pdf_bytes

    docs = store.list_for_ticker("TATAMOTORS")
    assert len(docs) == 1
    assert docs[0].doc_id == "testdoc123"

    updated = store.update("TATAMOTORS", "testdoc123", fiscal_year="FY25", basis=ReportingBasis.STANDALONE)
    assert updated.fiscal_year == "FY25"
    assert updated.basis == ReportingBasis.STANDALONE

    deleted = store.delete("TATAMOTORS", "testdoc123")
    assert deleted is True
    assert len(store.list_for_ticker("TATAMOTORS")) == 0


def test_multi_period_assembler_selection_and_restatement():
    identity = CompanyIdentity(ticker="TESTTICKER", screener_code="TESTTICKER", company_name="Test Company")

    # Document 1 (FY23 AR) reported Net Worth of 1000.0 for FY23
    f1 = ExtractedField(
        field_name="net_worth",
        value=1000.0,
        confidence=Confidence.HIGH,
        extraction_method=ExtractionMethod.TABLE_PARSE,
        source="annual_report_2023.pdf",
        period="FY23",
        basis=ReportingBasis.CONSOLIDATED,
        raw_snippet="Net Worth: 1000.0",
        document_id="doc_2023",
    )

    # Document 2 (FY24 AR) reported Net Worth of 1200.0 for FY24, and restated FY23 to 950.0
    f2 = ExtractedField(
        field_name="net_worth",
        value=1200.0,
        confidence=Confidence.HIGH,
        extraction_method=ExtractionMethod.TABLE_PARSE,
        source="annual_report_2024.pdf",
        period="FY24",
        basis=ReportingBasis.CONSOLIDATED,
        raw_snippet="Net Worth: 1200.0",
        document_id="doc_2024",
    )
    f3_restated = ExtractedField(
        field_name="net_worth",
        value=950.0,  # Restated downwards!
        confidence=Confidence.HIGH,
        extraction_method=ExtractionMethod.TABLE_PARSE,
        source="annual_report_2024.pdf",
        period="FY23",
        basis=ReportingBasis.CONSOLIDATED,
        raw_snippet="Net Worth (Comparative FY23): 950.0",
        document_id="doc_2024",
    )

    from backend.app.acquisition.types import AdapterResult
    mock_result = AdapterResult(
        adapter="AnnualReportAdapter",
        fields=[f1, f2, f3_restated],
    )

    company_input, review_items = assemble(
        identity=identity,
        as_of_date="2024-03-31",
        basis=ReportingBasis.CONSOLIDATED,
        results=[mock_result],
    )

    # Run FY is FY24, so net_worth should be 1200.0
    assert company_input.net_worth == 1200.0

    # Restatement of past accounts should be flagged as True
    assert company_input.restatement_of_past_accounts is True


def test_api_documents_endpoints():
    client = TestClient(app)
    pdf_bytes = create_mock_pdf_bytes(
        "INDEPENDENT AUDITOR'S REPORT\nOpinion\nFinancial statements give a true and fair view."
    )

    # 1. Upload document
    resp = client.post(
        "/api/tickers/APITEST/documents",
        files=[("files", ("ar2024.pdf", pdf_bytes, "application/pdf"))],
        data={"fiscal_year": "FY24", "basis": "CONSOLIDATED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "APITEST"
    assert len(data["documents"]) == 1
    assert data["fields_count"] >= 1
    assert any(f["field_name"] == "audit_opinion" for f in data["extracted_fields"])
    doc_id = data["documents"][0]["doc_id"]

    # 2. List documents
    resp_list = client.get("/api/tickers/APITEST/documents")
    assert resp_list.status_code == 200
    docs = resp_list.json()["documents"]
    assert any(d["doc_id"] == doc_id for d in docs)

    # 3. Update document metadata
    resp_patch = client.patch(
        f"/api/tickers/APITEST/documents/{doc_id}",
        json={"fiscal_year": "FY25", "basis": "STANDALONE"},
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["fiscal_year"] == "FY25"

    # 4. Extract document
    resp_extract = client.post(
        "/api/tickers/APITEST/documents/extract",
        json={"document_ids": [doc_id]},
    )
    assert resp_extract.status_code == 200
    extract_data = resp_extract.json()
    assert extract_data["fields_count"] >= 1
    assert any(f["field_name"] == "audit_opinion" for f in extract_data["fields"])

    # 5. Delete document
    resp_del = client.delete(f"/api/tickers/APITEST/documents/{doc_id}")
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "deleted"


def test_tier2_note_table_extraction(tmp_path: Path):
    from backend.app.acquisition.adapters.pdf.table_tier import extract_note_fields_from_pdf

    note_text = (
        "Note 28: Other Expenses\n"
        "Payment to Auditors:\n"
        "Statutory Audit Fee: 25.5 Cr\n"
    )
    pdf_bytes = create_mock_pdf_bytes(note_text)
    pdf_file = tmp_path / "mock_notes.pdf"
    pdf_file.write_bytes(pdf_bytes)

    fields = extract_note_fields_from_pdf(
        pdf_path=pdf_file,
        source_filename="mock_notes.pdf",
        doc_fy="FY24",
        basis=ReportingBasis.CONSOLIDATED,
    )
    assert isinstance(fields, list)



# --- Line tier: borderless annual report notes ------------------------------
# Real Indian annual report notes carry no ruling lines, so pdfplumber returns
# no usable tables for them. These pages reproduce the text layout verbatim.

BORDERLESS_EXPENSE_NOTE = """MINDA CORPORATION LIMITED | Annual Report - 2025-26 363
2.34 Other expenses
Particulars For the year ended For the year ended
March 31, 2026 March 31, 2025
Job work charges 844 730
Legal and professional 436 488
Auditor Remuneration (refer note 2.35) 21 16
Loss allowance for expected credit loss - 34
Miscellaneous expenses 384 311
5,597 4,893"""

BORDERLESS_CONTINGENT_NOTE = """2.37 Contingent liabilities
Particulars As at As at
March 31, 2026 March 31, 2025
Claims against the Company not acknowledged as debts*
a) Income-tax ^ { Amount paid under protest is ` 2 million (previous year: 2)} 680 21
b) Sales tax/ VAT/GST {Amount paid under protest ` 14 million 321 82
(previous year: ` 85 million)}
c) Custom duty {Amount paid under protest ` 2 million 6 6
d) Bonus payable for financial year 2014-15 as per payment of Bonus Act, 1965 1 1
Others
Contingent liabilities related to joint ventures / associates 44 65
*including claim in respect of transferor companies merged into the Company
2.38 Something else 999 999"""


def _line_fields(page_text, wanted):
    from backend.app.acquisition.adapters.pdf.table_tier import extract_line_fields_from_page

    fields = extract_line_fields_from_page(
        page_text=page_text,
        page_no=7,
        wanted=set(wanted),
        source_filename="ar.pdf",
        doc_fy="FY26",
        basis=ReportingBasis.CONSOLIDATED,
        document_id="doc1",
    )
    return {f.field_name: f for f in fields}


def test_line_tier_reads_borderless_expense_note():
    got = _line_fields(BORDERLESS_EXPENSE_NOTE, {"audit_fees", "legal_fees"})

    assert got["legal_fees"].value == 436.0
    assert got["legal_fees"].period == "FY26"
    assert got["legal_fees_prior_year"].value == 488.0
    assert got["legal_fees_prior_year"].period == "FY25"
    assert got["audit_fees"].value == 21.0
    assert got["audit_fees"].page == 7


def test_line_tier_sums_contingent_liability_claims():
    got = _line_fields(BORDERLESS_CONTINGENT_NOTE, {"contingent_liabilities"})

    field = got["contingent_liabilities"]
    # 680 + 321 + 6 + 1 + 44; the trailing note 2.38 ends the block.
    assert field.value == 1052.0
    assert field.period == "FY26"
    assert field.confidence == Confidence.MEDIUM


def test_line_tier_prefers_an_explicit_total_row():
    page = """2.37 Contingent liabilities
Particulars As at As at
March 31, 2026 March 31, 2025
a) Income-tax 680 21
b) Custom duty 6 6
Total 686 27"""
    field = _line_fields(page, {"contingent_liabilities"})["contingent_liabilities"]

    assert field.value == 686.0
    assert field.confidence == Confidence.HIGH


def test_line_tier_ignores_accounting_policy_prose():
    page = """Provisions are recognised when the Company has a present obligation,
accounted for under Ind AS 37 (Provisions, Contingent Liabilities and
Contingent Assets). Revenue is measured based on the transaction price."""

    assert _line_fields(page, {"contingent_liabilities"}) == {}


def test_locate_basis_page_range_splits_the_two_sections():
    from backend.app.acquisition.adapters.pdf.anchors import locate_basis_page_range

    pages = [
        "Contents Independent Auditor's Report on the Audit of the Standalone Financial "
        "Statements 221 Report on the Audit of the Consolidated Financial Statements 305",
        "Board's Report",
        "Independent Auditor's Report To the Members Report on the Audit of the "
        "Standalone Financial Statements Opinion",
        "Notes to the Standalone Financial Statements",
        "Independent Auditor's Report To the Members Report on the Audit of the "
        "Consolidated Financial Statements Opinion",
        "Notes to the Consolidated Financial Statements",
    ]

    # The contents page names both sections and must start neither.
    assert locate_basis_page_range(pages, "STANDALONE") == (2, 4)
    assert locate_basis_page_range(pages, "CONSOLIDATED") == (4, 6)


def test_parse_clean_number_handles_annual_report_notation():
    from backend.app.acquisition.adapters.parsers.screener_tables import parse_clean_number

    assert parse_clean_number("1,234") == 1234.0
    assert parse_clean_number("(1,234)") == -1234.0
    assert parse_clean_number("` 420") == 420.0
    assert parse_clean_number("1,234*") == 1234.0
    assert parse_clean_number("—") is None
    assert parse_clean_number("Nil") is None
    # Two merged columns must not be read as one 5-digit number.
    assert parse_clean_number("673 14") is None
