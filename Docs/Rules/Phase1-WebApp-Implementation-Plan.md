# Phase 1 Gatekeeper — Web Application Implementation Plan

*How to turn `Phase1-Algorithms.md` (the decision engine spec) and `Phase1-Rules.md`
(the policy) into a running web application. Covers scraping, PDF extraction (including
hard-to-parse PDFs), report generation with a PDF export option, and bulk ticker input
via CSV/Excel. This is an architecture and build plan, not code — implementation should
follow this sequencing.*

*Revision 2 — adds the field-coverage matrix (§3), reporting-basis handling, provenance
capture, near-threshold escalation, result versioning and report staleness, and a
corrected schema. Tracks `Phase1-Algorithms.md` revision 2.*

---

## 1. System overview

Five components, deliberately decoupled so a weak link (a scraper breaking, a PDF that
won't parse) degrades gracefully into "INCONCLUSIVE, needs manual input" instead of
crashing the pipeline or silently guessing.

```
                         ┌─────────────────────┐
   CSV/Excel upload ───▶ │   Batch Controller   │
   Single ticker    ───▶ │  (job fan-out layer) │
                         └──────────┬───────────┘
                                    │ one job per ticker
                                    ▼
                         ┌─────────────────────┐
                         │   Job Queue/Worker   │  (async, retryable)
                         └──────────┬───────────┘
                                    ▼
        ┌───────────────────────────────────────────────┐
        │              Data Acquisition Layer             │
        │  ┌───────────────┐        ┌───────────────────┐ │
        │  │  Web Scraper   │        │  PDF Extractor    │ │
        │  │ (Screener/BSE/ │───────▶│ (Annual Reports,  │ │
        │  │  NSE/SEBI)     │  PDFs  │  Reg-30 filings)  │ │
        │  └───────────────┘        └───────────────────┘ │
        └──────────────────────┬──────────────────────────┘
                                ▼  CompanyInput + FieldProvenance
                    ┌───────────────────────┐
                    │   Decision Engine       │  (pure functions from
                    │  (Phase1-Algorithms.md) │   Phase1-Algorithms.md §3-9)
                    └───────────┬────────────┘
                                ▼  Phase1Result (versioned)
                    ┌───────────────────────┐
                    │   Rendering Layer       │
                    │  (internal table +      │
                    │  user.md investor prose)│
                    └───────────┬────────────┘
                                ▼
                 ┌──────────────┴───────────────┐
                 ▼                               ▼
          Web/JSON report                  PDF export
      (per ticker + batch matrix)      (per ticker + consolidated)
```

**Design principle carried over from the algo spec:** the Decision Engine never touches
a scraper, a PDF, or a browser. It only accepts a `CompanyInput` object (with its
provenance map). This means the engine can be fully unit-tested against the 18 fixtures
in `Phase1-Algorithms.md` §11 with zero network/PDF dependencies, and the acquisition
layer can be swapped or patched without touching pass/fail logic.

**Second principle, added in revision 2:** every value that reaches the engine carries
its own provenance — source, period, reporting basis, page, confidence. The engine
cannot produce the `citation` that `Phase1-Rules.md` §7 requires unless the acquisition
layer supplies this, so provenance is part of the extraction contract, not a logging
nicety bolted on later.

---

## 2. Tech stack recommendation

| Layer | Choice | Why |
| :-- | :-- | :-- |
| Backend / API | Python 3.11+, FastAPI | Best-in-class PDF/OCR/table-extraction ecosystem (see §5); async-friendly for scraping fan-out |
| Job queue | Celery + Redis (or RQ for a simpler start) | Scraping + PDF parsing are slow (seconds–minutes/ticker); must be async, retryable, individually failable per ticker |
| Database | PostgreSQL | Relational integrity across companies → filings → checks → reports; JSONB columns for raw extracted payloads and array-valued fields |
| Object storage | S3-compatible (AWS S3 / MinIO for local dev) | Store downloaded Annual Report / Reg-30 PDFs and generated report PDFs, addressable by ticker+doc hash |
| PDF text/table extraction | `pdfplumber` (primary), `camelot-py` (table-heavy notes), `PyMuPDF`/`fitz` (fast text + layout) | Layered by document type, see §5.2 |
| OCR fallback | `Tesseract` via `pytesseract`, pre-processed with `OpenCV` (deskew/binarize) | For scanned/image-only PDFs — see §5.2 tier 4 |
| CSV/Excel ingestion | `pandas` + `openpyxl` | Native support, handles both `.csv` and `.xlsx` |
| Report → PDF rendering | `WeasyPrint` (HTML/CSS → PDF) | Keeps one HTML template as the single source for both web and PDF rendering — no separate PDF-only template to maintain |
| Frontend | React (Vite) or Next.js, minimal | Ticker input (single + bulk upload), job status, report viewer, download buttons |
| Scraping/browser automation | `httpx`/`requests` for static pages; Playwright only where a site requires JS rendering | Prefer plain HTTP first — browser automation is slower and more fragile; escalate only when needed |
| Auth | Any standard session/JWT provider; roles `viewer`, `analyst`, `reviewer`, `admin` | §10 has FKs to a users table and §5.4 gates who may resolve a review item — this cannot be deferred to "later" |

Two dependency caveats worth knowing before Phase D:

- **`camelot-py` needs Ghostscript** as a system binary and is thinly maintained. Budget
  for the container-image work, and treat it as replaceable (`tabula-py`, `unstructured`)
  rather than load-bearing — tier 3 is a fallback, not the primary path.
- **`WeasyPrint` needs Pango/Cairo** system libraries; this bites on slim base images.

This stack is a recommendation, not a hard requirement — every module below is
specified independently of the exact library, so a Node/TypeScript equivalent
(`pdf-parse`/`pdf.js`, `pdf-tables-extractor`, `tesseract.js`, `puppeteer`) is a valid
substitution if the team prefers a single-language stack with the frontend.

---

## 3. Field coverage matrix — build this first

**This is the contract between §4 (scraper), §5 (PDF extractor) and the Decision
Engine.** Every field in `Phase1-Algorithms.md` §0 `CompanyInput` appears here exactly
once, with an owner. A field with no owner is a field that silently stays null, which
turns into a permanent `HOLD_INCONCLUSIVE` no matter how good the rest of the system is.

Column meanings: **Source** — where the value comes from. **Owner** — which adapter or
extraction tier produces it, and in which build phase. **Basis** — must the value carry
a `CONSOLIDATED`/`STANDALONE` tag (§3.3). **Floor** — the minimum confidence that may
populate `CompanyInput` automatically (§5.3); anything below goes to review.

### 3.1 Check-bearing fields

| `CompanyInput` field | Check | Source | Owner (phase) | Basis | Floor |
| :-- | :-: | :-- | :-- | :-: | :-- |
| `audit_opinion` | 1 | AR → Independent Auditor's Report → "Opinion" paragraph | PDF tier 1 (D) | n/a | **HIGH only** — verdict-flipping narrative |
| `auditor_resigned_mid_tenure_last_3y` | 1 | AR auditor/Board's report **plus** BSE/NSE Reg-30 announcements for the trailing 12m post-dating the AR | PDF tier 1 (D) + BSE/NSE adapters (F) | n/a | HIGH |
| `regulatory_action.active_or_past_5y`, `.nature` | 1 | SEBI enforcement archive + targeted press scan (§4.3) | SEBI adapter (F) | n/a | **MANUAL** — search-based, always human-confirmed |
| `legal_fees` | 1 | AR → Notes → Other Expenses → "Legal and professional charges" | PDF tier 2/3 (D) | yes | MEDIUM + threshold escalation |
| `audit_fees` | 1 | AR → Notes → "Payment to auditors" / "Auditor's remuneration" | PDF tier 2/3 (D) | yes | MEDIUM + threshold escalation |
| `legal_fees_prior_year` | 1 | Comparative (prior-year) column of the same note; fall back to prior-FY AR | PDF tier 2/3 (D) | yes | MEDIUM |
| `govt_shareholding_pct` | 2 | Screener shareholding pattern (Government row); BSE Reg-31 cross-check | **Screener (C)**, BSE (F) | n/a | HIGH |
| `promoter_holding_pct_of_company` | 2 | Screener shareholding pattern | Screener (C) | n/a | HIGH |
| `pledged_pct_of_promoter_holding` | 2 | Screener quarterly pledge; BSE Reg-31 cross-check, flag >1pp gap | Screener (C), BSE (F) | n/a | HIGH |
| `pledged_pct_history_last_4q` | 2 | Screener trailing 4–8 quarters | Screener (C) | n/a | HIGH |
| `pledged_pct_of_total_shares` | 2 | BSE Reg-31 if reported; else **derived** per algo §2c | Screener/BSE (C/F), else derivation | n/a | HIGH or `DERIVED` |
| `rpt_sales_plus_purchases` | 3 | AR → Notes → Related Party Transactions (sales + purchases) | PDF tier 2/3 (D) | yes | MEDIUM + threshold escalation |
| `revenue` | 3 | **AR → Statement of P&L → Revenue from operations**, same statement/FY/basis as the RPT note; Screener P&L as cross-check only | PDF tier 2 (D), Screener cross-check (C) | yes | MEDIUM + threshold escalation |
| `unusual_affiliate_dealings` | 3 | AR RPT note narrative + loans/advances to related parties | **Review queue by default** (E) | n/a | **MANUAL** — judgement, not extraction |
| `contingent_liabilities` | 4 | AR → Notes → "Contingent Liabilities and Commitments" | PDF tier 2/3 (D) | yes | MEDIUM + threshold escalation |
| `net_worth` | 4 | **AR → Balance Sheet → Total Equity / Shareholders' funds**; Screener as cross-check | PDF tier 2 (D), Screener cross-check (C) | yes | MEDIUM + threshold escalation |
| `cfo_last_5y` | 5 | Screener Cash Flow → "Cash from Operating Activity", 5 FYs | Screener (C) | yes | HIGH |
| `pat_last_5y` | 5 | Screener P&L → "Net Profit", 5 FYs | Screener (C) | yes | HIGH |
| `cfo_changes_last_3y` | 6 | AR Board's / Corporate Governance report KMP changes + BSE/NSE Reg-30 announcements | PDF tier 1 (D) + BSE/NSE (F) | n/a | HIGH |
| `restatement_of_past_accounts` | 6 | AR → prior-period-error / restatement note **and** auditor's Emphasis of Matter | PDF tier 1 (D) | n/a | **HIGH only** |

### 3.2 Structural fields (easy to forget, and every one of them is load-bearing)

| Field | Why it matters | Source | Owner (phase) |
| :-- | :-- | :-- | :-- |
| `years_of_track_record_available` | Gates Checks 1, 5, 6. If it is null the engine holds; if it were wrongly 0 the app would hold on *every* company | `min(` years since listing from BSE/NSE company master `,` count of FYs of financials actually retrieved `)` | Screener + BSE (C) |
| `data_basis` | Every ratio in Checks 1, 3, 4, 5 depends on it | Run configuration; default `CONSOLIDATED` per rules §8.1, fall back to `STANDALONE` only if no consolidated statements exist, and record which | Orchestrator (C) |
| latest AR fiscal year + AR publication date | §4.1's BSE/NSE filter is "announcements post-dating the latest AR" — that date has to come from somewhere | AR cover page / Screener Documents metadata | PDF tier 1 (D) |
| `company_type` | Derived by the engine, never supplied | — | Engine |
| `as_of_date`, `ticker` | Job parameters | — | Orchestrator |

### 3.3 Reporting basis rule

Rules §8.1 prefers the consolidated view. Checks 3, 4 and 5 are all ratios, and mixing a
consolidated numerator with a standalone denominator produces a confident wrong number
that passes every confidence check in §5.3. Therefore:

- Every financial extraction records `basis` and `period` in its provenance entry —
  non-negotiable, same as recording the value itself.
- The run declares one `data_basis`. If a required figure is only available on the other
  basis, the field is **not** substituted; the check goes INCONCLUSIVE via
  `assert_comparable()` (algo §2b) and the review queue gets an item saying which figure
  is missing on which basis.
- Screener's `/consolidated/` and standalone pages are different URLs — the adapter must
  fetch the one matching the declared basis, not whichever loads.

### 3.4 How to use this matrix

It is a test artefact, not documentation. Before Phase C, write a test that enumerates
`CompanyInput`'s fields by reflection and fails if any field is absent from this table.
Before each of Phases C–F, the phase is done when every row assigned to it produces a
populated field with valid provenance on at least three real tickers.

---

## 4. Data Acquisition Layer — Web Scraper

Maps to `Phase1-Rules.md` §8.1–8.3.

### 4.1 Source adapter pattern

One adapter per source, all implementing a common interface, so adding a 7th source
later doesn't touch the orchestrator:

```
interface SourceAdapter {
  name: string
  fetch(ticker_or_scrip_code, basis) -> RawPage[]   // HTML/JSON payloads
  parse(RawPage[]) -> (PartialCompanyInput, map<field, FieldProvenance>)
  health_check() -> bool                            // cheap ping to detect layout/site changes early
}
```

`parse()` returns provenance alongside values — an adapter that returns a number without
saying where it came from is an incomplete adapter, because the citation the engine owes
`Phase1-Rules.md` §7 can then never be built.

Adapters to build, in priority order (matches the rules file's "Primary Hub" framing):

1. **ScreenerAdapter** — primary hub. Pulls: 5-yr CFO/PAT table (Check 5), trailing
   4–8 quarters promoter holding + pledge % (Check 2), **government shareholding %**
   (company classification + Check 2 auto-pass), **revenue and net worth as
   cross-checks** (Checks 3 & 4), **listing/reporting history length**, and the
   Documents section's Annual Report PDF links (handed off to the PDF Extractor).
2. **BSEAnnouncementsAdapter** — Reg-30 disclosures, filtered by category
   (`Resignation`, `Company Update`) for auditor/CFO exits post-dating the latest AR
   (Checks 1 & 6).
3. **BSEShareholdingAdapter** — Regulation 31 filing, cross-verification for Check 2's
   pledge %, independent of Screener's number (flag a discrepancy > 1pp between the two
   sources rather than silently picking one).
4. **NSEAnnouncementsAdapter** — backup/fallback for #2 when BSE is unavailable or a
   dual-listed stock's NSE filing is more current.
5. **SEBIEnforcementAdapter** — searchable order archive for Check 1's regulatory-action
   field; this one is closer to a targeted search than a scrape (see 4.3).

### 4.2 Resilience requirements (non-negotiable, since these are third-party sites)

- **Caching layer**: cache by `(source, canonical_url, basis)` with an explicit TTL
  (default 24h), **not** by fetch date — a date in the key can never produce a hit after
  midnight and cannot express a TTL at all. Screener/BSE data doesn't change intraday for
  this use case; don't re-hit the same URL twice in one run, and don't re-scrape on every
  batch re-run. Store the fetch timestamp as a value so provenance can report it.
- **Rate limiting + backoff**: fixed delay between requests per source (configurable,
  default 1–2s), exponential backoff on 429/503, circuit breaker that pauses an
  adapter for N minutes after repeated failures rather than hammering a struggling site.
- **User-Agent / robots.txt respect**: identify the scraper honestly; check each site's
  `robots.txt` at startup and log (don't silently ignore) any disallowed paths — the
  Screener/BSE/NSE/SEBI endpoints named in the rules file are the ones this app is
  scoped to use, not a general-purpose crawler.
- **Layout-change detection**: each adapter's `parse()` should assert on expected
  structure (e.g., "promoter holding table has N columns") and raise a distinct
  `LayoutChangedError` rather than silently returning garbage — this surfaces as
  INCONCLUSIVE with a specific "source layout changed, needs adapter fix" note instead
  of a wrong number flowing into the Decision Engine.
- **No fabrication on failure**: if an adapter fails after retries, the corresponding
  `CompanyInput` fields stay `null`. Per the algo spec's golden rule, that's what turns
  into `INCONCLUSIVE`, never a guess.

### 4.3 SEBI regulatory scan — special case

This one isn't a structured table scrape; it's closer to the targeted search in rules
§8.1's "Targeted Regulatory Press Scan" row. Implementation:

- Query SEBI's enforcement archive with the company name.
- Additionally run the general web query pattern from the rules file
  (`"{Company}" AND (SEBI OR "Enforcement Directorate" OR SFIO OR CBI) AND (fraud OR
  investigation OR debarred OR "show cause")`) via a search API (e.g., a news/web search
  API the team already has access to).
- This step's output is inherently lower-confidence than a structured filing. Store it
  with `confidence: MANUAL` (it always requires human confirmation before populating
  `regulatory_action`) and require it to be surfaced in the report as "no adverse result
  found in a web scan as of {date}" rather than a hard "no regulatory issues" claim —
  **absence of evidence in a web scan is not evidence of absence.**
- A clean scan therefore does not by itself set `active_or_past_5y = false`. A reviewer
  does, after seeing the scan output. An unreviewed clean scan leaves the field null and
  Check 1 inconclusive, which is the correct conservative outcome.

---

## 5. Data Acquisition Layer — PDF Extractor

This is the highest-risk module because Annual Report PDFs vary enormously in quality.
Maps to rules §8.2–8.3 (auditor's opinion, RPT note, contingent liabilities note,
balance sheet, P&L, KMP changes, legal/audit fee notes).

**How many Annual Reports to fetch:** rules §8.2 says the last 5 FYs. In practice the
latest AR supplies all of Checks 1, 3, 4 and 6, plus `legal_fees_prior_year` from its
comparative column; the prior-FY AR is fetched only when that comparative column is
missing or unparseable. Do not fetch five ARs by default — it multiplies the slowest
part of the pipeline by five for data that Screener already provides for Check 5.

### 5.1 Classify the PDF before extracting

First step for every downloaded PDF, before any field extraction is attempted:

```
function classify_pdf(pdf_path) -> PdfClass:
    text_layer_ratio = extractable_text_chars / total_page_count
    if text_layer_ratio > threshold_native:      // has a real, dense text layer
        return NATIVE_TEXT
    if has_partial_text_layer(pdf):               // e.g. scanned pages mixed with native ones
        return HYBRID
    return SCANNED_IMAGE_ONLY                      // no usable text layer at all
```

This classification decides which extraction strategy runs, and is stored against the
document so re-runs don't re-classify every time.

### 5.2 Extraction strategy ladder (try cheap/reliable first, escalate only if needed)

| Tier | Method | Used for | Notes |
| :-- | :-- | :-- | :-- |
| 1 | `PyMuPDF` text extraction + keyword/section anchoring | `NATIVE_TEXT` PDFs, all narrative sections (Auditor's Opinion paragraph, Board's Report KMP changes, restatement note) | Search for section headers with fuzzy matching to survive minor formatting differences year to year |
| 2 | `pdfplumber` table extraction | `NATIVE_TEXT` PDFs, numeric notes (RPT, Contingent Liabilities, Auditor Remuneration, Legal & Professional charges, Balance Sheet equity, P&L revenue) | Tables in Annual Report notes are usually plain PDF tables, not images — pdfplumber's `extract_tables()` handles most of these |
| 3 | `camelot-py` (lattice + stream modes) | Same numeric notes when pdfplumber's table extraction produces malformed/merged cells | Camelot's lattice mode is strong when notes have visible grid lines; stream mode as fallback when they don't |
| 4 | OCR (`pytesseract` + `OpenCV` pre-processing: deskew, binarize, upscale) | `SCANNED_IMAGE_ONLY` pages, or `HYBRID` PDFs' scanned pages specifically | Run OCR per-page only on pages that failed tiers 1–3, not the whole document — keeps cost down |
| 5 | Manual review queue | Anything tier 1–4 couldn't produce a confident value for | See 5.4 — this is not a failure state, it's a designed fallback |

**Column-to-year mapping (tiers 2–3).** Annual Report notes are two-column: current FY
and comparative prior FY, and which column is which is a header, not a position. Every
table extraction must resolve the column header to a fiscal year and record it as
`period` in provenance. An unresolvable column header means the value goes to review —
silently taking column 1 is how `legal_fees` and `legal_fees_prior_year` get swapped,
which inverts the surge sub-check.

### 5.3 Confidence scoring, not silent success/failure

Every extracted field gets a confidence tag and full provenance, not just a value:

```
struct ExtractedField {
  value: any
  confidence: HIGH | MEDIUM | LOW | MANUAL | DERIVED
  extraction_method: enum { NATIVE_TEXT, TABLE_PARSE, OCR, MANUAL, DERIVED, HTML_SCRAPE }
  source: string               // document filename or source URL
  period: string               // "FY24" — resolved from the column header, not assumed
  basis: CONSOLIDATED | STANDALONE | NOT_APPLICABLE
  source_page: int | null
  raw_snippet: string          // the exact text/row the value came from, for audit
  extracted_at: timestamp
}
```

This struct maps 1:1 onto `FieldProvenance` in `Phase1-Algorithms.md` §0 — the extractor
emits it, the engine cites from it, the renderer displays it.

- `HIGH` — Tier 1/2 native extraction with an exact section-header match, or a
  structured HTML scrape with the expected table shape.
- `MEDIUM` — Tier 3 table-repair, or a Tier 1 match on a fuzzy/partial header.
- `LOW` — OCR output, or a regex match with no confirmed section anchor.

**Rule for the Decision Engine handoff:** only `HIGH` and `MEDIUM` confidence fields
populate `CompanyInput` automatically. `LOW`-confidence fields are held for manual
review (§5.4) and the corresponding `CompanyInput` field stays `null` until a human
confirms or corrects it — this directly feeds the algo spec's `INCONCLUSIVE` path
rather than letting an OCR misread silently produce a wrong PASS/FAIL.

Some fields are floored at `HIGH` regardless (see §3.1): `audit_opinion` and
`restatement_of_past_accounts` are single words that flip a verdict on their own, and a
fuzzy header match is not good enough to reject a company on.

**Near-threshold escalation.** Confidence alone is the wrong gate for numbers that sit
close to a limit: a MEDIUM-confidence table repair that reads 9.8% instead of 10.8%
produces a confident wrong verdict. Any `MEDIUM` numeric whose computed ratio lands
inside the band below is escalated to review regardless of confidence.

| Check | Computed quantity | Threshold (rules §2) | Escalate MEDIUM within |
| :-: | :-- | :-- | :-- |
| 1 | legal fees ÷ audit fees | 5× | 4.0× – 6.5× |
| 1 | legal fees YoY growth | 2× | 1.7× – 2.5× |
| 2 | pledged % of promoter holding | 10% | 8% – 13% |
| 3 | RPT ÷ revenue | 5% | 4% – 6.5% |
| 4 | contingent liabilities ÷ net worth | 15% | 12% – 19% |
| 5 | cumulative CFO ÷ PAT | 0.80 | 0.70 – 0.92 |

Bands are deliberately asymmetric-tolerant and configurable; tune them in Phase H
against observed extraction error, and log every escalation so the rate is measurable.
`HIGH`-confidence values are not escalated — that is the point of the HIGH tier.

### 5.4 Manual review queue (the answer to "some PDFs are harder to extract")

This is the load-bearing piece for hard-to-parse PDFs — the system must not block or
guess, it must degrade to a clearly-flagged human step:

1. An item is written to `review_queue` when a field (a) falls out of tiers 1–4,
   (b) lands at `LOW` confidence, (c) lands at `MEDIUM` inside a near-threshold band,
   (d) is floored at `MANUAL` by §3.1, or (e) fails the basis/period comparability guard.
   The item carries `{ticker, check_id, field_name, best_guess_value, raw_snippet,
   source_page, source_url, period, basis, reason}`.
2. A lightweight reviewer UI shows the flagged page image (or the relevant text
   snippet) side-by-side with an input box — a human confirms or overrides the value in
   seconds rather than reading the whole report. The reviewer also confirms the period
   and basis, since those are as easy to get wrong as the number.
3. Once resolved, the value is written back into `CompanyInput` with
   `extraction_method: MANUAL`, provenance naming the reviewer and timestamp, and the
   pipeline can be re-run for that ticker without re-scraping/re-extracting everything
   else (idempotent per-field, not per-run).
4. If a ticker's report is generated before manual review is done, affected checks
   report as `INCONCLUSIVE — data not available` per the algo spec, exactly as the
   rules file requires (§1: "do not guess... mark that check INCONCLUSIVE"). Resolving
   the item later produces a **new revision** of `Phase1Result`, which may change the
   verdict — see §7.4 for what that means for anything already published.
5. Only a user with the `reviewer` role may resolve an item, and the resolution is
   append-only (an audit trail, not an overwrite) — a human-entered number that decides
   a REJECT needs to be as traceable as a scraped one.
6. Track a per-adapter/per-document "extraction success rate" metric — if a particular
   filer's PDFs consistently fall to OCR/manual (e.g., a company that files scanned
   reports every year), flag that ticker for a standing manual-review expectation rather
   than re-discovering it every run.

### 5.5 Section-anchor library

Maintain a small, versioned library of section-header patterns per note, since Annual
Report formatting drifts year to year and filer to filer:

```
SECTION_PATTERNS = {
  "auditor_opinion":            ["INDEPENDENT AUDITOR'S REPORT", "Opinion", "Basis for Opinion"],
  "emphasis_of_matter":         ["Emphasis of Matter", "Material Uncertainty"],
  "related_party":              ["Related Party Transactions", "Related Party Disclosures"],
  "contingent_liabilities":     ["Contingent Liabilities", "Contingent Liabilities and Commitments"],
  "auditor_remuneration":       ["Payment to Auditors", "Auditor's Remuneration", "Remuneration to Auditors"],
  "legal_professional_charges": ["Legal and Professional", "Legal & Professional Charges"],
  "kmp_changes":                ["Key Managerial Personnel", "Changes in Key Managerial Personnel"],

  // added in revision 2 — these back Checks 3, 4 and 6 and had no anchor before
  "balance_sheet_equity":       ["Total Equity", "Shareholders' Funds", "Equity and Liabilities",
                                 "Total equity attributable to owners"],
  "revenue_from_operations":    ["Revenue from Operations", "Statement of Profit and Loss",
                                 "Total Income"],
  "restatement":                ["Restatement", "Prior Period Errors", "Restated",
                                 "Correction of Prior Period"],
  "report_fiscal_year":         ["Annual Report 20", "for the year ended", "Financial Year 20"],
}
```

Fuzzy-match (edit distance or embedding similarity) against these, don't require exact
strings — this is what keeps the extractor from breaking on every minor wording change.
`balance_sheet_equity` and `revenue_from_operations` additionally need the consolidated
vs standalone statement distinguished, since an AR contains both.

---

## 6. Decision Engine implementation

- Translate `Phase1-Algorithms.md` §3–§9 directly into code — one pure function per
  check, no I/O inside these functions (no HTTP calls, no file reads). Inputs and
  outputs only.
- Include the helpers: `apply_track_record_guard` (§2), `compose_citation` (§2a),
  `assert_comparable` (§2b), `derive_pledged_pct_of_total_shares` (§2c). The last three
  are new in algo revision 2 and each has fixtures attached.
- Unit test against all 18 fixtures in `Phase1-Algorithms.md` §11 before wiring
  anything else — this is cheap to get right early and expensive to debug once
  scraping/PDF noise is mixed in. Fixture 13 in particular is a regression guard for a
  bug that produced a wrong REJECT.
- Store `Phase1Result` as-is (JSONB column) so a report can always be regenerated from
  stored results without re-running acquisition.
- Store the `CompanyInput` and its provenance map alongside the result. Without it a
  stored verdict cannot be explained after the fact, and `input_digest` cannot be
  verified.

---

## 7. Report Generation & PDF export

### 7.1 Single HTML template, two render targets

Per §1's design principle, keep one Jinja2 (or equivalent) HTML template for the
investor-facing report (applying `user.md`'s wrapping rules from `Phase1-Rules.md` §5),
rendered two ways:

- **Web view** — served directly as a report page in the app.
- **PDF export** — the same HTML run through WeasyPrint. No separate PDF-specific
  content to maintain; formatting differences (print CSS) only.

The SEBI disclaimer from `user.md` §9 is a locked template constant, included verbatim,
not editable in the UI and not regenerated per report (algo §10 requirement 2).

### 7.2 Report types to support

| Report | Contents | Format options |
| :-- | :-- | :-- |
| Single-ticker investor report | §5 worked-example style narrative (REJECT/CLEARED/HOLD), full Pass/Fail table, sourced findings, citation gaps stated plainly, revision + as-of date + reporting basis in the header, verbatim disclaimer | Web + PDF |
| Single-ticker analyst report | The raw §4 internal working table — numbers, thresholds, citations, provenance per field, no prose wrapping | Web + PDF (for internal/analyst use) |
| Batch summary matrix | One row per ticker: verdict, failing check(s), inconclusive check(s), revision, date processed — a scan-list view across an uploaded sheet | Web (sortable/filterable table) + consolidated PDF (summary table + per-ticker appendix) |
| Review-needed report | Tickers/checks stuck in manual review queue, with a direct link to resolve each, and age in queue | Web only (operational, not investor-facing) |

### 7.3 PDF export implementation notes

- Generate PDFs asynchronously (same job queue as scraping) — don't block the HTTP
  request on WeasyPrint rendering, especially for a batch consolidated PDF across many
  tickers.
- Store generated PDFs in object storage keyed by
  `(ticker, as_of_date, report_type, revision)` — **revision is part of the key**, so a
  new revision produces a new object rather than overwriting one someone may already be
  reading.
- Batch consolidated PDF should open with a one-page summary matrix (ticker → verdict)
  before the per-ticker detail pages, so a user reviewing 50 tickers isn't forced to
  page through everything to find the rejects.

### 7.4 Result versioning and report staleness

A `HOLD_INCONCLUSIVE` is a temporary verdict by design: resolving a review item can turn
it into `CLEARED_TO_PHASE_2` or `REJECT`. That means **a PDF exported yesterday can
assert a verdict the system no longer holds** — for an investment gatekeeper this is the
most consequential failure mode in the whole design, so it gets explicit handling:

1. `phase1_results` is append-only. A re-run inserts a new row with `revision + 1` and
   `supersedes` pointing at the prior `result_id`; nothing is ever updated in place.
2. Every rendered artefact — web page and PDF — carries `ticker`, `as_of_date`,
   `revision`, `generated_at` and `data_basis` in a header block, plus the
   `input_digest`. A PDF can therefore always be matched to the evaluation behind it.
3. When a new revision is written, prior revisions' signed URLs are revoked and their
   stored objects marked `superseded`. A request for a superseded artefact returns the
   current revision with a visible "this replaces revision N, verdict changed from X to
   Y" banner rather than silently serving either one.
4. The web report for a ticker always resolves to the latest revision. Older revisions
   remain retrievable by explicit `result_id` for audit, always labelled superseded.
5. If a verdict *changes* between revisions (not merely gains detail), that is a
   notifiable event: it appears in the batch matrix as changed, and — if the product
   later grows notifications — is what they should be wired to.

---

## 8. Bulk ticker input (CSV/Excel)

### 8.1 Upload contract

Accept `.csv` and `.xlsx`. Required column: `ticker` (or `symbol`). Optional columns
the app should recognize if present but never require: `company_name`,
`bse_scrip_code`, `nse_symbol` — these help disambiguate when a ticker string alone is
ambiguous across exchanges.

### 8.2 Validation before job creation

- Reject the upload with a clear per-row error list (not a single generic failure) if:
  required column is missing, a ticker cell is empty, or duplicate tickers appear
  (dedupe with a warning rather than hard-failing, unless the user wants strict mode).
- Cap batch size (configurable) to keep scraping load and review-queue volume
  manageable; surface the cap in the UI before upload, not after. **Derive the cap from
  a measured per-ticker budget** (§8.4) rather than picking a round number — a cap that
  implies a 9-hour batch is not a working cap.
- Normalize ticker casing/whitespace before matching against exchange symbol lists.

### 8.3 Processing model

- One job per ticker (not one giant job per file) — this is what lets a single bad
  ticker (delisted, misspelled, PDF unreachable) fail independently without blocking
  the rest of the batch.
- Batch-level record tracks `{batch_id, uploaded_by, uploaded_at, total, completed,
  failed, in_review}` for progress display.
- Per-ticker status visible in real time: `QUEUED → SCRAPING → EXTRACTING_PDF →
  AWAITING_REVIEW (optional) → EVALUATING → DONE`.
- On completion, the batch summary matrix (§7.2) is auto-generated; the consolidated
  PDF is generated on demand (not automatically for every batch, since it may be large).

### 8.4 Throughput budget (measure before promising a cap)

The batch cap is a consequence of per-ticker cost, not an independent choice. Instrument
Phase C–E and fill this in with real numbers before Phase G ships:

| Stage | Expected per ticker | Notes |
| :-- | :-- | :-- |
| Screener scrape (2–3 pages, rate-limited) | ~5–10 s | Dominated by the deliberate inter-request delay |
| AR download | ~10–60 s | ARs are commonly 10–80 MB |
| PDF tiers 1–3 on a native-text AR | ~20–90 s | Scales with page count |
| PDF tier 4 (OCR) when it triggers | minutes | The reason §13 asks about a paid OCR budget |
| Engine + render | < 1 s | Negligible |

A native-text ticker is therefore roughly 1–3 minutes; a scanned one can be 10×. With
worker concurrency `W` and a rate limit of one Screener request per 1–2 s, Screener
serialises the front of the pipeline — so the practical cap is `W × (available window ÷
mean per-ticker time)`, adjusted for the observed OCR-fallback rate. Publish the number
the measurement gives, and re-derive it in Phase H.

---

## 9. API surface (illustrative)

All endpoints are authenticated; the roles in brackets are the minimum required.

```
POST   /api/tickers/{ticker}/run              → enqueue a single-ticker Phase 1 job      [analyst]
POST   /api/batches                           → upload CSV/Excel, enqueue N jobs          [analyst]
GET    /api/batches/{batch_id}                → batch progress + per-ticker status        [viewer]
GET    /api/tickers/{ticker}/report           → latest Phase1Result (JSON, with revision) [viewer]
GET    /api/tickers/{ticker}/report.pdf       → investor-facing PDF, latest revision      [viewer]
GET    /api/results/{result_id}               → a specific revision (audit, labelled)     [analyst]
GET    /api/batches/{batch_id}/report.pdf     → consolidated batch PDF                    [viewer]
GET    /api/review-queue                      → items awaiting manual PDF review          [reviewer]
POST   /api/review-queue/{item_id}/resolve    → submit a human-confirmed value            [reviewer]
GET    /api/sources/health                    → adapter health_check() status             [admin]
GET    /api/coverage                          → §3 matrix vs live fill rates per field    [analyst]
```

`/api/coverage` is worth building early: it is the operational form of §3, showing which
`CompanyInput` fields are actually being populated in production and which are quietly
always null.

---

## 10. Database schema (core tables)

```
users(id PK, email UNIQUE, display_name, role, created_at, disabled_at)

companies(id PK, ticker, exchange, company_name, bse_scrip_code, nse_symbol,
          company_type, listing_date, last_updated,
          UNIQUE (ticker, exchange))
          -- surrogate PK, not ticker: §8.1 already concedes a bare ticker is
          -- ambiguous across exchanges

raw_documents(id PK, company_id FK, source, doc_type, fiscal_year, document_date,
              fetch_date, storage_url, content_hash, pdf_class,
              UNIQUE (company_id, content_hash))

extracted_fields(id PK, company_id FK, doc_id FK nullable, field_name,
                 value JSONB,              -- JSONB, not scalar: cfo_last_5y and
                                           -- pledged_pct_history_last_4q are arrays
                 period,                   -- "FY24" / "Q1FY25" / "FY20-FY24"
                 basis,                    -- CONSOLIDATED | STANDALONE | NOT_APPLICABLE
                 confidence, extraction_method, source, source_page, raw_snippet,
                 extracted_at, superseded_by FK nullable,
                 UNIQUE (company_id, field_name, period, basis, extracted_at))

company_inputs(id PK, company_id FK, as_of_date, data_basis,
               input JSONB,                -- the exact CompanyInput handed to the engine
               provenance JSONB,           -- field_name -> FieldProvenance
               input_digest, created_at)

phase1_results(id PK, company_id FK, company_input_id FK, as_of_date, data_basis,
               verdict, checks JSONB, failing_checks JSONB, inconclusive_checks JSONB,
               citation_gaps JSONB, revision, supersedes FK nullable, input_digest,
               generated_at,
               UNIQUE (company_id, as_of_date, revision))
               -- append-only; never UPDATE a verdict in place

generated_reports(id PK, phase1_result_id FK, report_type, storage_url,
                  generated_at, superseded_at nullable)

review_queue(id PK, company_id FK, check_id, field_name, best_guess_value JSONB,
             period, basis, raw_snippet, source_page, source_url, reason,
             status, resolved_value JSONB, resolved_at, resolved_by FK -> users)

batches(id PK, uploaded_by FK -> users, uploaded_at, total, completed, failed, in_review)
batch_items(id PK, batch_id FK, company_id FK, status, phase1_result_id FK nullable)
```

Changes from revision 1: surrogate keys on `companies`; `users` table added (previously
`uploaded_by` and `resolved_by` were FKs to nothing); `period` and `basis` columns on
`extracted_fields` (previously every field was implicitly single-period, which
`legal_fees` vs `legal_fees_prior_year` alone disproves); `value` widened to JSONB for
the array-valued fields; `company_inputs` added so a stored verdict can be explained;
`revision`/`supersedes`/`citation_gaps` on `phase1_results`; `generated_reports` added
so superseded PDFs can be found and revoked (§7.4).

---

## 11. Build sequencing (phased delivery)

Sequenced so each phase produces something independently testable/demoable, and later
phases don't require re-architecting earlier ones.

**Phase 0 — Field coverage matrix + auth skeleton**
Write §3 as an executable test (reflect over `CompanyInput`, fail on any unowned field)
and stand up the `users` table with the four roles. Both are cheap now and expensive to
retrofit — §3 in particular is what prevents discovering in Phase F that nothing ever
populated `net_worth`.

**Phase A — Decision Engine core**
Implement `Phase1-Algorithms.md` §1–§9 as pure functions, including the four helpers.
Validate against all 18 fixtures. No scraping, no UI — just a library with a test suite.
This de-risks the policy logic before any I/O complexity is added.

**Phase B — Manual-input single-ticker flow**
Thin API + minimal UI where a human pastes in the `CompanyInput` fields directly (no
scraping yet) and gets back a report (web + PDF). The paste form must capture source,
period and basis per field, not just values — that is how the citation path gets tested
end-to-end before any extractor exists. Validates the rendering layer and `user.md`
wrapping.

**Phase C — Scraper adapters (Screener first)**
Wire ScreenerAdapter for **Checks 2 and 5, plus government shareholding, revenue, net
worth (as cross-checks) and track-record length** — highest value, lowest PDF complexity,
since Screener's tables are structured HTML. Pulling the Check 3 and 4 denominators
forward from Phase D materially shrinks the hardest module. Confirms the acquisition →
engine → report pipeline works end-to-end for the easiest source.

**Phase D — PDF extractor, tiers 1–3**
Native-text and table extraction for Annual Report notes (Checks 1, 3, 4, 6's narrative
and table fields, plus the AR's own fiscal year and date). Build the section-anchor
library (§5.5) against a handful of real sample Annual Reports across different filers to
calibrate fuzzy-match thresholds. Implement column-to-fiscal-year resolution here, not
later — it is the difference between `legal_fees` and `legal_fees_prior_year`.

**Phase E — OCR fallback + manual review queue**
Tier 4 (OCR) and Tier 5 (review queue + resolver UI), plus near-threshold escalation
(§5.3) and result revisioning (§7.4). This is the phase that actually answers "what
happens when a PDF is hard to parse" — build it against real PDFs that failed Phase D,
not synthetic ones.

**Phase F — Remaining adapters + cross-verification**
BSE/NSE announcements, BSE shareholding cross-check, SEBI scan. Add the
discrepancy-flagging logic (§4.1 point 3) between Screener and BSE pledge %.

**Phase G — Bulk upload + batch reporting**
CSV/Excel ingestion, per-ticker job fan-out, batch progress UI, consolidated PDF, and
the measured throughput budget (§8.4) that sets the real batch cap. Deliberately late
because it's a thin orchestration layer over everything built in A–F — building it early
would mean building it twice.

**Phase H — Hardening**
Rate-limit tuning against real site behavior, layout-drift alerting, caching TTL tuning,
near-threshold band tuning against observed extraction error, load testing a full batch
at the measured cap.

---

## 12. Open decisions — blocking before Phase C

These change what gets built, so they are worth a decision rather than a default guess.

1. **Scraping legality / ToS — blocking, not advisory.** Screener.in, BSE and NSE terms
   all address automated access, and NSE in particular is restrictive. The answer decides
   whether §4's adapters exist at all or whether the product is manual-upload-first with
   scraping as an opt-in the operator enables for their own personal-use account. Settle
   this before Phase C is built, not before it "ships broadly" — the architecture differs.
2. **Who uses this, and under what licence.** Personal research, an internal analyst
   team, or an external product? This sets the auth model, whether reports may be
   redistributed, and how much of §12.1's answer applies.
3. **OCR budget.** Tesseract is free/local but slower and lower-accuracy than a paid
   document-AI service on dense financial tables. Decide whether Phase E defaults to
   Tesseract or budgets for a paid fallback specifically for `LOW`-confidence financial
   tables. §8.4's throughput numbers depend on this.
4. **Manual review SLA.** How long does a ticker wait in `AWAITING_REVIEW` before the
   report is generated as-is with INCONCLUSIVE checks? A product decision, and it
   interacts with §7.4 — a short SLA means more revisions and more superseded PDFs.
5. **Data retention.** How long are ARs, extracted fields, and generated reports kept?
   Reviewer identities in `review_queue.resolved_by` are personal data; a retention and
   access policy should exist before the first real reviewer uses the system.
6. **Batch cap** — derive from §8.4 rather than deciding in advance, but confirm who
   sets it and whether it differs per role.

---

## 13. Traceability

Every module in this plan maps back to a specific section of the two existing docs —
no scraping/PDF/report behavior here should introduce a rule not already in
`Phase1-Rules.md`, and no Decision Engine behavior here should diverge from
`Phase1-Algorithms.md`. If either source file changes, review §3–§7 of this plan for
knock-on effects (a new/changed check may need a new row in the §3 matrix, a new scraper
field, or a new PDF section anchor).

Concretely, the §3 field-coverage matrix is the join key between the three documents: a
field exists in `Phase1-Algorithms.md` §0, is sourced by a row in §3 here, and is
justified by a row in `Phase1-Rules.md` §1 / §8.2. If a field cannot be traced through
all three, one of the documents is wrong.
