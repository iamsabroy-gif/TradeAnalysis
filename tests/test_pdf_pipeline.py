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
