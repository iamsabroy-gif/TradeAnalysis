"""
FastAPI application for Phase 1 Gatekeeper.
Provides endpoints for evaluating companies, data acquisition via Screener and
analyst workbook uploads, retrieving versioned results, inspecting field coverage,
and rendering reports.
Strictly maps to Phase1-WebApp-Implementation-Plan.md §9 and Phase1-PhaseC-Scraper-Implementation-Plan.md §8.
"""

import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from backend.app.acquisition import (
    AnnualReportAdapter,
    CompanyIdentity,
    ScreenerAdapter,
    SourceDocument,
    WorkbookUploadAdapter,
    assemble,
    document_store,
    generate_workbook_template_bytes,
    registry,
    validate_and_hash_upload,
    validate_upload,
)
from backend.app.acquisition.adapters.pdf.classify import classify_pdf
from backend.app.acquisition.review.store import review_store
from backend.app.engine.orchestrator import run_phase1
from backend.app.models.coverage import FIELD_COVERAGE_MATRIX
from backend.app.models.enums import AuditOpinion, Confidence, PdfClass, ReportingBasis
from backend.app.models.schemas import CompanyInput, Phase1Result
from backend.app.rendering.analyst_table import render_analyst_report
from backend.app.rendering.investor_prose import render_investor_report
from tests.test_fixtures import make_clean_company_input

app = FastAPI(
    title="Phase 1 Gatekeeper API",
    version="1.0.0",
    description="Investment gatekeeper decision engine and reporting platform",
)

# Allow CORS for development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register default adapters in registry
screener_adapter = ScreenerAdapter()
workbook_adapter = WorkbookUploadAdapter()
annual_report_adapter = AnnualReportAdapter()
registry.register(screener_adapter, enabled=True)
registry.register(workbook_adapter, enabled=True)
registry.register(annual_report_adapter, enabled=True)

# In-memory store for evaluation results and inputs
RESULTS_STORE: Dict[str, Phase1Result] = {}
INPUTS_STORE: Dict[str, CompanyInput] = {}
TICKER_LATEST_MAP: Dict[str, str] = {}  # ticker -> latest_result_id

# Template environment
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "rendering" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


class EvaluationRequest(CompanyInput):
    prior_result_id: Optional[str] = None


class RunPipelineRequest(BaseModel):
    basis: ReportingBasis = ReportingBasis.CONSOLIDATED
    as_of_date: str = "2024-03-31"
    manual_overrides: Optional[Dict[str, Any]] = None
    prior_result_id: Optional[str] = None
    document_ids: Optional[List[str]] = None


class UpdateDocumentMetadataRequest(BaseModel):
    fiscal_year: Optional[str] = None
    basis: Optional[ReportingBasis] = None


class ExtractDocumentsRequest(BaseModel):
    document_ids: Optional[List[str]] = None
    basis: ReportingBasis = ReportingBasis.CONSOLIDATED


class ResolveReviewRequest(BaseModel):
    resolved_value: Any
    reviewer: str = "analyst"


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Phase 1 Gatekeeper"}


@app.get("/api/sources/health")
def get_sources_health():
    """Returns adapter registry health and circuit breaker status."""
    return registry.health_check_all()


@app.get("/api/coverage")
def get_field_coverage():
    """Returns the §3 Field Coverage Matrix enriched with phase owners."""
    return {
        "total_fields": len(FIELD_COVERAGE_MATRIX),
        "matrix": FIELD_COVERAGE_MATRIX,
    }


@app.get("/api/templates/workbook.xlsx")
def download_workbook_template():
    """Generates and serves the analyst workbook Excel template derived from FIELD_COVERAGE_MATRIX."""
    excel_bytes = generate_workbook_template_bytes()
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=phase1_analyst_workbook.xlsx"},
    )


@app.post("/api/tickers/{ticker}/uploads")
async def upload_ticker_file(ticker: str, file: UploadFile = File(...)):
    """
    Accepts and validates an analyst workbook or source export (.xlsx or .csv)
    without running the Decision Engine. Returns parsed fields preview + validation errors.
    """
    contents = await file.read()
    try:
        safe_name, content_hash = validate_and_hash_upload(file.filename or "upload.xlsx", contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    parse_res = workbook_adapter.parse_bytes(contents, filename=safe_name)

    return {
        "filename": safe_name,
        "content_hash": content_hash,
        "fields_count": len(parse_res.fields),
        "errors_count": len(parse_res.errors),
        "errors": [{"field_name": e.field_name, "message": e.message} for e in parse_res.errors],
        "fields": [
            {
                "field_name": f.field_name,
                "value": f.value,
                "confidence": f.confidence.value,
                "period": f.period,
                "basis": f.basis.value,
                "source": f.source,
            }
            for f in parse_res.fields
        ],
    }


@app.post("/api/tickers/{ticker}/run")
def run_ticker_pipeline(ticker: str, req: RunPipelineRequest):
    """
    Full Phase C acquisition and evaluation pipeline:
    1. Resolves CompanyIdentity.
    2. Runs enabled adapters (e.g. ScreenerAdapter).
    3. Assembles results against the declared basis and confidence floors.
    4. Evaluates through run_phase1().
    5. Returns verdict, reports, review items, and empty fields.
    """
    clean_ticker = ticker.strip().upper()
    ident = CompanyIdentity(
        ticker=clean_ticker,
        screener_code=clean_ticker,
        company_name=clean_ticker,
    )

    adapter_results = []
    adapter_errors = []
    # If ScreenerAdapter is enabled, fetch and parse
    if registry.is_enabled("ScreenerAdapter"):
        try:
            pages = screener_adapter.fetch(ident, basis=req.basis)
            parsed_res = screener_adapter.parse(pages)
            adapter_results.append(parsed_res)
            if parsed_res.errors:
                adapter_errors.extend([f"{e.field_name}: {e.message}" for e in parsed_res.errors])
        except Exception as e:
            # Degrades gracefully; does not crash pipeline
            adapter_errors.append(f"Screener acquisition failed: {str(e)}")

    # If AnnualReportAdapter is enabled, extract from uploaded PDFs
    if registry.is_enabled("AnnualReportAdapter"):
        try:
            docs = document_store.list_for_ticker(clean_ticker)
            if req.document_ids:
                docs = [d for d in docs if d.doc_id in req.document_ids]
            if docs:
                pdf_res = annual_report_adapter.parse_documents(docs)
                adapter_results.append(pdf_res)
                if pdf_res.errors:
                    adapter_errors.extend([f"{e.field_name}: {e.message}" for e in pdf_res.errors])
        except Exception as e:
            adapter_errors.append(f"PDF Annual Report extraction failed: {str(e)}")

    # Assemble CompanyInput
    company_input, review_items = assemble(
        identity=ident,
        as_of_date=req.as_of_date,
        basis=req.basis,
        results=adapter_results,
        manual_overrides=req.manual_overrides,
    )

    # Persist review queue items
    if review_items:
        review_store.add_items(review_items)

    # Check for prior result if re-evaluating
    prior: Optional[Phase1Result] = None
    if req.prior_result_id and req.prior_result_id in RESULTS_STORE:
        prior = RESULTS_STORE[req.prior_result_id]

    result = run_phase1(company_input, prior=prior)

    # Store
    RESULTS_STORE[result.result_id] = result
    INPUTS_STORE[result.result_id] = company_input
    TICKER_LATEST_MAP[clean_ticker] = result.result_id

    # Compute which check-bearing fields are still empty
    check_fields = [
        "audit_opinion",
        "auditor_resigned_mid_tenure_last_3y",
        "legal_fees",
        "audit_fees",
        "promoter_holding_pct_of_company",
        "pledged_pct_of_promoter_holding",
        "rpt_sales_plus_purchases",
        "revenue",
        "contingent_liabilities",
        "net_worth",
        "cfo_last_5y",
        "pat_last_5y",
        "cfo_changes_last_3y",
        "restatement_of_past_accounts",
    ]
    empty_fields = [f for f in check_fields if getattr(company_input, f, None) is None]

    investor_report = render_investor_report(result)
    analyst_report = render_analyst_report(result, company_input)

    return {
        "result": result.model_dump(),
        "investor_report": investor_report,
        "analyst_report": analyst_report,
        "review_items": [item.model_dump() for item in review_items],
        "empty_fields": empty_fields,
        "company_input": company_input.model_dump(),
        "adapter_errors": adapter_errors,
    }


@app.post("/api/tickers/{ticker}/documents")
async def upload_ticker_documents(
    ticker: str,
    files: List[UploadFile] = File(...),
    fiscal_year: Optional[str] = Form(None),
    basis: Optional[ReportingBasis] = Form(None),
):
    """
    Accepts, validates, classifies, and stores one or more Annual Report PDFs.
    """
    clean_ticker = ticker.strip().upper()
    saved_docs = []
    errors = []

    for file in files:
        contents = await file.read()
        try:
            safe_name, content_hash = validate_upload(file.filename or "report.pdf", contents)
        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})
            continue

        pdf_class, page_count, detected_fy = classify_pdf(contents)
        doc_fy = fiscal_year or detected_fy
        doc = SourceDocument(
            doc_id=content_hash[:16],
            ticker=clean_ticker,
            filename=safe_name,
            fiscal_year=doc_fy,
            basis=basis or ReportingBasis.CONSOLIDATED,
            pdf_class=pdf_class,
            page_count=page_count,
            stored_path="",
            uploaded_at="",
        )
        saved = document_store.save(doc, contents)
        saved_docs.append({
            "doc_id": saved.doc_id,
            "ticker": saved.ticker,
            "filename": saved.filename,
            "fiscal_year": saved.fiscal_year,
            "basis": saved.basis.value if isinstance(saved.basis, ReportingBasis) else saved.basis,
            "pdf_class": saved.pdf_class.value if isinstance(saved.pdf_class, PdfClass) else saved.pdf_class,
            "page_count": saved.page_count,
            "uploaded_at": saved.uploaded_at,
        })

    return {
        "ticker": clean_ticker,
        "documents": saved_docs,
        "errors": errors,
    }


@app.get("/api/tickers/{ticker}/documents")
def list_ticker_documents(ticker: str):
    """Lists all stored Annual Report documents for a ticker."""
    clean_ticker = ticker.strip().upper()
    docs = document_store.list_for_ticker(clean_ticker)
    return {
        "ticker": clean_ticker,
        "documents": [
            {
                "doc_id": d.doc_id,
                "ticker": d.ticker,
                "filename": d.filename,
                "fiscal_year": d.fiscal_year,
                "basis": d.basis.value if isinstance(d.basis, ReportingBasis) else d.basis,
                "pdf_class": d.pdf_class.value if isinstance(d.pdf_class, PdfClass) else d.pdf_class,
                "page_count": d.page_count,
                "uploaded_at": d.uploaded_at,
            }
            for d in docs
        ],
    }


@app.patch("/api/tickers/{ticker}/documents/{doc_id}")
def update_document_metadata(ticker: str, doc_id: str, req: UpdateDocumentMetadataRequest):
    """Updates fiscal year or reporting basis metadata for a stored document."""
    clean_ticker = ticker.strip().upper()
    updated = document_store.update(clean_ticker, doc_id, fiscal_year=req.fiscal_year, basis=req.basis)
    if not updated:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "doc_id": updated.doc_id,
        "ticker": updated.ticker,
        "filename": updated.filename,
        "fiscal_year": updated.fiscal_year,
        "basis": updated.basis.value if isinstance(updated.basis, ReportingBasis) else updated.basis,
        "pdf_class": updated.pdf_class.value if isinstance(updated.pdf_class, PdfClass) else updated.pdf_class,
        "page_count": updated.page_count,
        "uploaded_at": updated.uploaded_at,
    }


@app.delete("/api/tickers/{ticker}/documents/{doc_id}")
def delete_ticker_document(ticker: str, doc_id: str):
    """Deletes a stored document and its metadata sidecar."""
    clean_ticker = ticker.strip().upper()
    deleted = document_store.delete(clean_ticker, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "doc_id": doc_id}


@app.post("/api/tickers/{ticker}/documents/extract")
def extract_ticker_documents(ticker: str, req: ExtractDocumentsRequest):
    """
    Runs extraction on stored documents for a ticker without running full evaluation.
    Returns parsed fields with provenance (page citations, extraction method, confidence).
    """
    clean_ticker = ticker.strip().upper()
    docs = document_store.list_for_ticker(clean_ticker)
    if req.document_ids:
        docs = [d for d in docs if d.doc_id in req.document_ids]

    if not docs:
        raise HTTPException(status_code=404, detail="No documents found for extraction")

    res = annual_report_adapter.parse_documents(docs)

    return {
        "ticker": clean_ticker,
        "documents_count": len(docs),
        "fields_count": len(res.fields),
        "errors_count": len(res.errors),
        "errors": [{"field_name": e.field_name, "message": e.message} for e in res.errors],
        "fields": [
            {
                "field_name": f.field_name,
                "value": f.value,
                "confidence": f.confidence.value,
                "period": f.period,
                "basis": f.basis.value,
                "source": f.source,
                "page": f.page,
                "document_id": f.document_id,
                "raw_snippet": f.raw_snippet,
            }
            for f in res.fields
        ],
    }


@app.get("/api/tickers/{ticker}/review")
def list_review_queue(ticker: str):
    """Lists pending review queue items for a ticker."""
    clean_ticker = ticker.strip().upper()
    items = review_store.list_for_ticker(clean_ticker)
    return {"ticker": clean_ticker, "items": [item.model_dump() for item in items]}


@app.post("/api/review/{item_id}/resolve")
def resolve_review_item(item_id: str, req: ResolveReviewRequest):
    """Resolves a pending review queue item with an analyst decision."""
    item = review_store.resolve(item_id, resolved_value=req.resolved_value, reviewer=req.reviewer)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return {"status": "resolved", "item_id": item_id, "resolved_value": req.resolved_value}


@app.get("/api/fixtures")
def get_sample_fixtures():
    """
    Returns pre-built test fixtures matching Phase1-Algorithms.md §11
    to enable one-click testing in the web UI.
    """
    clean = make_clean_company_input()

    f2 = clean.model_copy(deep=True)
    f2.ticker = "REJECT_AUDIT"
    f2.audit_opinion = AuditOpinion.QUALIFIED

    f3 = clean.model_copy(deep=True)
    f3.ticker = "REJECT_PLEDGE"
    f3.pledged_pct_of_promoter_holding = 34.0
    f3.pledged_pct_history_last_4q = [25.0, 28.0, 30.0, 34.0]

    f4 = clean.model_copy(deep=True)
    f4.ticker = "PSU_PASSED"
    f4.govt_shareholding_pct = 55.0
    f4.promoter_holding_pct_of_company = None
    f4.pledged_pct_of_promoter_holding = None
    f4.pledged_pct_history_last_4q = None

    f9 = clean.model_copy(deep=True)
    f9.ticker = "HOLD_MISSING_DATA"
    f9.net_worth = None

    f14 = clean.model_copy(deep=True)
    f14.ticker = "HOLD_BASIS_MISMATCH"
    if "revenue" in f14.provenance:
        f14.provenance["revenue"].basis = ReportingBasis.STANDALONE

    return {
        "fixtures": [
            {
                "id": "fixture_1_clean",
                "label": "Fixture 1: Clean Happy Path (Tata Motors)",
                "expected": "CLEARED_TO_PHASE_2",
                "data": clean.model_dump(),
            },
            {
                "id": "fixture_2_qualified_audit",
                "label": "Fixture 2: Qualified Audit Opinion",
                "expected": "REJECT (Check 1)",
                "data": f2.model_dump(),
            },
            {
                "id": "fixture_3_high_pledge",
                "label": "Fixture 3: High & Rising Promoter Pledge (34%)",
                "expected": "REJECT (Check 2)",
                "data": f3.model_dump(),
            },
            {
                "id": "fixture_4_govt_psu",
                "label": "Fixture 4: Govt PSU 55% Stake Auto-Pass",
                "expected": "CLEARED_TO_PHASE_2 (Check 2 exempt)",
                "data": f4.model_dump(),
            },
            {
                "id": "fixture_9_missing_net_worth",
                "label": "Fixture 9: Missing Net Worth (Hold Inconclusive)",
                "expected": "HOLD_INCONCLUSIVE (Check 4)",
                "data": f9.model_dump(),
            },
            {
                "id": "fixture_14_basis_mismatch",
                "label": "Fixture 14: Basis Mismatch (Consolidated RPT vs Standalone Rev)",
                "expected": "HOLD_INCONCLUSIVE (Check 3)",
                "data": f14.model_dump(),
            },
        ]
    }


@app.post("/api/evaluate")
def evaluate_ticker(payload: EvaluationRequest):
    """
    Evaluates CompanyInput directly through the Decision Engine.
    Handles versioning if prior_result_id is provided.
    """
    prior: Optional[Phase1Result] = None
    if payload.prior_result_id and payload.prior_result_id in RESULTS_STORE:
        prior = RESULTS_STORE[payload.prior_result_id]

    input_data = CompanyInput(**payload.model_dump(exclude={"prior_result_id"}))
    result = run_phase1(input_data, prior=prior)

    # Persist in-memory
    RESULTS_STORE[result.result_id] = result
    INPUTS_STORE[result.result_id] = input_data
    TICKER_LATEST_MAP[result.ticker] = result.result_id

    investor_report = render_investor_report(result)
    analyst_report = render_analyst_report(result, input_data)

    return {
        "result": result.model_dump(),
        "investor_report": investor_report,
        "analyst_report": analyst_report,
    }


@app.get("/api/results/{result_id}")
def get_result(result_id: str):
    """Fetches a specific evaluation revision."""
    if result_id not in RESULTS_STORE:
        raise HTTPException(status_code=404, detail="Result not found")
    res = RESULTS_STORE[result_id]
    inp = INPUTS_STORE.get(result_id, CompanyInput(ticker=res.ticker, as_of_date=res.as_of_date))
    return {
        "result": res.model_dump(),
        "investor_report": render_investor_report(res),
        "analyst_report": render_analyst_report(res, inp),
    }


@app.get("/api/tickers/{ticker}/latest")
def get_latest_ticker_result(ticker: str):
    """Fetches the latest evaluation for a ticker."""
    if ticker not in TICKER_LATEST_MAP:
        raise HTTPException(status_code=404, detail=f"No results found for ticker {ticker}")
    latest_id = TICKER_LATEST_MAP[ticker]
    return get_result(latest_id)


@app.get("/api/reports/{result_id}/html", response_class=HTMLResponse)
def render_report_html(result_id: str):
    """
    Renders unified HTML report for web view and PDF printing.
    """
    if result_id not in RESULTS_STORE:
        raise HTTPException(status_code=404, detail="Result not found")
    res = RESULTS_STORE[result_id]
    inp = INPUTS_STORE.get(result_id, CompanyInput(ticker=res.ticker, as_of_date=res.as_of_date))

    investor_data = render_investor_report(res)
    analyst_data = render_analyst_report(res, inp)

    template = jinja_env.get_template("report.html")
    rendered = template.render(
        investor=investor_data,
        analyst=analyst_data,
    )
    return HTMLResponse(content=rendered)


# Mount frontend dist static files if built
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
