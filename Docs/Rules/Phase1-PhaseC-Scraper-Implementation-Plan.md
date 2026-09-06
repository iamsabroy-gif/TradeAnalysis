# Phase C — Data Acquisition Layer (Web Scraper) Implementation Plan

*Turns §4 of `Phase1-WebApp-Implementation-Plan.md` into a buildable module. Scope is
**Phase C only**: the adapter framework, the shared HTTP/cache/resilience layer, the
ScreenerAdapter, the **upload adapters** (§5A) that let a user supply the same data as a
file instead of a scrape, and the assembler that turns adapter output into a
`CompanyInput` + provenance map. Phases D–F (PDF extractor, OCR, BSE/NSE/SEBI adapters) are explicitly
out of scope and are only accounted for at the seams.*

*Traceability: implements plan §4.1, §4.2, §11 Phase C. Consumes the §3 field coverage
matrix. Does not introduce any rule not already in `Phase1-Rules.md` §8.1–8.3.*

---

## 0. Blocking precondition — settle §12.1 before writing adapter code

Plan §12.1 lists scraping legality / terms of service as **blocking, not advisory**, and
it is still open. It changes the architecture, not just the rollout:

| Answer to §12.1 | What Phase C becomes |
| :-- | :-- |
| Personal-use, operator-run | Build as specified below. Adapters ship enabled, credentials are the operator's own. |
| Internal analyst team | Same code, but adapters ship **disabled by default** behind `SOURCES_ENABLED`, and the operator enables per source. |
| External product | ScreenerAdapter is not viable as a redistributed scrape. §4 becomes licensed-data or upload-first: build C1–C3 plus §5A's upload adapters and skip C4b entirely. |

Everything in §1–§4 below (framework, HTTP layer, assembler, provenance) survives all
three answers, and so does §5A (upload adapters) — uploads are a legitimate input path
under every one of them. Only §5 (ScreenerAdapter) is contingent. **Build C1–C3 and C4a
in parallel with that decision; do not start C4b until it is answered.**

This is the practical reason the upload path is in Phase C rather than deferred: it means
the phase ships a working end-to-end product no matter how §12.1 lands. The scrape then
becomes a convenience layer over an input route that already works, rather than the only
route and therefore a single point of failure.

---

## 1. What Phase C actually delivers

**Before:** the frontend asks a human to type `pledged_pct_of_promoter_holding`,
`promoter_holding_pct_of_company`, `contingent_liabilities` and `net_worth` into a form,
because nothing populates `CompanyInput`. The engine, rendering layer and versioning all
work; there is no acquisition layer at all.

**After Phase C:** entering a ticker populates these fields automatically, each with a
`FieldProvenance` entry, and the form becomes a *review-and-override* surface rather than
a data-entry surface.

| `CompanyInput` field | Check | After Phase C | Notes |
| :-- | :-: | :-- | :-- |
| `govt_shareholding_pct` | 2 | **Auto** | Also drives `classify_company_type` |
| `promoter_holding_pct_of_company` | 2 | **Auto** | |
| `pledged_pct_of_promoter_holding` | 2 | **Auto** | BSE cross-check deferred to Phase F |
| `pledged_pct_history_last_4q` | 2 | **Auto** | Trailing 4–8 quarters |
| `pledged_pct_of_total_shares` | 2 | **Derived** | Existing `derive_pledged_pct_of_total_shares()` — no scrape needed |
| `cfo_last_5y` | 5 | **Auto** | |
| `pat_last_5y` | 5 | **Auto** | |
| `revenue` | 3 | **Auto (provisional)** | Screener P&L; superseded by the AR figure in Phase D |
| `net_worth` | 4 | **Auto (provisional)** | Screener balance sheet; superseded in Phase D |
| `years_of_track_record_available` | gate | **Auto** | `min(years since listing, FYs of financials retrieved)` |
| `data_basis` | all ratios | **Set by orchestrator** | Default `CONSOLIDATED` per rules §8.1 |
| — AR PDF links | — | **Captured, not parsed** | Stored for Phase D handoff |
| `contingent_liabilities`, `rpt_sales_plus_purchases`, `legal_fees`, `audit_fees`, `audit_opinion`, … | 1,3,4,6 | **Manual or uploaded** | PDF-owned (Phase D). The form keeps these inputs, and §5A's workbook upload can supply them in bulk |

Be explicit about that last row in the UI. Phase C removes two of the four boxes on the
current screen (pledge %, promoter holding) and leaves two (contingent liabilities is
PDF-owned; net worth gets a provisional Screener value the analyst can accept or
override). Anyone expecting "type a ticker, get a verdict" will otherwise read the
remaining inputs as a bug.

**And there is a second route to the same table.** Everything above describes the scrape
path. §5A adds an upload path that reaches the identical assembler: the user supplies a
filled workbook or a source-produced export instead of the app fetching anything. Via
upload, *every* row in the table above can be populated in Phase C — including the
PDF-owned fields that the scraper cannot reach until Phase D. The two routes are not
alternatives to choose between at build time; a single run can mix them, field by field.

---

## 2. Module layout

```
backend/app/acquisition/
    __init__.py
    types.py            # RawPage, ExtractedField, AdapterResult, exceptions
    base.py             # SourceAdapter ABC
    http_client.py      # SourceHttpClient: rate limit, backoff, circuit breaker, UA
    cache.py            # CacheBackend protocol + FileCache (dev) / RedisCache (prod)
    robots.py           # startup robots.txt check + logging
    assembler.py        # AdapterResult[] -> (CompanyInput, provenance map)
    registry.py         # name -> adapter instance; drives /api/sources/health
    uploads/
        __init__.py
        intake.py       # size/type sniffing, hashing, safe storage (§5A.5)
        template.py     # generates the workbook template FROM the coverage matrix
        workbook.py     # WorkbookUploadAdapter  (kind A)
    adapters/
        __init__.py
        screener.py     # ScreenerAdapter (C4b)
        screener_export.py       # ScreenerExportAdapter, XLSX (kind B)
        parsers/
            screener_tables.py   # pure HTML  -> values, no I/O
            screener_sheets.py   # pure XLSX  -> values, no I/O
```

Note that `screener.py` and `screener_export.py` target the same tables from different
containers, so their parsers should converge on one row-mapping table shared between
them — the field list, row labels and structural assertions in §5.2 are the same
regardless of whether the bytes arrived over HTTP or in an upload.

**Prerequisite refactor (do this first, it is ten minutes).**
[backend/app/api/main.py:19](backend/app/api/main.py#L19) imports `FIELD_COVERAGE_MATRIX`
from `tests/test_coverage_matrix.py`. The matrix stops being a test artefact in Phase C —
the assembler reads its `confidence_floor` at runtime to decide what may populate
`CompanyInput`. Move it to `backend/app/models/coverage.py`, have both
[main.py](backend/app/api/main.py) and
[tests/test_coverage_matrix.py](tests/test_coverage_matrix.py) import from there, and add
an `owner_phase` key so `/api/coverage` can report "expected auto in C" vs "still manual".
Production code importing from `tests/` will otherwise break the moment the app is
packaged without its test suite.

---

## 3. Core contracts

### 3.1 Types (`types.py`)

```python
@dataclass(frozen=True)
class RawPage:
    source: str            # "screener"
    url: str               # canonical, post-redirect
    content: str           # HTML or JSON body
    fetched_at: datetime
    from_cache: bool
    basis: ReportingBasis  # which basis this URL represents

@dataclass(frozen=True)
class ExtractedField:
    field_name: str        # must be a CompanyInput attribute name
    value: Any
    confidence: Confidence
    extraction_method: ExtractionMethod  # HTML_SCRAPE for all of Phase C
    source: str            # the URL
    period: str            # "FY24", "Q3FY25", "as-of 2025-06-30"
    basis: ReportingBasis
    raw_snippet: str       # the exact table row the number came from
    page: int | None = None

@dataclass
class AdapterResult:
    adapter: str
    fields: list[ExtractedField]
    documents: list[DocumentRef]   # AR PDF links for Phase D — captured, not fetched
    errors: list[AdapterError]     # non-fatal, per-field
    pages: list[RawPage]           # for audit / raw_documents persistence
```

`ExtractedField` maps 1:1 onto plan §5.3's struct and onto
[`FieldProvenance`](backend/app/models/schemas.py) — the assembler's job is a mechanical
translation, no field invented at that layer.

Exceptions: `LayoutChangedError` (parse assertion failed — distinct from a network
failure, per §4.2), `SourceUnavailableError` (network/circuit open),
`TickerNotFoundError`, `AmbiguousTickerError`.

### 3.2 The adapter interface (`base.py`)

```python
class SourceAdapter(ABC):
    name: str
    owns_fields: frozenset[str]       # cross-checked against the coverage matrix at import

    @abstractmethod
    def fetch(self, ident: CompanyIdentity, basis: ReportingBasis) -> list[RawPage]: ...

    @abstractmethod
    def parse(self, pages: list[RawPage]) -> AdapterResult: ...

    @abstractmethod
    def health_check(self) -> HealthStatus: ...
```

Two rules that make this testable, and both matter more than they look:

1. **`fetch` does all I/O; `parse` does none.** Every parser is a pure function from HTML
   string to values. This is what lets the whole adapter suite run in CI against recorded
   HTML with the network unplugged (§7).
2. **`parse` never raises for a missing field.** A field it cannot find is absent from
   `fields` and present in `errors`. Only a *structural* violation ("the shareholding
   table should have ≥ 4 quarter columns, found 1") raises `LayoutChangedError`. This is
   the §4.2 distinction between "no data" (→ `null` → INCONCLUSIVE, correct) and "the site
   changed and we are now reading garbage" (→ adapter fix, loud).

### 3.3 `CompanyIdentity`

Plan §10 already concedes a bare ticker is ambiguous across exchanges. Resolve it once,
at the front of the pipeline, rather than in each adapter:

```python
@dataclass(frozen=True)
class CompanyIdentity:
    ticker: str            # as the user typed it
    screener_code: str     # Screener's URL slug
    bse_scrip_code: str | None   # Phase F
    nse_symbol: str | None       # Phase F
    company_name: str
    listing_date: date | None
```

Phase C resolves this from Screener's own search endpoint and caches it in the
`companies` table (plan §10). Ambiguity raises `AmbiguousTickerError`, which the API
surfaces as a 409 with candidates for the analyst to pick — not a silent first-match.

---

## 4. Shared infrastructure (C2) — build before any adapter

All four §4.2 requirements live in one client, so adapter #2 through #5 inherit them for
free.

**Cache key** — `sha256(source | canonical_url | basis)`, value `{body, fetched_at,
status, final_url}`, TTL default 24h, per-source override. Keyed by URL and basis, never
by date (§4.2 is explicit about why). `fetched_at` is stored as a *value* so provenance
can report the true fetch time even on a cache hit — a cached page's provenance must say
when the data was fetched, not when the run happened. `FileCache` under
`var/cache/` for dev; Redis in prod, same interface.

**Rate limiting** — a per-source token bucket, default 1 request / 1.5s, configurable via
`SOURCE_RATE_LIMIT_<NAME>`. Applies across concurrent workers, so once Celery arrives in
Phase G it must be Redis-backed, not in-process. Build the interface now with an
in-process implementation; note the swap in the docstring.

**Backoff + circuit breaker** — exponential backoff with jitter on 429/503/timeout, 3
attempts. After 5 consecutive failures the breaker opens for 10 minutes; while open,
`fetch` raises `SourceUnavailableError` immediately without a request. Breaker state is
what `/api/sources/health` reports.

**robots.txt** — fetched and parsed once per source at startup, cached for the process
lifetime. Disallowed paths are **logged at WARNING with the path and the rule that
matched**, per §4.2's "log, don't silently ignore". Config flag `ROBOTS_ENFORCE`
(default true in the external-product answer to §12.1, operator-set otherwise).

**Honest User-Agent** — `Phase1Gatekeeper/1.0 (+contact)`, from config. No browser
impersonation. If a source only works with a spoofed UA, that is a §12.1 signal, not a
technical obstacle to route around.

---

## 5. ScreenerAdapter (C4b)

### 5.1 Pages fetched

| Page | Purpose |
| :-- | :-- |
| `/company/{code}/consolidated/` (or non-consolidated per `basis`) | P&L, balance sheet, cash flow tables; shareholding section; Documents section |
| Quarterly shareholding view | Trailing 4–8 quarters of promoter holding + pledge |
| Search/lookup endpoint | `CompanyIdentity` resolution |

Per §3.3, the adapter fetches the URL matching the **declared** basis — never "whichever
loads". If the consolidated page does not exist for a company, that is a
`data_basis` fallback decision recorded in the run, not a silent switch.

**Spike this first (C4.0, half a day).** Before writing the adapter, verify by hand for
three tickers: whether the pledge and shareholding tables are server-rendered or require
JS (decides `httpx` vs Playwright per §2), whether a login/session is required for the
quarterly shareholding depth, whether the consolidated slug is stable, and what the
Documents section's AR link markup looks like. Every number below assumes server-rendered
HTML; if the spike says otherwise, the fetch layer changes and the parsers do not.

### 5.2 Field extraction, with the assertions that guard each one

| Field | Source table | Structural assertion (else `LayoutChangedError`) |
| :-- | :-- | :-- |
| `cfo_last_5y` | Cash Flow → "Cash from Operating Activity" | row exists; ≥ 5 FY columns; all values numeric |
| `pat_last_5y` | P&L → "Net Profit" | row exists; ≥ 5 FY columns; column headers align with the CFO row's |
| `promoter_holding_pct_of_company` | Shareholding → "Promoters" | row exists; latest column is a percentage in [0, 100] |
| `govt_shareholding_pct` | Shareholding → government/president-of-India row | row may legitimately be **absent** → field absent, not an error |
| `pledged_pct_of_promoter_holding` | Pledge row, latest quarter | value in [0, 100] |
| `pledged_pct_history_last_4q` | Pledge row, trailing quarters | ≥ 4 quarter columns present |
| `revenue` | P&L → "Sales"/"Revenue from operations", latest FY | numeric; FY matches `as_of_date`'s FY |
| `net_worth` | Balance sheet → Equity + Reserves | both rows present; sum > 0 |
| `years_of_track_record_available` | count of FY columns ∩ listing date | `min(...)`; **never emit 0** — absent instead |

That last one is load-bearing per plan §3.2: a wrongly-zero track record makes the app
HOLD on every company. If the count cannot be established, emit nothing and let the field
stay `null`.

**Column-to-period resolution is mandatory here too.** Screener's FY columns are headers,
not positions. Resolve each column to a fiscal year, record it as `period` on every
`ExtractedField`, and assert that the CFO row and PAT row resolve to the *same* ordered
FY list before emitting `cfo_last_5y`/`pat_last_5y` — Check 5 divides one by the other,
and a one-column offset produces a confident wrong ratio.

### 5.3 Confidence assignment

All Phase C values are `HTML_SCRAPE`. Per §5.3, a structured HTML scrape with the
expected table shape is `HIGH`. Therefore:

- Exact row-label match + all structural assertions passed → `HIGH`.
- Fuzzy row-label match (label drift, e.g. "Net Profit" vs "Profit after tax") → `MEDIUM`.
- Anything else → not emitted.

`pledged_pct_of_total_shares` is emitted by the existing
[`derive_pledged_pct_of_total_shares()`](backend/app/engine/helpers.py#L132) with
confidence `DERIVED` and `extraction_method=DERIVED`, not by the adapter.

### 5.4 Documents handoff

The Documents section's AR links are captured as `DocumentRef(fiscal_year, url, title)`
and persisted to `raw_documents` — **not downloaded** in Phase C. Downloading 10–80 MB
PDFs is Phase D's cost. Capturing the links now means Phase D starts with a working
document index instead of building discovery from scratch.

---

## 5A. Upload adapters (C4a) — the scrape-free input path

Scraping is one way to fill `CompanyInput`. Uploading a file is another, and it reaches
the **same** assembler through the **same** `SourceAdapter` interface — `fetch()` reads a
stored file instead of an HTTP response, `parse()` is unchanged in kind. This is the
payoff of keeping C1–C3 source-agnostic.

Two reasons this is worth building alongside the scraper rather than instead of it:

1. **It makes the app usable under every answer to §12.1.** If the answer is "external
   product", uploads *are* the product's input layer. If the answer is "personal use",
   uploads are the fallback for the days Screener is down, a layout has drifted, or the
   ticker is one Screener doesn't cover.
2. **It covers the whole `CompanyInput` scope today**, including the fields the scraper
   can never reach. A human who has read the Annual Report can supply
   `contingent_liabilities`, `audit_opinion` and `rpt_sales_plus_purchases` in Phase C —
   fields that otherwise wait for the Phase D PDF extractor. The upload path is the
   shortest route to a company that passes through all six checks with zero `null`s.

### 5A.1 Three upload kinds, in increasing order of trust

| Kind | What the user uploads | Adapter | Confidence |
| :-- | :-- | :-- | :-- |
| **A. Analyst workbook** | The app's own CSV/XLSX template, hand-filled | `WorkbookUploadAdapter` | `MANUAL` |
| **B. Source export** | A file the source itself produced — e.g. Screener's own per-company Excel export | `ScreenerExportAdapter` | `HIGH` (structural) |
| **C. Source document** | Annual Report PDF, BSE shareholding filing | *(captured in C, parsed in D)* | — |

Kind **A** is the floor: it always works, needs no third party, and is the honest
representation of "a human read the filing and typed the number." Kind **B** is the
interesting one — the user downloads the export themselves using a feature the source
provides, then hands the app a file. The app never touches the source. That sidesteps
§12.1 for the financial tables entirely, while giving the same structured, assertable
data a scrape would.

*(Verify in the C4.0 spike: whether Screener's Excel export exists for the account tier
in use, and which sheets/rows it contains. The `ScreenerExportAdapter` is contingent on
that, the `WorkbookUploadAdapter` is not.)*

Kind **C** is stored and hashed in Phase C, not parsed. Uploading an AR PDF in Phase C
registers it in `raw_documents` so Phase D has a document to work on — the same handoff
§5.4 does for scraped links.

### 5A.2 The analyst workbook template

One row per `CompanyInput` field. The columns are not negotiable, because they are the
provenance contract from plan §3.3 and §5.3 — a template that collects only values
recreates exactly the citation gap Phase B's paste form was built to avoid:

```
field_name | value | source | period | basis | notes
```

- `field_name` — must match a `CompanyInput` attribute. The template is **generated from
  the coverage matrix**, not hand-maintained, so it can never drift from the schema.
- `value` — scalar, or a comma-separated list for the array fields (`cfo_last_5y`,
  `pat_last_5y`, `pledged_pct_history_last_4q`), oldest → newest, matching the schema's
  documented order.
- `source` — free text, but **required**. "FY24 AR page 118" is a citation; blank is not.
- `period` — "FY24", "Q3FY25". Required for anything the matrix marks period-bearing.
- `basis` — `CONSOLIDATED` / `STANDALONE` / `NOT_APPLICABLE`. Required wherever the
  matrix says `basis_required`, and checked against the run's `data_basis` by the
  assembler's existing §6.1 rule. This is the guard against a hand-filled workbook mixing
  a consolidated numerator with a standalone denominator.

Ship the generated template from `GET /api/templates/workbook.xlsx`, pre-filled with the
field list, the check each field feeds, and the basis requirement — so the analyst is
filling a form, not authoring a spreadsheet.

**Validation is a first-class step, not a parse.** Reject the upload with a per-row error
report — never a partial silent import:

| Failure | Response |
| :-- | :-- |
| Unknown `field_name` | Row rejected, named in the error report (catches typos and schema drift) |
| Value fails the schema's type/range | Row rejected with the expected type |
| Missing `source` on a populated row | Row rejected — this is the citation contract |
| Missing/mismatched `basis` where required | Row **accepted into review**, not into `CompanyInput` (§6.1) |
| Array field with the wrong element count | Row rejected — `cfo_last_5y` with 4 elements silently breaks Check 5 |
| Empty row | Ignored — a blank field is a legitimate "I don't have this", which is what INCONCLUSIVE is for |

### 5A.3 Confidence, and where `MANUAL` sits in the ordering

A hand-filled workbook value is `confidence=MANUAL`, `extraction_method=MANUAL`. The
assembler needs an explicit answer to a question Phase C is the first to raise: **does
`MANUAL` satisfy a `HIGH` floor?**

Yes. `MANUAL` means a human read the source and asserted the value, which is the same
standard the review queue applies in Phase E and a stronger one than any extractor
reaches. So the floor comparison is not a simple enum ordering — encode it as:

```
MANUAL always passes.  Otherwise: HIGH > MEDIUM > LOW, compared against the floor.
DERIVED passes only where the matrix names derivation as the owner.
```

Without this rule the two fields floored at `HIGH` (`audit_opinion`,
`restatement_of_past_accounts`) would be unfillable by upload, which would make the
scrape-free path unable to complete Check 1 or Check 6 — the exact opposite of the point.

The corollary is that an uploaded workbook can produce a `REJECT` on a human's say-so.
That is correct and intended, but it means the **uploader's identity belongs in
provenance**, alongside the source string. Add `asserted_by` to the upload path now;
Phase E's review queue needs the same field and will reuse it.

### 5A.4 Precedence against scraped values

The §6.3 owner-priority rule already covers this, with one addition: a `MANUAL` value
always wins, per §6.6. If a workbook and a scrape disagree, the workbook is used **and**
the discrepancy is surfaced in the report — a human overriding a scraped number is a fact
worth showing an auditor, not a silent substitution.

### 5A.5 Handling untrusted files

Uploads are the first untrusted input this app accepts. None of this is optional:

- **Size and count caps** before anything is read — a workbook is kilobytes, an AR PDF is
  tens of megabytes. Enforce separate caps per kind and reject early.
- **Sniff the content, don't trust the extension or the client's MIME type.**
- **Read XLSX with formulas off** (`openpyxl` with `data_only=True`) and cap the
  decompressed size — a spreadsheet is a zip archive, and an unbounded one is a
  decompression bomb.
- **Store by content hash** in `raw_documents` (the §10 schema's `UNIQUE (company_id,
  content_hash)` already dedupes re-uploads of the same file).
- **Never render an uploaded filename back into a report unescaped.** Filenames reach the
  analyst-facing report through provenance, and the rendering layer already exists.
- Uploaded files are user data — they fall under §12.5's unanswered retention question.

### 5A.6 What this changes upstream

The `/run` flow becomes: `sources = [enabled adapters] + [uploads attached to this run]`,
assembled identically. The frontend's ticker box gains a sibling — a drop zone, plus a
"download the template" link — and the field groups from §8 gain a third state:
auto-filled, uploaded, or still empty.

---

## 6. The assembler (C3) — where the coverage matrix becomes executable

```python
def assemble(
    identity: CompanyIdentity,
    as_of_date: str,
    basis: ReportingBasis,
    results: list[AdapterResult],
    manual_overrides: dict[str, Any] | None = None,
) -> tuple[CompanyInput, list[ReviewItem]]
```

Rules, applied in this order:

1. **Basis filter.** Any `ExtractedField` whose `basis` disagrees with the run's declared
   `data_basis` (and whose matrix row says `basis_required`) is dropped to a review item.
   Per §3.3 it is *never* substituted — the check goes INCONCLUSIVE via the engine's
   existing `assert_comparable()`.
2. **Confidence floor.** Look up `confidence_floor` in the coverage matrix. Below floor →
   the field stays `null` and a `ReviewItem` is created. This is the §5.3 handoff rule,
   and it is why the matrix has to move out of `tests/`.
3. **Precedence on conflict.** When Phase D lands, two adapters will offer `revenue` and
   `net_worth`. Precedence is by matrix `owner`, not by arrival order: the AR (PDF tier 2)
   value wins over the Screener cross-check. Encode this now as an ordered
   `owner_priority` list, even though Phase C has only one source — retrofitting
   precedence after two sources exist means auditing every already-generated result.
4. **Discrepancy flag.** When two sources both supply a field and differ by more than the
   per-field tolerance (§4.1 point 3: >1pp for pledge %), emit **both** into provenance
   and raise a review item. Never silently pick one. Stubbed in C3, exercised in Phase F.
5. **Provenance construction.** Every populated field gets a `FieldProvenance`. The
   engine's existing `citation_gaps` logic in
   [orchestrator.py](backend/app/engine/orchestrator.py) already fails loudly if a
   PASS/FAIL relied on a field with no provenance entry — that is the acceptance test for
   this step, and it is already written.
6. **Manual overrides win.** A human-confirmed value from the form or the review queue
   supersedes any scraped value, with `confidence=MANUAL` and the reviewer's identity in
   provenance.

`manual_overrides` is how the existing UI keeps working unchanged: Phase C prefills, the
analyst edits, the edits win.

---

## 7. Testing strategy

**No test in CI touches the network.** Three layers:

1. **Parser unit tests (the bulk).** Record real Screener HTML once into
   `tests/fixtures/screener/{ticker}-{date}.html` and commit it. Parsers are pure
   functions, so these tests are fast and exact: assert values, `period`, `basis`,
   `confidence`, and `raw_snippet` — not just the number.
2. **Layout-drift tests.** Mutate the recorded fixtures deliberately — delete the pledge
   row, drop a quarter column, replace numbers with "-" — and assert `LayoutChangedError`
   or field-absence, specifically *not* a wrong value. This is the test that catches the
   failure mode §4.2 exists to prevent, and it is the one teams skip.
3. **Pipeline test.** Recorded HTML → adapter → assembler → `run_phase1()` → assert the
   verdict, and assert `result.citation_gaps == []`. The 18 engine fixtures stay untouched
   and network-free, per the plan's first design principle.

4. **Upload tests (§5A).** Commit a good workbook, and one deliberately broken workbook
   per row of the §5A.2 validation table — unknown field name, missing `source`, wrong
   array length, basis mismatch. Assert the *specific* rejection, not just that it
   failed. Add a malformed-file case (a `.xlsx` that is actually HTML, an oversized file)
   asserting the §5A.5 guards fire before any parsing happens.

**Live smoke test, run manually and outside CI:** `pytest -m live` against three real
tickers, one per company type (a PSU for the `govt_shareholding_pct` path, a
high-pledge private promoter, a professionally-managed company). Plan §3.4's exit
criterion for Phase C is exactly this — every Phase-C row in the matrix populated with
valid provenance on three real tickers. Re-record the HTML fixtures from this run.

Add a **fixture staleness check**: if a recorded fixture is older than 90 days, the live
smoke test warns. Silently ageing fixtures are how a parser suite stays green for a year
against a site that changed in month two.

---

## 8. API and frontend changes

**New endpoints** (plan §9):

```
POST /api/tickers/{ticker}/run     → resolve identity, run enabled adapters + any
                                      attached uploads, assemble, run_phase1(),
                                      return result + provenance + the list of
                                      fields still empty
POST /api/tickers/{ticker}/uploads → accept a workbook / source export / source
                                      document; returns parsed preview + per-row
                                      validation errors, WITHOUT running the engine
GET  /api/templates/workbook.xlsx  → the §5A.2 template, generated from the
                                      coverage matrix
GET  /api/sources/health           → registry health_check() + circuit-breaker state
GET  /api/coverage                 → extend the existing endpoint with live fill rates
                                      per field, not just the static matrix
```

Upload and run are deliberately **separate calls**. The analyst uploads, sees exactly
what was parsed and what was rejected, corrects, then runs. Coupling them into one
multipart call would mean a typo in row 14 either fails the whole evaluation or silently
drops a field — and a silently dropped field becomes an INCONCLUSIVE the analyst cannot
explain.

`POST /api/tickers/{ticker}/run` returns a **partial** `CompanyInput` alongside the
result. Phase C is synchronous (5–10s per §8.4); the Celery fan-out is Phase G. Do not
build the job queue here — but do return a shape that can later carry a `job_id` without
a breaking change.

**Frontend** — the current form becomes a two-stage flow:

1. Enter ticker → **Fetch** (if scraping is enabled) → the form populates, each
   auto-filled field showing a small provenance chip (source, period, basis, confidence)
   and an "override" affordance.
2. **Or drop in a file** — a filled workbook, a Screener export — and the same fields
   populate, chipped as `MANUAL` or `HIGH` with the filename as source. A "download the
   template" link sits next to the drop zone; the template is where most analysts will
   start.
3. The analyst fills whatever is still empty. Group the fields by state — auto-filled,
   uploaded, still empty — and label the PDF-owned group "Not yet automated (Phase D)" so
   the remaining boxes read as scope, not breakage.

If §12.1 resolves to the external-product answer, stage 1 simply is not rendered and the
flow starts at stage 2. That is the whole UI consequence, which is the point of routing
both paths through one assembler.

Keep the fixture dropdown. It is how the engine gets tested without the network, and
Phase C does not change that.

---

## 9. Sequencing

| Step | Deliverable | Done when |
| :-- | :-- | :-- |
| **C0** | Move `FIELD_COVERAGE_MATRIX` to `backend/app/models/coverage.py`; add `owner_phase` | `main.py` no longer imports from `tests/`; existing tests pass |
| **C1** | `types.py`, `base.py`, `registry.py` | An in-repo `FakeAdapter` returning canned `ExtractedField`s registers and runs |
| **C2** | `http_client.py`, `cache.py`, `robots.py` | Unit tests for TTL expiry, backoff, breaker open/close, robots parse. No real site hit |
| **C3** | `assembler.py` | FakeAdapter → assembler → `run_phase1()` produces a verdict with `citation_gaps == []`, and a below-floor field produces a review item instead of a value |
| **C4a** | Upload intake + template generator + `WorkbookUploadAdapter` | A filled workbook drives a complete run: all six checks conclusive, `citation_gaps == []`, every §5A.2 validation case rejected with its specific error |
| **C4.0** | Screener spike | Written answers to the four §5.1 questions, plus whether the Excel export exists; recorded HTML/XLSX for 3 tickers |
| **C4b** | `ScreenerAdapter` (+ `ScreenerExportAdapter` if the spike confirms the export) | All §5.2 fields extracted with correct period/basis/confidence; drift tests pass |
| **C5** | `POST /run`, `POST /uploads`, `/api/templates/workbook.xlsx`, `/api/sources/health`, coverage fill-rates | End-to-end from ticker or workbook to rendered report |
| **C6** | Frontend fetch-and-review flow + upload drop zone | The two Check-2 boxes prefill from a scrape, and a workbook prefills the whole form |
| **C-exit** | Live smoke on 3 real tickers | Every Phase-C matrix row populated with valid provenance (plan §3.4), via both routes |

C1–C3 and **C4a** are independent of the §12.1 decision and of the spike — C4a is the
one that turns the framework into a shippable product on its own. Only C4b depends on
both. If the §12.1 answer is slow in coming, C4a is where the phase's value lands, and
nothing about it is throwaway work under any later answer.

---

## 10. Risks

| Risk | Mitigation |
| :-- | :-- |
| §12.1 unresolved and C4 gets built anyway | C1–C3 are source-agnostic; hold C4 behind the decision. The framework is not wasted work under any answer |
| Screener requires JS or login for pledge history | The C4.0 spike answers this before the adapter is written; only the fetch layer changes |
| Silent layout drift returns wrong numbers | Structural assertions + `LayoutChangedError` + the mutation tests in §7.2. This is the single highest-value test class in the phase |
| Screener cross-check values get treated as authoritative | Owner-priority precedence in the assembler (§6.3), built before a second source exists |
| Rate limiter is in-process, breaks under Celery | Redis-backed interface from the start; documented in the docstring |
| Basis mixing (consolidated numerator ÷ standalone denominator) | Basis is carried on every `ExtractedField` and filtered in the assembler before the engine sees it (§6.1); the engine's `assert_comparable()` is the backstop, not the primary guard |
| A hand-filled workbook produces a confident wrong REJECT | `basis` and `source` are required per row and validated (§5A.2); the uploader is recorded in provenance (§5A.3) and shown in the analyst report. This is a governance control, not a technical one — the human is the source of truth by design |
| Workbook template drifts from `CompanyInput` | The template is **generated** from the coverage matrix, and the matrix is already reflection-tested against the schema. Drift is structurally impossible rather than merely caught |
| Malicious or malformed upload | §5A.5 — caps before read, content sniffing, formulas off, decompression bound, escaped filenames in reports |

---

## 11. Explicitly out of scope for Phase C

AR PDF **parsing** (D — Phase C stores and hashes an uploaded AR, it does not read it),
OCR (E), the review-queue resolver UI (E — C3 only *emits* review items), BSE/NSE/SEBI
adapters (F), Celery/Redis job fan-out (G), **multi-ticker** CSV bulk upload (G — §5A is
one workbook for one company; the batch fan-out layer is a different thing), Postgres persistence (the in-memory stores in
[main.py](backend/app/api/main.py) stay until Phase G unless the §10 schema is pulled
forward), and auth (Phase 0, still outstanding).
