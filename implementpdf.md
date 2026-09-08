# Annual Report PDF Ingestion — Implementation Plan

**Scope:** add multi-PDF annual report upload and parsing to the Phase 1 Gatekeeper app.
**Status of codebase reviewed:** `backend/app/acquisition`, `backend/app/api/main.py`, `backend/app/models`, `frontend/src/App.jsx`, and `Docs/Rules/*`.

---

## 1. Review — where PDF support actually stands

**Yes, this is feasible, and the codebase is already shaped for it.** Phase D (the PDF
extractor) is fully specified in `Docs/Rules/Phase1-WebApp-Implementation-Plan.md` §5 but
is entirely unimplemented — no PDF code exists anywhere under `backend/`.

### Already in our favour

| Existing asset | Where | Why it matters |
| :-- | :-- | :-- |
| `OWNER_PRIORITY` already ranks PDF tiers | `backend/app/acquisition/assembler.py:26-35` | `"PDF tier 1 (D)": 80`, `"PDF tier 2 (D)": 75`, `"PDF tier 2/3 (D)": 70` — above `Screener (C): 50`, below workbook/manual |
| Coverage matrix already assigns those owners | `backend/app/models/coverage.py` | `audit_opinion`, `legal_fees`, `rpt_sales_plus_purchases`, `contingent_liabilities`, `net_worth` etc. are already declared PDF-owned |
| `.pdf` already whitelisted, 100 MB cap defined | `backend/app/acquisition/uploads/intake.py:11` | `MAX_PDF_SIZE_BYTES` exists and `.pdf` passes extension validation |
| `ExtractionMethod` has PDF members | `backend/app/models/enums.py:30-36` | `NATIVE_TEXT`, `TABLE_PARSE`, `OCR` already defined |
| `ReviewQueueItem` carries PDF provenance | `backend/app/models/schemas.py:123-139` | `source_page` and `source_url` already present |

**Consequence:** a PDF adapter that emits `ExtractedField` objects slots into precedence,
basis filtering, and confidence floors with *zero* assembler changes for scalar fields.

### What actually blocks it

1. **The upload endpoint is a trap for PDFs.** `backend/app/api/main.py:104` calls
   `validate_and_hash_upload(...)` with the *default* `max_bytes` (the 2 MB workbook cap),
   so a real annual report is rejected on size. If it weren't, line 112 hands the bytes
   straight to `workbook_adapter.parse_bytes()`, which would fail inside `openpyxl`.
   `.pdf` is allowed by the validator but has no route.
2. **Single-file only.** `file: UploadFile = File(...)` — no multi-file, no per-document identity.
3. **`RawPage.content` is `str`.** PDFs are bytes. The `fetch`/`parse` split in
   `backend/app/acquisition/base.py` assumes text pages.
4. **No document store.** `var/cache/` is an HTML-keyed `FileCache`; there is no
   `raw_documents` registry, so nothing survives a request.
5. **The assembler keys candidates by `field_name` alone**
   (`assembler.py:80-85`). Five annual reports each emitting `net_worth` collide into one
   bucket sorted only by owner priority — FY20's net worth could beat FY24's.
   **This is the single most important change for multi-PDF.**
6. **The review queue is fire-and-forget.** `assemble()` returns `review_items`,
   `main.py:206` returns them in the response, and nothing stores or resolves them.
   §5.4 of the plan is load-bearing for hard PDFs and does not exist.
7. **Everything is synchronous.** PDF extraction is seconds-to-minutes per document;
   `/api/tickers/{ticker}/run` would time out.
8. **`requirements.txt` has no PDF libraries.**

---

## 2. Design decision — how many annual reports?

§5 of the WebApp plan says *do not* fetch five annual reports by default: the latest report
supplies Checks 1, 3, 4 and 6, and Screener supplies the 5-year CFO/PAT series for Check 5.
That is correct for **auto-fetch**.

For **analyst upload**, multiple reports buy three things Screener cannot:

- **(a)** `cfo_last_5y` / `pat_last_5y` at annual-report confidence rather than provisional Screener values.
- **(b)** `legal_fees_prior_year` when the current report's comparative column is missing or unparseable.
- **(c)** **Restatement detection.** Comparing FY23's reported figure against FY24's
  comparative column for the same year is a direct, high-confidence signal for
  `restatement_of_past_accounts` — a field that today has **no automated source at all**.

**Rule adopted:** latest annual report required; prior years optional and additive.

---

## 3. Implementation stages

### Stage 0 — Unblock the PDF path (small, do first)

- `intake.py`: add `validate_upload(filename, bytes)` that picks the size cap by extension
  (2 MB for `.xlsx`/`.csv`, 100 MB for `.pdf`) instead of the caller passing `max_bytes`.
  Add a magic-byte check (`%PDF-`) so the extension alone is not trusted.
- `main.py:96-134`: branch on extension — `.pdf` routes to the new PDF path, not `workbook_adapter`.
- `requirements.txt`: add `pymupdf`, `pdfplumber`. Defer `camelot-py` / `pytesseract` to
  Stage 7 — both drag in system dependencies (Ghostscript, Tesseract), which the WebApp
  plan flags at §5 under "dependency caveats".

### Stage 1 — Document store and multi-file intake

New `backend/app/acquisition/documents/store.py`:

- `SourceDocument` dataclass: `doc_id` (= content sha256), `ticker`, `filename`,
  `fiscal_year`, `basis`, `pdf_class`, `page_count`, `stored_path`, `uploaded_at`, `uploader`.
- File-backed store at `var/documents/{ticker}/{doc_id}.pdf` plus a JSON sidecar, mirroring
  the existing `FileCache` pattern so it is swappable for S3/MinIO later (WebApp plan §2).
- Content-hash dedupe: re-uploading the same report is a no-op, not a duplicate candidate.

Extend `backend/app/acquisition/types.py`:

- `ExtractedField` gains `document_id: Optional[str] = None` — a frozen dataclass with a
  default, so no existing call site breaks.
- Add a `PdfClass` enum (`NATIVE_TEXT` / `HYBRID` / `SCANNED_IMAGE_ONLY`) to `enums.py`.

New endpoints:

- `POST /api/tickers/{ticker}/documents` — `files: List[UploadFile]`, accepts N PDFs in one
  call. Validates, hashes, stores, classifies. Returns
  `[{doc_id, filename, detected_fiscal_year, pdf_class, page_count, warnings}]`.
  **Fiscal year is detected but analyst-confirmable** — the `report_fiscal_year` anchor in
  §5.5 is not reliable enough to trust silently, and a wrong fiscal-year assignment poisons
  every field extracted from that document.
- `GET /api/tickers/{ticker}/documents` — list.
- `PATCH /api/tickers/{ticker}/documents/{doc_id}` — correct `fiscal_year` / `basis`.
- `DELETE /api/tickers/{ticker}/documents/{doc_id}`.

### Stage 2 — Classifier and extraction ladder (tiers 1–2)

New package `backend/app/acquisition/adapters/pdf/`:

- **`classify.py`** — implements §5.1 exactly:
  `text_layer_ratio = extractable_chars / page_count` → returns the `PdfClass`.
  Stored on the document so re-runs skip reclassification.
- **`text_tier.py`** (tier 1, PyMuPDF) — page-indexed text plus a fuzzy section locator
  returning `(page, char_span, matched_header, match_score)`.
- **`table_tier.py`** (tier 2, pdfplumber) — `extract_tables()` over the pages the anchor
  located, plus **column-header → fiscal-year resolution**. §5.2 is blunt about this: an
  unresolvable header sends the value to review rather than defaulting to column 1.
  Getting this wrong silently swaps `legal_fees` and `legal_fees_prior_year`, which inverts
  the Check 1 surge sub-check.
- **`anchors.py`** — the §5.5 `SECTION_PATTERNS` library, versioned, including the
  consolidated-vs-standalone disambiguation that `balance_sheet_equity` and
  `revenue_from_operations` require (an annual report contains both).

### Stage 3 — `AnnualReportAdapter`

`backend/app/acquisition/adapters/pdf/annual_report.py`, implementing `SourceAdapter`:

- `owns_fields` = exactly the fields whose matrix `owner` starts with `"PDF tier"` —
  derived from `FIELD_COVERAGE_MATRIX` rather than hardcoded, keeping the matrix the single
  source of truth (the same technique `WorkbookUploadAdapter` uses).
- `parse_document(doc: SourceDocument) -> AdapterResult` as the real entry point;
  `fetch()` returns `[]` like the workbook adapter, since documents arrive by upload.
- Per-field extractors, each returning an `ExtractedField` with `document_id`, `page`,
  `raw_snippet`, resolved `period`, and confidence per §5.3 — HIGH for exact-anchor
  tier 1/2, MEDIUM for a fuzzy anchor or tier-3 repair, LOW for OCR or unanchored regex.
- Start with the highest-value, lowest-risk set: `audit_opinion`, `contingent_liabilities`,
  `net_worth`, `revenue`, `rpt_sales_plus_purchases`, `legal_fees` / `legal_fees_prior_year`,
  `audit_fees`. Leave `restatement_of_past_accounts` and `cfo_changes_last_3y` — both
  HIGH-floored narrative fields — to Stage 4 or manual entry.

### Stage 4 — Multi-year assembly (the core of "multiple annual reports")

This is the real work, in `backend/app/acquisition/assembler.py`:

1. **Key candidates by `(field_name, period)`, not `field_name`** — `assembler.py:80`.
   Without this, five annual reports are five competing answers to one question.
2. **Add a period-selection step** before the existing priority sort. For scalar fields the
   run's fiscal year wins (already derived at `assembler.py:191` as `run_fy`); a value from a
   non-run fiscal year is used only where the schema explicitly wants it
   (`legal_fees_prior_year` → `prior_fy`). Off-period candidates for a scalar field are
   dropped silently, not queued for review — they are expected, not anomalous.
3. **Add series assembly** for `cfo_last_5y` and `pat_last_5y`: collect `(period, value)`
   across documents, sort by fiscal year descending, and emit the list only if the years are
   contiguous and complete. A gap sends the series to review rather than producing a wrong
   Check 5 ratio from four years labelled as five.
4. **Cross-document restatement check** — the payoff for multi-year. Where AR(N) and AR(N-1)
   both report the same fiscal year for a given field, compare them. A material divergence
   sets `restatement_of_past_accounts` with HIGH-confidence, fully cited provenance and a
   `raw_snippet` naming both documents.
5. **Near-threshold escalation** (§5.3 table) — a MEDIUM numeric whose computed ratio lands
   inside the escalation band goes to review regardless of confidence. This exists nowhere
   today. It belongs in the assembler next to the confidence-floor check at
   `assembler.py:148`, because it needs both the value and the check's threshold.

Extend `RunPipelineRequest` with `document_ids: Optional[List[str]] = None` so a run declares
which reports it used. `/api/tickers/{ticker}/run` loads them, calls `parse_document` per
document, and appends each `AdapterResult` to the existing `adapter_results` list — the
existing `assemble()` signature already takes `List[AdapterResult]` and needs no change.

### Stage 5 — Review queue persistence

Add `REVIEW_STORE: Dict[str, ReviewQueueItem]` alongside the existing in-memory stores, plus
`GET /api/tickers/{ticker}/review` and `POST /api/review/{item_id}/resolve`. Resolution
writes back as a manual override, append-only, and re-running produces a **new**
`Phase1Result` revision (§5.4.3–4).

Without this, every LOW-confidence PDF extraction is a dead end and hard PDFs have no
degradation path — which is precisely what §5.4 exists to prevent.

### Stage 6 — Async execution

PDF runs move to a background job, with `GET /api/jobs/{job_id}` for status. The WebApp plan
calls for Celery + Redis; for a single-user local app, FastAPI `BackgroundTasks` with an
in-memory job dict is the honest first step and keeps the deployment story unchanged.

### Stage 7 — Tiers 3–4 (defer)

`camelot-py` and `pytesseract` / OpenCV, only if tiers 1–2 measurably fail on real filings.
Both add system-level dependencies (Ghostscript, Tesseract) that complicate deployment for
what may be a small marginal gain. §5.4.6's per-filer extraction-success metric tells you
whether it is worth it — instrument first, then decide.

### Frontend

`frontend/src/App.jsx` currently has one `fileInputRef` and a single-file `handleFileProcess`.
Add a parallel **Annual Reports** panel:

- multi-file input (`multiple`, `accept=".pdf"`),
- a table of uploaded documents with editable fiscal year and basis,
- per-document extraction status.

Reuse the existing dropzone handler by branching on file extension.
`UploadValidationModal` extends naturally to show extracted fields with page citations.

---

## 4. Suggested first slice

**Stages 0 + 1, plus a tier-1-only `audit_opinion` extractor.**

That is one narrative field — HIGH-floored, verdict-flipping, with a clean section anchor.
It proves the document store, the adapter, assembler precedence, and the provenance chain
end to end, and it removes Check 1's hardest field from the manual list.
