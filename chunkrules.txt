chunkrule-v3.md — Annual Report Chunking & Extraction Rules (Note-Unit Revision)

Defines how any Indian listed company's annual report (arbitrary length, arbitrary formatting) is broken down and mapped into the CompanyInput schema used by Phase1-Algorithms-v3.md. This revision replaces chunkrule-v2.md. It keeps v2's allocation of work between methods — that part was right — and adds the layer v2 was missing: what happens *below* the note heading, where the numbers actually live.

Read this before building or running any extraction step.

Golden rule (inherited from Phase1-Algorithms-v3.md §0): if a data point cannot be found and classified with confidence, its field stays null. Never guess a value to fill a gap. A missed section becomes INCONCLUSIVE downstream — that is correct behaviour, not a failure of this pipeline. v3 extends this: a value read from the wrong row, or in an undeclared unit, is worse than null. Prefer null.

Revision history

v3 — this revision. v2 correctly reassigned the work (structure tags basis, keywords locate notes, embeddings fall back) but treated "reached the correct note" as the finish line. A live run against three FY2025-26 reports of very different size and typesetting — Dynamic Services (164pp), Oswal Pumps (258pp), Minda Corporation (393pp) — showed that locating the note is roughly half the problem:

(1) The extractor reached the right note and still read the wrong number. "Payment to Auditors" is a sub-label *inside* Note 37 Other Expenses in the Dynamic report, so a rule that accepts the note's Total row returned ₹7,999.81 lakh (the whole other-expenses total) as the audit fee instead of ₹3.07 lakh — a 2,600x error at HIGH confidence.

(2) Units were captured by nothing. The three reports report in lakh, million and million respectively, and Minda declares its unit on some pages but not on the pages carrying the values. Anything that assumes a default is silently wrong by 10x on exactly the figures that feed Phase 1 thresholds.

(3) Note numbering has at least three conventions in three reports — "37 OTHER EXPENSES", "37<tab>Other expenses" / "39.2 : Contingent Liabilities", "2.33 Other expenses". Any scheme hardcoded to one of them fails completely on the others, not partially.

v3 therefore adds three sub-steps (§3b note-unit chunking, §3c row/column selection, §3d units) and corrects the §2 field table. No pass/fail threshold and no CompanyInput field changed.

0. Why chunk this way

Two annual reports are never formatted the same way. v2 solved this at the section level: split on structure (font size, bookmarks, layout) for the one thing structure reliably tells us — which statement set a chunk belongs to — and locate individual notes with keyword anchors rather than embeddings.

The correction v3 adds: **do not chunk the notes block by token budget.** v2 §1 caps sub-chunks at ~1,500–3,000 tokens. That number is inherited from v1, where chunks were fed to an embedding model — you size chunks to an embedding context window. v2 demoted embeddings to a fallback but kept v1's chunk geometry. Nothing in the v2 primary path wants a token-budgeted chunk, and a token budget is actively harmful there: it splits a note mid-table, so a label and its value can land in different chunks.

The atomic unit of an annual report's notes block is **the note**. Never split one; never merge two.

1. Step 1 — Structural split (mechanical, format-agnostic) — for BASIS TAGGING only

Unchanged from v2 §1. Goal: turn one large PDF into a bounded, ordered list of coarse sections, and tag each with its reporting basis (STANDALONE / CONSOLIDATED / NOT_APPLICABLE). Do not expect this step to isolate individual notes; it cannot.

Prefer PDF bookmarks/TOC metadata if present. If no bookmarks exist, fall back to font-based heading detection. Preserve page numbers on every chunk — required later for citation/provenance.

Token budgets apply only to this level, and only to feed the §4 embedding fallback. §3b and §3c ignore them entirely.

Correction note — effective font size: raw font_size from common PDF extractors is frequently 1.0 for every fragment (the font's internal scale); the true rendered size must be recovered by multiplying by the text-matrix vertical scale. Running headers/footers repeat at a fixed size on every page and must be excluded from heading detection. Both are real, observed failure modes.

Correction note — TOC page offset: the printed page numbers in a report's TOC do not necessarily equal the PDF page index. Provenance must record the PDF page index; if a printed page number is also cited, reconcile the offset explicitly.

Output of Step 1: an ordered list of coarse chunks, each with {text, page_range, heading_path, basis, source_confidence}.

1a. Technique — locate with OCR, confirm with vision (mixed text/scanned reports)

NOT YET IMPLEMENTED. This section is a specification for unbuilt work, not a description of current behaviour. The current pipeline classifies a report as SCANNED_IMAGE_ONLY and then silently skips it: there is no OCR and no vision pass anywhere in the codebase. Until this is built, a scanned financial-statements block yields nothing and must surface as INCONCLUSIVE, not as a clean zero.

Why it will matter: the narrative front-matter usually has a text layer while the signed financial statements are re-inserted as scanned pages — exactly the block feeding Checks 1, 3, 4 and 5. Confirmed on the VGINFOTECH FY2025-26 report: pages 1–117 had a full text layer; pages 118–156 were image-only.

1a.1 Detect the boundary, don't assume the whole document. If a contiguous page range returns empty text while other ranges extract cleanly, OCR/vision applies to that range only.

1a.2 OCR every page in the image-only range, but only to locate, not to read. ~150 DPI is enough. Use the OCR text as a cheap page-level index against the §2 categories. Never compute or cite a number from this pass: OCR corrupts dense financial tables (transposed digits, merged decimal points, dropped minus signs).

1a.3 Vision-read only the pages that matched a category. This is the authoritative source for any figure compared against a threshold.

1a.4 Provenance reflects which pass produced the number. Vision-read → HIGH (MEDIUM if the scan is degraded). OCR-only → LOW, flagged unconfirmed, and must not satisfy a check's "required fields" test. Located but never vision-read → record explicitly as "located, not confirmed" so a re-run finishes the vision pass rather than redoing the OCR locate.

2. Step 2 — Canonical target schema

The categories this pipeline extracts *from the annual report*. This is not the complete CompanyInput field list — several fields come from elsewhere, and saying so explicitly is the point of the third column. If Phase 1's rules add a new check, this table gets a new row.

Category | What it's looking for (meaning, not wording) | Keyword anchors | Source
audit_opinion | The auditor's formal opinion paragraph | masthead + confirmer, see §3a | AR
auditor_resigned_mid_tenure_last_3y | Auditor resignation during tenure | "resignation of statutory auditor", CARO clause 3(xviii) | AR
audit_fees | Statutory audit fee as reported in notes | "payment to auditors", "auditor's remuneration", "remuneration to auditors", "auditor remuneration", "statutory audit" | AR
legal_fees / legal_fees_prior_year | Legal & professional charges, current and prior column | "legal and professional", "legal fees", "legal charges" | AR
related_party_transactions (rpt_sales_plus_purchases) | Related party sales + purchases | "related party transactions", "related party disclosures", "Ind AS 24", "AS 18" | AR
contingent_liabilities | Disclosed contingent claims, guarantees, disputed demands | "contingent liabilit", "claims against the company not acknowledged", "guarantees" | AR
revenue | Revenue from operations, same statement/FY/basis as the RPT note | "revenue from operations", "total income" | AR
net_worth | Total equity attributable to owners (exclude NCI) | "total equity", "shareholders' funds", "net worth" | AR
cash_flow_operations | Net cash from operating activities, multi-year | "cash flow from operating", "net cash", "operating activities" | AR (multi-report, see §7a) 
profit_after_tax | PAT, matching the cash-flow periods | "profit for the year", "profit after tax" | AR (multi-report, see §7a)
restatement_of_past_accounts | Prior-period restatement (NOT routine Ind AS regrouping) | "restatement", "prior period errors", "correction of prior period" | AR
kmp_changes / cfo_changes_last_3y | CFO/KMP appointments and resignations | "key managerial personnel", "chief financial officer", "resign" | AR
regulatory_action | SEBI/RBI/SFIO/ED/CBI proceedings, penalties, show-cause | "SEBI", "SFIO", "Enforcement Directorate", "show cause", "penalty", "adjudication order" | AR (secretarial audit report + board's report)
unusual_affiliate_dealings | Loans/advances to promoter entities, circular flows | "unsecured loans given", "advances given", RPT note | AR
years_of_track_record_available | Listed/reporting history | "Nth Annual Report" on the cover | AR
company_type / govt_shareholding_pct | PSU vs professionally-managed vs promoter-led | shareholding pattern table, "promoter" | AR shareholding table; Screener for pledge
promoter_shareholding (pledge %) | Pledge/encumbrance %, trailing quarters | — | NOT in the AR — Screener.in / BSE Reg 31 only

Note on promoter_shareholding: pledge % and the trailing-quarter series are not in an annual report. The keyword pass will correctly return zero hits and the field resolves as INCONCLUSIVE unless the external source is pulled (Phase1-Rules-v2.md §8.4-B).

Note on regulatory_action: this is materially under-weighted in v2. The Dynamic FY25 report discloses a ₹12 lakh SEBI adjudication penalty, and it appears only in the secretarial audit report and the board's report — not in the financial statements notes. An extractor scoped to the notes block will never see it.

3. Step 3 — Note-level location by keyword anchor (PRIMARY)

For each category, search for its keyword anchors. This is the default path: fast, deterministic, fully auditable, and every hit maps to an exact page.

Mechanics: run the anchors as literal/regex searches over the text layer, confined to the basis window from §5. Prefer hits inside the audited financial statements over narrative sections. A category may have zero hits, or multiple.

Limitation to be honest about: keyword anchoring is brittle against wording variation. A report calling the auditor's report "Report of the Statutory Auditors" may not match. That is what §4 exists to catch.

3a. Locating the auditor's report specifically

The bare word "Opinion" appears throughout an annual report — accounting policies, the board's report, every cross-reference — so it is not usable as an anchor on its own. Require **two** signals within the first ~1,500 characters of a page:

- a masthead: "independent auditor'?s'? report" or "report on the audit of the (standalone|consolidated) financial statements"
- a confirmer: "to the members" or "we have audited"

Then classify in this **priority order**, which is load-bearing: ADVERSE → DISCLAIMER → QUALIFIED → CLEAN. The clean-opinion boilerplate ("give a true and fair view") appears in qualified reports too, so testing for it first would misclassify the one case Phase 1 must never miss.

3b. Step 3b — Note-unit chunking (NEW in v3)

Once the basis window is known, flatten the notes region to a single ordered stream of (page, line) and cut it into note units. Five rules, each of which failed a real report before it was added.

3b.1 Segment on note numbering, not font size. All note headers share a font size — that is precisely why structure cannot separate them (v2 §13 observed this and drew the wrong conclusion). What they do carry is a number. Match `^(\d{1,3})(\.(\d{1,3}))?\s*[:.]?\s+<Title>$` where the title starts with a capital, and key each candidate as a `(major, minor)` tuple. This covers all three observed conventions — `37 OTHER EXPENSES` → (37,0), `39.2 : Contingent Liabilities` → (39,2), `2.33 Other expenses` → (2,33) — without knowing in advance which a report uses.

3b.2 Select the longest non-decreasing run, not a greedy scan. Real note headers ascend. A greedy "accept if ≥ last" scan is not enough: one stray line such as "…page 118 sets out general and specific…" parses as (118,0), locks the gate, and rejects every genuine note after it. Measured: greedy gave 5 note units on Oswal and 6 on Minda; longest-run selection gives 53 and 45. Monotonicity is also what rejects false positives like "17.97 Years" and balance-sheet line items like "1 Non Current Assets".

3b.3 Bound notes at LINE offsets, never page ranges. Page 150 of the Dynamic report holds notes 34–37; page 152 holds notes 40, 41, 42 and 43. Page-range bounds leak across four or five notes — this alone produced a profit figure from Note 39 EPS as the contingent-liabilities value. Store `start`/`end` as indices into the flattened stream; retain the page per line for citation.

3b.4 Collapse repeated headers. Minda reprints "2.39 Related party disclosures…" as a running header on continuation pages, fragmenting one note into three. Merge equal consecutive keys.

3b.5 Bare integers are values, not page numbers. A digit-only line is furniture only in the header/footer band. Minda prints its columns as plain integers (436, not 436.00); a blanket "drop digit-only lines" filter deletes every value in the report.

Gaps in the numbering (undetected headers whose titles wrap across lines) are harmless: a note's extent runs to the *next detected* header, so an undetected header merges two notes rather than losing one.

Fallback chain: no numbering detected → fall back to §1 heading chunks. Numbering non-monotonic across the whole region (restated or merged reports) → segment per contiguous ascending run. Anchor found in no note unit → §4.

3c. Step 3c — Row and column selection inside a note (NEW in v3)

An anchor hit yields a note, not a number. Ask one question first:

**Is the anchor the note's own header, or a sub-label inside it?**

- anchor **is** the header → a `Total` row is this note's value
- anchor is a **sub-label** → `Total` belongs to the parent note; reject it and read only the specific labelled row, scanning from the sub-label forward

This single test is what separates ₹3.07 lakh from ₹7,999.81 lakh. "Payment to Auditors:" is a sub-label inside Note 37 OTHER EXPENSES; "Contingent Liabilities" *is* Note 40's header, so its total is legitimate.

3c.2 Bound the table within the note. A note is not all table. Oswal's Note 39.2 is "Contingent Liabilities **and Commitments**"; Minda's 2.37 runs into three paragraphs of prose quoting "₹ 95 million" and "₹ 671 millions". Summing the whole note gave 607.29 and 1,969.76 against true values of 50.55 and 1,052. Stop the row scan at the first footnote marker (`*  $  ^  #  †`), sub-section heading ("Commitments"), or prose paragraph.

3c.3 Do not count a figure twice. Where a group header ("Claims against the Company not acknowledged as debts") and its own first row ("a) Income-tax … 680") both match the row patterns, the same 680 is added twice. Track which value line each match consumed and skip an already-consumed line.

3c.4 Read the columns. Indian notes are typeset one value per line beneath the label, not as trailing numbers on the label line — support both, preferring the label line when it already carries enough numbers. The first numeric column is the current year and the second is the prior year; a bare dash is nil, not missing. This is where `legal_fees_prior_year` comes from, and it is the only place column order is decided. Map columns to fiscal years from the note's own period header where one exists.

3c.5 Suppress running furniture before any of this. Lines repeating near the top of more than ~35% of pages ("Solar|Domestic|Agriculture|Industrial", "True Partner!", "Oswal Pumps Limited") are page decoration and will otherwise be read as note content.

3d. Step 3d — Units (NEW in v3)

Every value carries a unit, and no report states it next to the number.

3d.1 Capture the declaration. Match a header-band declaration of the form "(All amounts are in ₹ in Millions, unless otherwise stated)" / "(Amount in Lakhs)". Observed: Dynamic = lakh, Oswal = million, Minda = million.

3d.2 Carry it forward. Reports do not repeat the declaration on every page. Minda declares it on pages 301, 303, 313 … but **not** on page 364, where the audit and legal fees are. A per-page lookup therefore finds nothing and defaults — silently wrong by 10x. Apply the most recent declaration at or before the page, exactly as the report intends it to be read.

3d.3 An undeclared unit is unknown, not lakh. If no declaration precedes a value anywhere in the region, the unit is null: cap confidence at MEDIUM and do not normalize. Never assume a default.

3d.4 Normalize before storing. Convert to one canonical unit (lakh) and record both the printed value and the resolved unit in provenance. Because Checks 3/4/5 are ratios, a uniform unit error cancels and a mixed one does not — contingent liabilities from a lakh note over a net worth from a crore balance sheet is off by 100x and looks entirely plausible.

4. Step 4 — Embedding/LLM classification (FALLBACK)

Run only for categories §3 could not place: zero keyword hits, or hits ambiguous across categories. Do not run it as the default path.

Primary fallback — embedding similarity: embed the candidate chunk and each category description; assign if similarity clears the threshold. Secondary — targeted LLM classification, one chunk at a time, never the whole document.

A chunk may match zero categories; most of an annual report is irrelevant to Phase 1. Discard non-matches, do not force a classification. A chunk may match more than one; keep it linked to all.

Output of Steps 3–4: category → [chunk_id, page, note_key, confidence, method], where method is keyword | embedding | llm and is carried into provenance.

5. Step 5 — Basis tagging (consolidated vs standalone)

Unchanged from v2 §5, and still the one place the structural split is genuinely load-bearing. Annual reports carry both statement sets back to back and every note repeats, so an extractor taking the first anchor hit silently reads the wrong basis. The boundary is a layout fact — detect it structurally, from the "Report on the audit of the (standalone|consolidated) financial statements" / "Notes to the (standalone|consolidated) financial statements" headings. A page naming both is a contents page and marks the start of neither.

Tag every chunk CONSOLIDATED | STANDALONE | NOT_APPLICABLE. Prefer consolidated per Phase1-Rules-v2.md §8.1, keeping standalone as corroboration.

Keywords cannot do this: "contingent liabilities" reads identically in both sets.

6. Step 6 — Resolve multiple matches per category

Prefer the audited notes section over narrative sections (MD&A, Chairman's letter). Prefer consolidated over standalone for ratios. If two notes-section candidates conflict, prefer the one nearer the final signed statements and flag it in provenance. If only a narrative mention exists, use it at confidence LOW.

7. Step 7 — Populate CompanyInput with provenance

For each resolved category: extract the value per §3c, normalize per §3d, populate the field, and populate FieldProvenance alongside it — source, period, basis (§5), page (PDF index), note_key (§3b), **row label actually read**, **unit as printed and as normalized**, **whether the anchor was the note header or a sub-label** (§3c), confidence, method (§3/§4), extracted_at.

The three new provenance items are not decoration. They are what makes the ₹7,999.81 vs ₹3.07 class of error visible in review rather than invisible.

For each unresolved category: leave the field null, write no provenance entry, and let run_phase1() surface it as INCONCLUSIVE with the category named.

7a. Multi-report series (cfo_last_5y, pat_last_5y)

These need several annual reports, and the upload path is explicitly multi-report. Run Steps 1–3 per document, then stitch by fiscal year. Where FY25's comparative column and FY24's current column disagree, prefer the later report's restated figure and flag the difference — a disagreement here is itself a signal for restatement_of_past_accounts.

8. Step 8 — Validate before handing off to the rule engine

Basis consistency: for any check spanning fields (RPT ÷ Revenue), confirm both share a basis. If not, do not compute the ratio.

Period consistency: confirm fields feeding one check cover the same fiscal year.

**Unit consistency (new):** confirm both operands of a ratio resolved to the same canonical unit and that neither has a null unit. A null unit fails the check into INCONCLUSIVE; it does not default.

No silent zero-filling: confirm every null is an intentional "not found", not a default left over from a failed step. A bare dash correctly read as nil is a real zero and must be distinguishable from a missing value.

9. Step 9 — Cache the classification map, not raw content

Persist {category → chunk_id, page, note_key, basis, unit, confidence, method} per report; key it on the document content hash. On a repeat query reuse the map. On a new report — next FY or a different company — always re-run Steps 1–4 from scratch. Nothing about a prior report's structure carries over.

10. Handling format outliers (explicit, not special-cased)

Situation | How it's handled
Integer note numbering ("37 OTHER EXPENSES") | §3b.1 — (37,0)
Decimal note numbering ("2.33 Other expenses") | §3b.1 — (2,33)
Sectioned numbering with colon ("39.2 : Contingent Liabilities") | §3b.1 — (39,2)
Number and title separated by a tab | §3b.1 — treat any whitespace run as the separator
Note header reprinted on continuation pages | §3b.4 — collapse equal consecutive keys
Several notes on one page | §3b.3 — line-level bounds, never page ranges
Values printed as bare integers, no decimals | §3b.5 — digit-only lines are furniture only in the header/footer band
Unit declared on some pages only | §3d.2 — carry the last declaration forward
Unit never declared | §3d.3 — unit is null, confidence capped, no normalization
Target is a sub-label inside a larger note | §3c.1 — reject the parent's Total
Note mixes a table with prose ("…and Commitments") | §3c.2 — stop at footnote marker, sub-heading, or prose
Party-wise RPT table with no per-group total | Not yet solved — return null, never a substitute figure (see §11)
Whole report scanned/image-only | §1a, NOT YET IMPLEMENTED — INCONCLUSIVE, not zero
Non-standard section naming ("Report of the Statutory Auditors") | §4 fallback
No formal RPT note (common for smaller companies) | No match → null → INCONCLUSIVE, not an error
Report contains only standalone financials | data_basis reflects what is available
Multi-volume / split PDF | Run Step 1 per volume, merge before Step 3
No bookmarks in the PDF | §1 font-based detection with effective-size correction

11. Validation before trusting this on a new company

Measured results, three FY2025-26 reports, ground truth read from the documents:

Field | Dynamic (164pp, lakh) | Oswal Pumps (258pp, million) | Minda Corp (393pp, million)
audit_fees | 3.07 ✓ | 4.74 ✓ | 21 ✓
legal_fees | 21.46 ✓ | 43.52 ✓ | 436 ✓
contingent_liabilities | 0.0 ✓ | 50.55 ✓ | 1,052 ✓
rpt_sales_plus_purchases | 256.56 ✓ | null (declined) | null (declined)
unit resolved | lakh ✓ | million ✓ | million ✓
note units segmented | 61 | 53 | 45

10/10 on fields with a known truth, against 6/10 for the v2-era extractor. The three corrected errors were audit_fees 7,999.81 → 3.07 (Dynamic), contingent_liabilities 555.98 → 50.55 (Oswal — the wrong number off the wrong page entirely), and rpt 2,351.82 → 256.56 (Dynamic; 2,351.82 is share capital).

Known scope limit, stated plainly: the RPT extractor reads the "group label → Total" shape (Dynamic) and **declines** on party-wise tables that list one row per counterparty with no per-group total (Oswal, Minda). It returns null where the v2-era extractor returned 10,507.98 and 61,853 — the latter being consolidated revenue. Declining is the correct failure mode under the golden rule, but this is 1 of 3 reports and is the first thing v4 should fix.

Before relying on this pipeline for an unfamiliar report, sanity-check it against reports that differ on the axes that actually vary: a large-cap and a small-cap; a PSU and a professionally-managed (zero-promoter) company; and — the single case that must never be missed — a report carrying a qualified or adverse audit opinion.

Additionally, record for each: how many categories were found by keyword (§3) vs by fallback (§4), and how many notes the numbering scheme segmented. **If the fallback places more than 30% of categories, or if segmentation yields fewer than ~15 note units on a report with a full notes block, the anchors or the numbering rules are overfit and need extending.** Both are alarms that must be able to fire; v2's "a small minority" could not.

12. Definition of done for this chunking layer

- Report split into page-tagged structural chunks, each tagged with reporting basis (§1, §5)
- Notes block segmented into note units by numbering, line-bounded, headers de-duplicated (§3b)
- Every relevant category located — by keyword anchor (§3) where possible, by fallback (§4) where not — with no forced classification of irrelevant content
- For every located category, the **row actually read** decided by the header-vs-sub-label test, within a bounded table, with no double-counted figure (§3c)
- Current and prior columns distinguished; a bare dash read as nil, not as missing (§3c.4)
- A unit resolved for every value, carried forward from the last declaration, null where undeclared (§3d)
- Multiple-match categories resolved by the stated preference order (§6)
- CompanyInput populated with full provenance including row label, unit, and anchor type (§7)
- Basis, period and unit consistency validated before handoff to run_phase1() (§8)
- Classification map cached, keyed on content hash (§9)
- No field silently defaulted — every null represents a genuine "not found", and every unit-less value is refused rather than assumed

Summary of the v2 → v3 change

v2 assigned each method the job it does well and stopped at the note heading. v3 keeps that allocation unchanged and specifies what happens inside the note: segment by numbering rather than font size or token budget, bound notes at line offsets, decide the row by whether the anchor is the note's header or a sub-label inside it, distinguish the current and prior columns, and resolve the reporting unit by carrying the last declaration forward. Measured 6/10 → 10/10 across three reports of different size, numbering convention and reporting unit. No threshold, schema field, or pass/fail rule changed.
