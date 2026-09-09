chunkrule-v2.md — Annual Report Chunking & Extraction Rules (Hybrid Revision)

Defines how any Indian listed company's annual report (arbitrary length, arbitrary formatting) is broken down and mapped into the CompanyInput schema used by Phase1-Algorithms.md. This revision replaces chunkrule.md (v1). It is still format-agnostic — content is classified by meaning, not by matching a specific company's heading text — but it changes how the note-level location is done, based on what a live run against real reports showed about where the two approaches (structural split vs keyword anchoring) each win and lose.

Read this before building or running any extraction step.

Golden rule (inherited from Phase1-Algorithms.md §0): if a data point cannot be found and classified with confidence, its field stays null. Never guess a value to fill a gap. A missed section becomes INCONCLUSIVE downstream — that is correct behaviour, not a failure of this pipeline.

Revision history

v2 — this revision. One structural change to the pipeline, no change to any pass/fail threshold or to the CompanyInput schema. The v1 pipeline ran Step 1 (structural split) and then Step 3 (embedding/LLM classification) as the primary path for finding every note. A live run on four FY2025-26 reports (Millworks Technologies, Oswal Pumps, Minda Corporation, Dynamic Services) showed two things:

(1) Structural split does one job reliably — separating standalone from consolidated statements — but it cannot isolate individual notes. "Contingent Liabilities", "Related Party", and "Auditor Remuneration" all sit at the same note-header font size, so Step 1 gets you to "Notes to Accounts" (a 60-page block) but never to "Note 39.2". Note-level location was always, in practice, done by keyword search — the embeddings were adding cost without adding location power.

(2) Keyword anchoring is fast, fully auditable, and reached the correct note in every case tested, but it is brittle against wording variation and it does not track reporting basis (standalone vs consolidated) reliably on its own.

v2 therefore re-splits the work along each method's actual strength:
- Structural split → basis tagging (standalone vs consolidated) and a coarse section map. Nothing else.
- Keyword anchoring → primary note-level location.
- Embedding/LLM classification → demoted to a fallback, run only on chunks keywords cannot place.

No threshold changed. No schema field changed. The only behavioural change is which method is the default for finding a note.

0. Why chunk this way

Two annual reports are never formatted the same way — heading text, section order, numbering, and even which statements come first vary company to company. A pipeline built around a couple of sample reports will overfit to their specific quirks. This file solves that by splitting on structure (font size, bookmarks, layout — things every PDF has) for the one thing structure reliably tells us (which statement set a chunk belongs to), and by locating individual notes with keyword anchors (fast, auditable) rather than embeddings (slow, opaque) as the default.

The key correction from v1: do not ask the structural split to do note-level location. It cannot. Use it only for basis tagging and the coarse section map, then let keyword anchoring find the specific note.

1. Step 1 — Structural split (mechanical, format-agnostic) — for BASIS TAGGING only

Goal: turn one large PDF into a bounded, ordered list of coarse sections, and — critically — tag each section with its reporting basis (STANDALONE / CONSOLIDATED / NOT_APPLICABLE). Do not expect this step to isolate individual notes; it will not, and v1's mistake was expecting it to.

Prefer PDF bookmarks/TOC metadata if present. Most annual report PDFs embed a navigable table of contents. If available, use it as the primary structural map.
If no bookmarks exist, fall back to font-based heading detection:
Extract text along with effective font size (see the correction note below), weight (bold/regular), and position.
Any line meaningfully larger or bolder than surrounding body text is a heading candidate.
Build a heading tree (nesting inferred from relative font size / indentation).
Chunk along heading boundaries. Each chunk = one heading's content, from that heading to the next heading at the same or higher level.
Cap chunk size. If a section (e.g. "Notes to Accounts") is very long, split it further into sub-chunks at a fixed token budget (target ~1,500–3,000 tokens), preserving sub-heading boundaries where possible so a table or clause is not cut mid-way.
Preserve page numbers on every chunk. Required later for citation/provenance (FieldProvenance.page in Phase1-Algorithms.md).

Correction note — effective font size: raw font_size from common PDF extractors is frequently 1.0 for every fragment (the font's internal scale), and the true rendered size must be recovered by multiplying by the text-matrix scale (the vertical scale factor of the text matrix). Additionally, running headers/footers ("CORPORATE OVERVIEW …", "True Partner!", page numbers) repeat at a fixed size on every page and must be excluded from heading detection or they will be misclassified as headings. Both of these are real, observed failure modes, not hypotheticals.

Correction note — TOC page offset: the printed page numbers in a report's TOC do not necessarily equal the PDF page index. A report whose TOC says "Independent Auditor's Report — page 114" may have that heading at PDF page 86 (a ~28-page offset from cover/title matter). Provenance must record the PDF page index, and if a printed page number is also cited, the offset must be reconciled explicitly.

Output of Step 1: an ordered list of coarse chunks, each with {text, page_range, heading_path, basis, source_confidence}. No interpretation of content has happened yet, but basis is already known because the standalone/consolidated boundary is structurally detectable (the "Standalone Balance Sheet" vs "Consolidated Balance Sheet" headings).

1a. Technique — locate with OCR, confirm with vision (mixed text/scanned reports)

Why this exists: a real annual report is rarely scanned end to end. In practice the narrative front-matter (corporate overview, MD&A, director's report) has a normal text layer, while the signed financial statements block — auditor's report, balance sheet, P&L, cash flow, notes to accounts — is often re-inserted as scanned/rasterized pages (the signature page gets photocopied and merged back in). This is exactly the block that feeds Checks 1, 3, 4, and 5, so getting this step wrong is costly. Confirmed on the VGINFOTECH FY2025-26 Annual Report: pages 1–117 had a full text layer; pages 118–156 (the entire financial statements) were image-only despite the same PDF having embedded fonts elsewhere.

Step 1 — Detect the boundary, don't assume the whole document. Run pdftotext (or equivalent) across the full document first. If a contiguous page range returns empty or near-empty text while other ranges in the same PDF extract cleanly, that range is image-only — OCR/vision applies only to that range, not the whole report. Don't let one scanned block trigger blanket OCR of pages that already have good text.

Step 2 — OCR every page in the image-only range, but only to locate, not to read. Rasterize the range (~150 DPI is enough for this pass) and run OCR page by page. Use the OCR output purely as a cheap, page-level index — "which page has the auditor's report, which page has the balance sheet, which page has the contingent liabilities note" — by matching OCR text against the Step 2 canonical schema categories. Do not compute or cite any number straight from this pass: OCR reliably corrupts dense multi-column financial tables (transposed digits, merged decimal points, dropped minus signs), which is disqualifying for anything feeding a Phase 1 threshold.

Step 3 — Vision-read only the specific pages that matched a category. For each page (or narrow page range) the OCR pass flagged as relevant, read the rasterized image directly rather than trusting the OCR text. This is the authoritative source for any figure that will be compared against a threshold (contingent liabilities ÷ net worth, CFO/PAT ratio, RPT ÷ revenue, legal ÷ audit fees, etc.).

Step 4 — Provenance reflects which pass actually produced the number.

A value read via vision on the matched page → confidence: HIGH (or MEDIUM if the scan itself is degraded/low-resolution), with page set to the exact page.
A value taken only from the OCR locate-pass, never vision-confirmed → stays confidence: LOW, and should be flagged as unconfirmed rather than silently used — don't let a LOW-confidence OCR figure quietly satisfy a check's "required fields" test.
A category located by OCR but never vision-read at all (e.g. analysis stopped early because an earlier check already produced a Phase 1 FAIL) is not the same as "not found" — record it explicitly as "located, not confirmed" in the working notes so a later re-run knows to finish the vision pass rather than re-doing the OCR locate step from scratch (see §9, cache the classification map).

Cost note: OCR-locate is cheap per page and scales fine across a large image-only range. Vision-read is materially more expensive per page, which is exactly why Step 3 restricts it to only the pages Step 2 already pointed to, instead of vision-reading the whole range.

2. Step 2 — Canonical target schema

Define, once, the fixed list of things Phase 1 actually needs — independent of any single company's wording. This is the same field list as CompanyInput in Phase1-Algorithms.md §0. Each target category gets a short semantic description (used for classification in Step 3/4), plus — new in v2 — a set of keyword anchors (used for the primary note-location pass in Step 3). The keyword anchors are a fast path, not a definition: they are the strings that most reliably appear in the note that holds each value, but the semantic description remains the source of truth for what the field means.

Category	What it's looking for (meaning, not wording)	Keyword anchors (v2)
audit_opinion	The auditor's formal opinion paragraph — clean/qualified/adverse/disclaimer language, auditor resignation disclosures	"opinion", "unqualified", "qualified", "adverse", "disclaimer", "Emphasis of Matter", "resignation of statutory auditor"
audit_and_legal_fees	Statutory audit fee and legal & professional charges, as reported in notes	"audit fee", "auditor's remuneration", "statutory audit", "legal and professional"
related_party_transactions	Related party sales, purchases, loans, or dealings with affiliates/promoter entities	"related party", "related parties", "Ind AS 24", "AS 18"
contingent_liabilities	Disclosed contingent claims, guarantees, disputed demands not on the balance sheet	"contingent liabilit", "claims against the company not acknowledged", "guarantees"
net_worth	Total equity / shareholders' funds, from the balance sheet	"total equity", "shareholders' funds", "net worth"
cash_flow_operations	Cash generated from operating activities, typically 5-year or multi-year view	"cash flow from operating", "net cash", "operating activities"
profit_after_tax	Net profit / PAT, matching the same periods as cash flow	"profit for the year", "profit after tax", "PAT"
promoter_shareholding	Promoter holding % and pledge/encumbrance %, current and trailing quarters	"promoter", "pledged", "encumbered", "shareholding pattern" (note: usually NOT in the AR — see §3 note)
kmp_changes	Board's Report disclosures on CFO/KMP appointments, resignations, restatements	"key managerial personnel", "KMP", "chief financial officer", "CFO", "resign"
regulatory_disclosures	Any SEBI/RBI/SFIO/ED/CBI proceedings, sanctions, or show-cause references mentioned in the report itself	"SEBI", "SFIO", "Enforcement Directorate", "show cause", "penalty", "proceeding"

This table is the single source of truth for "what are we looking for." If Phase 1's rules ever add a new check, this table gets a new row — nothing else in this file changes.

3. Step 3 — Note-level location by keyword anchor (PRIMARY — new in v2)

For each category, search the report text for its keyword anchors (column 3 of the Step 2 table). This is the default, primary path for finding the note that holds each value.

Why keyword first (the v2 correction): keyword anchoring is fast, deterministic, and fully auditable — every hit maps to an exact page and note number. In the live run it found the correct note for every category in all four reports, including "Contingent Liabilities" (Note 39.2), "Related Party" (Note 39.8), and "Auditor Remuneration" (Note 37.1). The structural split, by contrast, could only get to "Notes to Accounts" and could not distinguish these notes from each other.

Mechanics:
Run the anchors as literal/regex searches over the full text layer (per §1a, on the OCR-locate text for image-only ranges, then vision-confirmed).
For each category, collect candidate hits with {page, note_number, snippet}.
Prefer hits inside the audited financial statements / notes section over narrative sections (MD&A, Chairman's letter) — notes are the authoritative, audited source. This is the same preference order as v1 §5, applied at location time.
A category may have zero hits (expected for irrelevant content — see below) or multiple hits (standalone + consolidated — resolved in Step 6).

Keyword anchoring does not replace the semantic description — it is a fast index into the report. The semantic description is what lets you confirm the hit is the right note (e.g. a "contingent liabilit" hit inside the accounting-policy boilerplate is not the same as the Note 39.2 disclosure table; the description tells you which one you want).

Limitation to be honest about: keyword anchoring is brittle against wording variation. A report that calls the auditor's report "Report of the Statutory Auditors" or buries contingent liabilities under a differently-worded heading may not match the anchors. That is exactly what Step 4 (the fallback) exists to catch.

Note on promoter_shareholding: this category is normally NOT present in the annual report at all — pledge % and the trailing-quarter series live in the shareholding-pattern filing (Screener.in / BSE Regulation 31), not the AR. Do not expect the keyword pass to find it in the AR; it will correctly return zero hits, and the field resolves as INCONCLUSIVE unless the external source is pulled (see Phase1-Rules.md §8.4-B).

4. Step 4 — Embedding/LLM classification (FALLBACK — demoted in v2)

Run this only for categories that Step 3 could not place with confidence — i.e. zero keyword hits, or hits that are ambiguous (close across categories, or below a confidence threshold). Do not run it as the default path.

Primary fallback method — embedding similarity: embed the candidate chunk text and each category description; assign the chunk to its best-matching category if similarity clears a confidence threshold.
Secondary fallback — targeted LLM classification: for chunks that remain ambiguous, ask an LLM to classify that single chunk against the category list. Keep this call scoped to one chunk at a time — never the whole document — to stay within context limits and keep the classification auditable.

A chunk may match zero categories. That's expected — most of an annual report (director photos, sustainability narrative, shareholder FAQs) is irrelevant to Phase 1. Discard non-matches; do not force a classification.
A chunk may match more than one category (e.g. a chunk discussing both contingent liabilities and net worth). Keep it linked to all matching categories.

Output of Steps 3–4: a map of category → [chunk_id, page, note_number, confidence, method] where method records whether the note was found by keyword (default) or by embedding/LLM (fallback). This method tag is carried into provenance so a reader can see how each note was located.

5. Step 5 — Basis tagging (consolidated vs standalone)

Annual reports typically contain both consolidated and standalone financial statements. A value pulled from one and compared against a value from the other produces a meaningless ratio — this is the mismatch Phase1-Algorithms.md §2b guards against.

Basis tagging is done structurally, from Step 1 (not from keywords). Detect the nearest enclosing section label for each chunk — most reports have a clear "Standalone Financial Statements" / "Consolidated Financial Statements" divider.
Tag every classified chunk with basis: CONSOLIDATED | STANDALONE | NOT_APPLICABLE (the latter for non-financial chunks like audit opinion text or KMP changes, where the distinction doesn't apply).
When a category appears under both bases (e.g. contingent liabilities disclosed in both statement sets), prefer consolidated per Phase1-Rules.md §8.1, and keep the standalone value as a secondary/corroborating reference, not a competing source.

Why basis tagging belongs to structure, not keywords (v2 correction): the standalone/consolidated boundary is a layout fact — the two statement sets are physically separated in the PDF and headed differently. Structure detects this reliably and for free. Keywords do not: the word "contingent liabilities" appears identically in both sets, so a keyword hit carries no basis information on its own. This is the one place the structural split is genuinely load-bearing, and it is the reason Step 1 is kept at all.

6. Step 6 — Resolve multiple matches per category

A category can have more than one candidate chunk (e.g. contingent liabilities mentioned in MD&A commentary and in the formal Notes to Accounts; or in both standalone and consolidated notes).

Resolution order:

Prefer the chunk from the audited financial statements / notes section over narrative sections (MD&A, Chairman's letter) — notes are the authoritative, audited source.
Prefer consolidated over standalone for financial ratios (per §5 / Phase1-Rules.md §8.1), keeping standalone as corroboration.
If two notes-section chunks conflict (rare — e.g. restated figures across two printings), prefer the one nearer the final signed financial statements and flag the conflict in provenance notes.
If no notes-section chunk exists at all and only a narrative mention is found, use it but mark confidence: LOW — this is weaker evidence and should be visible downstream, not silently treated as equal to an audited figure.

7. Step 7 — Populate CompanyInput with provenance

For each category with a resolved chunk:

Extract the specific value(s) needed (e.g. audit opinion type, RPT total, CFO/PAT per year).
Populate the corresponding CompanyInput field (per Phase1-Algorithms.md §0).
Populate FieldProvenance alongside it: source (this report's filename), period (the FY the chunk covers), basis (from Step 5), page (from Step 1), note_number (from Step 3), confidence (from Steps 1/3/4/6), method (keyword | embedding | llm, from Step 3/4), extracted_at (now).

For each category with no resolved chunk:

Leave the CompanyInput field null.
Do not populate a provenance entry — a null field has nothing to cite.
This will correctly surface as INCONCLUSIVE when run_phase1() runs, with the missing category named — exactly the "flag missing data, don't estimate" rule in Phase1-Rules.md §1 and §6.

8. Step 8 — Validate before handing off to the rule engine

Run these checks on the populated CompanyInput before calling run_phase1():

Basis consistency: for any check that spans multiple fields (e.g. RPT ÷ Revenue), confirm both fields share the same basis. If not, do not compute the ratio — leave the check to resolve as INCONCLUSIVE in the engine.
Period consistency: confirm fields feeding the same check cover the same fiscal year. A contingent-liabilities figure from FY24 paired with a net-worth figure from FY23 is not usable together.
No silent zero-filling: confirm every null in the struct is an intentional "not found," not a default value left over from a failed extraction step.

9. Step 9 — Cache the classification map, not raw content
Persist {category → chunk_id, page, note_number, basis, confidence, method} for the report once classified — this is small and cheap to store.
On a repeat query against the same report, reuse this map instead of re-running Steps 1–4.
On a new report (next FY, or a different company), always re-run Steps 1–4 from scratch. Nothing about a prior report's structure — heading style, section order, font sizes — should be assumed to carry over.

10. Handling format outliers (explicit, not special-cased)
Situation	How it's handled
Whole report scanned/image-only	Same §1a technique, applied to the entire document instead of one block: OCR-locate every page, vision-confirm only the pages that matched a target category
Report is mixed — narrative in text, signed financials scanned (common case)	§1a: detect the image-only page range first, don't OCR the whole document; OCR-locate within that range, vision-confirm the matched pages
Non-standard section naming (e.g. "Report of the Statutory Auditors" instead of "Independent Auditor's Report")	Step 3 keywords may miss it → Step 4 (embedding/LLM) is the fallback that catches it. This is the exact case the fallback exists for.
No formal RPT note (common for smaller companies)	Category has no match → field stays null → correctly resolves to INCONCLUSIVE, not an error
Notes numbering differs company to company	Irrelevant — Step 3 never depends on note numbers; it depends on anchor text
Report contains only standalone financials (no consolidated)	data_basis on CompanyInput reflects what's actually available; no consolidated-preference conflict arises
Multi-volume / split PDF report	Run Step 1 once per volume, then merge chunk lists before Step 3 — treat as one logical document
No bookmarks in the PDF	Fall back to font-based heading detection (§1 correction note: recover effective font size, exclude running headers)

11. Validation before trusting this on a new company

Before relying on this pipeline for an unfamiliar report, sanity-check it against reports that differ on the axes that actually vary in practice, not just against whichever 2–3 samples happen to be on hand:

A large-cap and a small-cap report (formatting complexity differs a lot).
A PSU and a professionally-managed (zero-promoter) company (Check 2 auto-pass paths depend on correctly detecting company type).
A report containing a qualified or adverse audit opinion, if one can be found — this is the single case that must never be missed or misclassified, since it is an automatic Phase 1 FAIL.

Additionally (v2): for each of these, record how many categories were found by keyword (Step 3) vs by fallback (Step 4). If the fallback is doing more than a small minority of the location work, the keyword anchors need extending — that is the signal the anchors are overfit to a few reports, the same overfitting this file exists to avoid.

12. Definition of done for this chunking layer
 Report split into bounded, page-tagged structural chunks, each tagged with reporting basis (Step 1, Step 5).
 Every relevant category located — by keyword anchor (Step 3) where possible, by embedding/LLM fallback (Step 4) where not — with no forced classification of irrelevant content.
 Every classified chunk tagged with reporting basis (Step 5).
 Multiple-match categories resolved by the stated preference order (Step 6).
 CompanyInput populated with full provenance for every non-null field, including the method by which each note was located (Step 7).
 Basis and period consistency validated before handoff to run_phase1() (Step 8).
 Classification map cached for reuse within the same report (Step 9).
 No field silently defaulted — every null represents a genuine "not found."

Summary of the v1 → v2 change

v1 asked the structural split to do note-level location (it can't) and ran embeddings as the default classifier (unnecessary cost). v2 assigns each method the job it actually does well: structure tags basis, keywords locate notes, embeddings/LLM are the fallback for the rare wording-variation miss. No threshold, schema field, or pass/fail rule changed.
