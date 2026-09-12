"""
Tier 1 text extraction engine using PyMuPDF (fitz).
Maps strictly to implementpdf.md Stage 2 and Phase1-WebApp-Implementation-Plan.md §5.2.
Extracts narrative fields (audit_opinion, cfo_changes_last_3y, auditor_resigned_mid_tenure) with page citations.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
import pymupdf as fitz

from backend.app.acquisition.adapters.pdf.anchors import (
    SECTION_PATTERNS,
    locate_basis_page_range,
    matches_anchor,
    normalize_quotes,
)
from backend.app.acquisition.types import ExtractedField
from backend.app.models.enums import (
    AuditOpinion,
    Confidence,
    ExtractionMethod,
    RegulatoryNature,
    ReportingBasis,
    RetrievalTier,
)
from backend.app.models.schemas import RegulatoryActionInput


# The bare word "Opinion" appears in board reports and accounting policies all
# through an annual report, so the report's opening page is identified by its
# masthead plus the addressee line that only the statutory report carries.
_AUDITOR_REPORT_HEADINGS = [
    r"independent auditor'?s'? report",
    r"report on the audit of the (?:standalone|consolidated) financial statements",
]
_AUDITOR_REPORT_CONFIRMERS = ["to the members", "we have audited"]


def _page_text(page: fitz.Page) -> str:
    raw = page.get_text("text")
    return str(raw)


def locate_auditor_report_pages(
    doc: fitz.Document,
    basis: Optional[ReportingBasis] = None,
) -> List[int]:
    """
    Finds page indices (0-based) containing the Independent Auditor's Report.
    When `basis` is given and the document separates its standalone and
    consolidated sections, only that basis's report is returned.
    """
    page_texts = [_page_text(doc[i]) for i in range(len(doc))]
    start, end = 0, len(page_texts)
    if basis is not None:
        page_range = locate_basis_page_range(page_texts, basis.value)
        if page_range:
            start, end = page_range

    first_page: Optional[int] = None
    for page_idx in range(start, end):
        text = re.sub(r"\s+", " ", normalize_quotes(page_texts[page_idx]).lower())
        head = text[:1500]
        if not any(re.search(pat, head) for pat in _AUDITOR_REPORT_HEADINGS):
            continue
        if not any(marker in head for marker in _AUDITOR_REPORT_CONFIRMERS):
            # A contents entry or a cross-reference, not the report itself.
            continue
        first_page = page_idx
        break

    if first_page is None:
        return []

    # Auditor reports typically span 3-10 pages.
    candidate_pages = [first_page]
    for next_idx in range(first_page + 1, min(first_page + 12, end)):
        next_text = normalize_quotes(page_texts[next_idx]).lower()
        if (
            "independent auditor" in next_text
            or "basis for opinion" in next_text
            or "key audit matters" in next_text
        ):
            candidate_pages.append(next_idx)
    return candidate_pages


def extract_audit_opinion_from_doc(
    doc: fitz.Document,
    source_filename: str,
    period: str,
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> Optional[ExtractedField]:
    """
    Extracts and classifies the statutory audit opinion into CLEAN, QUALIFIED, ADVERSE, or DISCLAIMER.
    Returns ExtractedField with exact page citation and raw text snippet.
    """
    pages = locate_auditor_report_pages(doc, basis=basis)
    if not pages:
        # Fallback search across all pages, ignoring the basis split.
        pages = locate_auditor_report_pages(doc)
    if not pages:
        for page_idx in range(len(doc)):
            text = normalize_quotes(_page_text(doc[page_idx])).lower()
            if "independent auditor's report" in text:
                pages.append(page_idx)

    for page_idx in pages:
        text = _page_text(doc[page_idx])
        # Opinion wording wraps across lines in the PDF, so match against text
        # with its line breaks collapsed.
        lower = re.sub(r"\s+", " ", normalize_quotes(text).lower())

        # Check for Adverse Opinion
        if "adverse opinion" in lower:
            snippet_match = re.search(r"(?:adverse opinion.*?\.{1,2})", text, re.IGNORECASE | re.DOTALL)
            snippet = snippet_match.group(0)[:300] if snippet_match else text[:300]
            return ExtractedField(
                field_name="audit_opinion",
                value=AuditOpinion.ADVERSE,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"Adverse opinion on page {page_idx + 1}: {snippet.strip()}",
                document_id=document_id,
            )

        # Check for Disclaimer of Opinion
        if "disclaimer of opinion" in lower:
            snippet_match = re.search(r"(?:disclaimer of opinion.*?\.{1,2})", text, re.IGNORECASE | re.DOTALL)
            snippet = snippet_match.group(0)[:300] if snippet_match else text[:300]
            return ExtractedField(
                field_name="audit_opinion",
                value=AuditOpinion.DISCLAIMER,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"Disclaimer of opinion on page {page_idx + 1}: {snippet.strip()}",
                document_id=document_id,
            )

        # Check for Qualified Opinion
        if "qualified opinion" in lower or "basis for qualified opinion" in lower:
            snippet_match = re.search(r"(?:qualified opinion.*?\.{1,2})", text, re.IGNORECASE | re.DOTALL)
            snippet = snippet_match.group(0)[:300] if snippet_match else text[:300]
            return ExtractedField(
                field_name="audit_opinion",
                value=AuditOpinion.QUALIFIED,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"Qualified opinion on page {page_idx + 1}: {snippet.strip()}",
                document_id=document_id,
            )

        # Check for Clean / Unmodified Opinion
        clean_indicators = [
            "give a true and fair view",
            "gives a true and fair view",
            "unmodified opinion",
            "unmodified audit opinion",
            "opinion on the financial statements",
        ]
        for ind in clean_indicators:
            if ind in lower:
                # Ensure it's inside an opinion context
                m = re.search(r"(?:(?:in our opinion|our opinion).*?|)(?:true and fair view|unmodified).*?\.", text, re.IGNORECASE | re.DOTALL)
                snippet = m.group(0)[:300] if m else text[:300]
                return ExtractedField(
                    field_name="audit_opinion",
                    value=AuditOpinion.CLEAN,
                    confidence=Confidence.HIGH,
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                    source=source_filename,
                    period=period,
                    basis=basis,
                    page=page_idx + 1,
                    raw_snippet=f"Clean opinion on page {page_idx + 1}: {snippet.strip()}",
                    document_id=document_id,
                )

    return None


# ---------------------------------------------------------------------------
# Auditor resignation (Section A Q1 / chunkrule-v3.md §2 "auditor_resigned_
# mid_tenure_last_3y") — CARO 2020 clause 3(xviii) requires every statutory
# auditor's report to state explicitly whether a mid-tenure resignation
# occurred during the year. That single sentence is the reliable anchor;
# there is no numeric table involved.
#
# Limitation, stated plainly rather than hidden: this reads only the current
# document's own-year disclosure, not a stitched 3-year history the way
# cfo_last_5y is stitched across multiple uploaded Annual Reports
# (chunkrule-v3.md §7a). A single AR only speaks to its own fiscal year;
# raw_snippet says so explicitly so a reader can see the window actually
# covered, matching the disclosure discipline Phase1-Rules-v2.md §1a requires
# elsewhere in this pipeline.
# ---------------------------------------------------------------------------

_NO_AUDITOR_RESIGNATION = re.compile(
    r"no\s+resignation\s+of\s+the\s+statutory\s+auditors?\s+(?:during|in)\s+the\s+year",
    re.IGNORECASE,
)
_YES_AUDITOR_RESIGNATION = re.compile(
    r"(?:the\s+)?statutory\s+auditors?\s+(?:has|have)\s+resigned",
    re.IGNORECASE,
)


def extract_auditor_resignation_from_doc(
    doc: fitz.Document,
    source_filename: str,
    period: str,
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> Optional[ExtractedField]:
    """
    Reads CARO clause 3(xviii)'s explicit resignation statement. Returns
    None (not a guessed False) when neither the clean nor the disqualifying
    phrasing is found — a clause that isn't there at all is missing data,
    not evidence of "no resignation" (golden rule, chunkrule-v3.md line 7).
    """
    for page_idx in range(len(doc)):
        text = _page_text(doc[page_idx])
        norm = re.sub(r"\s+", " ", normalize_quotes(text))
        m = _NO_AUDITOR_RESIGNATION.search(norm)
        if m:
            snippet = norm[max(0, m.start() - 40): m.end() + 10]
            return ExtractedField(
                field_name="auditor_resigned_mid_tenure_last_3y",
                value=False,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"CARO 3(xviii), current FY only: {snippet.strip()}",
                document_id=document_id,
            )

    for page_idx in range(len(doc)):
        text = _page_text(doc[page_idx])
        norm = re.sub(r"\s+", " ", normalize_quotes(text))
        m = _YES_AUDITOR_RESIGNATION.search(norm)
        if m:
            snippet = norm[max(0, m.start() - 40): m.end() + 120]
            return ExtractedField(
                field_name="auditor_resigned_mid_tenure_last_3y",
                value=True,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=f"CARO 3(xviii), current FY only: {snippet.strip()}",
                document_id=document_id,
            )

    return None


# ---------------------------------------------------------------------------
# CFO changes (Section A Q6 / chunkrule-v3.md §2 "cfo_changes_last_3y") —
# read off the Board's Report "Key Managerial Personnel" changes disclosure.
#
# A genuine change-log page enumerates appointments/resignations/cessations
# for the year; a page that merely lists the current KMP roster (no change
# verbs) says nothing about whether a change occurred and must not be read
# as "zero changes". Only a page that demonstrably IS a change log, and
# happens not to mention the CFO role, supports a trustworthy 0.
#
# Same single-fiscal-year limitation as auditor resignation above — the
# count reflects only this document's own year, not a stitched 3-year
# window, and is tagged MEDIUM (not HIGH) confidence so the assembler's
# confidence floor (Rules §8.4-D-style discipline) routes it to analyst
# review rather than being silently accepted as a full 3-year answer.
# ---------------------------------------------------------------------------

_KMP_CHANGES_HEADING = re.compile(
    r"changes?\s+in\s+(?:the\s+)?key\s+managerial\s+personnel", re.IGNORECASE
)
_KMP_CHANGE_VERBS = re.compile(
    r"\b(?:appointed|appointment|resign(?:ed|ation)?|ceas(?:ed|ation)|"
    r"relinquish(?:ed)?|stepped\s+down|re-?appointed)\b",
    re.IGNORECASE,
)
# A genuine change entry names *when* the change took effect. Requiring this
# near a change verb is what separates an actual change-log line from an
# incidental "appointed"/"resigned" mention in unrelated narrative (board
# overview text, subsidiary incorporations, etc.) that happens to share a
# page with a "Key Managerial Personnel" heading.
_EFFECTIVE_DATE_HINT = re.compile(
    r"with effect from|w\.e\.f\.?|effective\s+(?:from|date)|\b\d{1,2}\s+"
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+20\d{2}\b",
    re.IGNORECASE,
)
_CFO_ROLE = re.compile(r"chief financial officer", re.IGNORECASE)
_CFO_CHANGE_EVENT = re.compile(
    r"chief financial officer[^.]{0,80}?(?:appointed|resign|ceas|relinquish|stepped down)"
    r"|(?:appointed|resign|ceas|relinquish|stepped down)[^.]{0,80}?chief financial officer",
    re.IGNORECASE,
)


_KMP_WINDOW_CHARS = 1200  # a KMP changes note is a short paragraph/table, not a whole page


def extract_cfo_changes_from_doc(
    doc: fitz.Document,
    source_filename: str,
    period: str,
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> Optional[ExtractedField]:
    for page_idx in range(len(doc)):
        text = _page_text(doc[page_idx])
        norm = re.sub(r"\s+", " ", normalize_quotes(text))
        # Require the specific "Changes in Key Managerial Personnel" heading,
        # not a bare "Key Managerial Personnel" mention — the latter also
        # titles the static roster / board-overview sections, which say
        # nothing about whether a change occurred this year.
        heading = _KMP_CHANGES_HEADING.search(norm)
        if not heading:
            continue

        # Bound the search to a window after the heading — an unrelated
        # change-verb or CFO mention elsewhere on a dense page must not be
        # attributed to this note. A real KMP-changes note is a short
        # paragraph/table.
        window = norm[heading.start(): heading.start() + _KMP_WINDOW_CHARS]
        if not _KMP_CHANGE_VERBS.search(window) or not _EFFECTIVE_DATE_HINT.search(window):
            # No change verb, or a change verb with no effective date nearby
            # — not a trustworthy itemized change entry. Move on rather than
            # risk reading a narrative aside as a change log.
            continue

        cfo_events = _CFO_CHANGE_EVENT.findall(window)
        if cfo_events:
            return ExtractedField(
                field_name="cfo_changes_last_3y",
                value=len(cfo_events),
                confidence=Confidence.MEDIUM,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=(
                    f"KMP change log, current FY only, {len(cfo_events)} CFO change "
                    f"event(s) matched on p.{page_idx + 1}: {window[:200]}"
                ),
                document_id=document_id,
            )
        if not _CFO_ROLE.search(window):
            return ExtractedField(
                field_name="cfo_changes_last_3y",
                value=0,
                confidence=Confidence.MEDIUM,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=(
                    f"KMP change log on p.{page_idx + 1} enumerates changes for the year "
                    f"with no Chief Financial Officer mention (current FY only): {window[:200]}"
                ),
                document_id=document_id,
            )

    return None


# ---------------------------------------------------------------------------
# Restatement of past accounts (Section A Q6 / Rules §8.4-D) — targeted
# search for "restatement" / "prior period error" / "Ind AS 8" / "restated",
# plus an Auditor's Report Emphasis of Matter check, exactly as §8.4-D
# specifies. Disambiguates ESG/BRSR-only mentions (a revised water-
# withdrawal or emissions figure is not a financial restatement) per the
# same section's explicit carve-out.
# ---------------------------------------------------------------------------

_RESTATEMENT_KEYWORDS = re.compile(
    r"\brestatement\b|\bprior period error(?:s)?\b|\bind\s*as\s*8\b|\brestated\b",
    re.IGNORECASE,
)
_ESG_CONTEXT = re.compile(
    r"\bbrsr\b|sustainability report|\bemission|water\s+withdrawal|\bghg\b|"
    r"scope\s*[123]\b|energy\s+consum|environmental,?\s+social",
    re.IGNORECASE,
)
# "Restatement"/"restated" is also standard Ind AS 21 vocabulary for
# retranslating foreign-currency monetary balances at each period end — a
# routine accounting-policy mechanic with nothing to do with correcting a
# prior misstatement. Bare "restat*" hits in this context are excluded, the
# same way an ESG-context hit is; "prior period error" / "Ind AS 8" hits are
# unaffected since they don't collide with this accounting-policy meaning.
_FOREX_RETRANSLATION_CONTEXT = re.compile(
    r"exchange rate|foreign currency|monetary (?:item|asset|liabilit)|retranslat|"
    r"translat(?:ed|ion) at",
    re.IGNORECASE,
)
_EMPHASIS_OF_MATTER = re.compile(r"emphasis of matter", re.IGNORECASE)
# Schedule III's mandated Statement of Changes in Equity (SOCIE) carries a
# "prior period errors" row/column in both its share-capital and other-
# equity reconciliation tables, in every Indian annual report, filled or
# nil — the exact wording varies ("changes... due to prior period errors",
# "changes in accounting policy / prior period errors"), so this is a
# page-level structural fact, not a phrase to enumerate: any restatement-
# keyword hit on a page that IS a SOCIE table is that table's own mandated
# row/column label, not a disclosure that a restatement occurred. A genuine
# restatement is disclosed in Notes-to-Accounts prose, a different page,
# and is unaffected by this exclusion.
_SOCIE_PAGE_HEADING = re.compile(
    r"statement of changes in equity", re.IGNORECASE
)
# The SOCIE table commonly spans several pages (share capital, then a wide
# "Other Equity" reconciliation) and does not repeat its title on every
# continuation page — only a running header/footer does (chunkrule-v3.md
# §3b.4's "reprinted header" problem, mirrored here for a whole statement
# rather than a single note). "Notes forming part of..." is the reliable
# start of the next section in Indian annual reports and closes the window.
_NOTES_SECTION_START = re.compile(
    r"notes forming part of", re.IGNORECASE
)


def extract_restatement_from_doc(
    doc: fitz.Document,
    source_filename: str,
    period: str,
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> List[ExtractedField]:
    """
    Returns 0-3 fields: restatement_of_past_accounts (always, if resolvable),
    restatement_search_retrieval_tier, restatement_esg_only_excluded (only
    when an ESG-only mention was found and excluded).
    """
    eom_pages = set()
    # (page_idx, local_context, page_is_esg, page_is_socie) — both
    # disambiguations are section-level facts, not tight local-window ones:
    # a BRSR page states its restatement in prose that doesn't always carry
    # the word "BRSR" within a few hundred characters of the sentence, and a
    # SOCIE table's "prior period errors" row/column label is boilerplate
    # regardless of exact local wording. Both need a whole-page context
    # check, not just the local window.
    keyword_hits: List[Tuple[int, str, bool, bool]] = []
    esg_only_hit = False
    in_socie = False  # carried forward across the SOCIE table's continuation pages

    for page_idx in range(len(doc)):
        text = _page_text(doc[page_idx])
        norm = re.sub(r"\s+", " ", normalize_quotes(text))
        if _EMPHASIS_OF_MATTER.search(norm):
            eom_pages.add(page_idx)
        page_is_esg = bool(_ESG_CONTEXT.search(norm))
        if _NOTES_SECTION_START.search(norm):
            in_socie = False
        if _SOCIE_PAGE_HEADING.search(norm):
            in_socie = True
        page_is_socie = in_socie
        for m in _RESTATEMENT_KEYWORDS.finditer(norm):
            start, end = max(0, m.start() - 150), min(len(norm), m.end() + 150)
            keyword_hits.append((page_idx, norm[start:end], page_is_esg, page_is_socie))

    # 1. Auditor's Emphasis of Matter mentioning restatement -> True, PRIMARY.
    for page_idx in sorted(eom_pages):
        text = _page_text(doc[page_idx])
        norm = re.sub(r"\s+", " ", normalize_quotes(text))
        m = _EMPHASIS_OF_MATTER.search(norm)
        if not m:
            continue
        window = norm[m.start(): m.end() + 400]
        if _RESTATEMENT_KEYWORDS.search(window):
            snippet = window[:300]
            return [
                ExtractedField(
                    field_name="restatement_of_past_accounts",
                    value=True,
                    confidence=Confidence.HIGH,
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                    source=source_filename,
                    period=period,
                    basis=basis,
                    page=page_idx + 1,
                    raw_snippet=f"Emphasis of Matter references restatement: {snippet}",
                    document_id=document_id,
                ),
                ExtractedField(
                    field_name="restatement_search_retrieval_tier",
                    value=RetrievalTier.PRIMARY,
                    confidence=Confidence.HIGH,
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                    source=source_filename,
                    period=period,
                    basis=basis,
                    page=page_idx + 1,
                    raw_snippet="Sourced per Rules §8.4-D: targeted search + Emphasis of Matter review",
                    document_id=document_id,
                ),
            ]

    if not keyword_hits:
        return [
            ExtractedField(
                field_name="restatement_of_past_accounts",
                value=False,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=None,
                raw_snippet="No restatement/prior-period-error/Ind AS 8 mention found anywhere in document; no Emphasis of Matter paragraph found",
                document_id=document_id,
            ),
            ExtractedField(
                field_name="restatement_search_retrieval_tier",
                value=RetrievalTier.PRIMARY,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=None,
                raw_snippet="Sourced per Rules §8.4-D: targeted search + Emphasis of Matter review, both exhaustive over this document",
                document_id=document_id,
            ),
        ]

    # 2. Every hit is either an ESG/BRSR mention or a nil-valued Schedule III
    #    "changes due to prior period errors" column header -> False, but
    #    disclose which disambiguation fired.
    genuine_hit_page = None
    genuine_snippet = None
    for page_idx, ctx, page_is_esg, page_is_socie in keyword_hits:
        if page_is_esg or _ESG_CONTEXT.search(ctx):
            esg_only_hit = True
            continue
        if page_is_socie:
            # This page IS a Statement of Changes in Equity — its "prior
            # period errors" row/column is a mandated Schedule III label,
            # not a disclosed event.
            continue
        if "prior period error" not in ctx.lower() and "ind as 8" not in ctx.lower() and _FOREX_RETRANSLATION_CONTEXT.search(ctx):
            # A bare "restatement"/"restated" hit in a foreign-currency
            # retranslation policy note — Ind AS 21 vocabulary, not a
            # financial restatement.
            continue
        genuine_hit_page, genuine_snippet = page_idx, ctx
        break

    if genuine_hit_page is not None:
        return [
            ExtractedField(
                field_name="restatement_of_past_accounts",
                value=True,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=genuine_hit_page + 1,
                raw_snippet=f"Restatement disclosure found: {genuine_snippet}",
                document_id=document_id,
            ),
            ExtractedField(
                field_name="restatement_search_retrieval_tier",
                value=RetrievalTier.PRIMARY,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=genuine_hit_page + 1,
                raw_snippet="Sourced per Rules §8.4-D: targeted search + Emphasis of Matter review",
                document_id=document_id,
            ),
        ]

    fields = [
        ExtractedField(
            field_name="restatement_of_past_accounts",
            value=False,
            confidence=Confidence.HIGH,
            extraction_method=ExtractionMethod.NATIVE_TEXT,
            source=source_filename,
            period=period,
            basis=basis,
            page=keyword_hits[0][0] + 1,
            raw_snippet=(
                "Restatement-shaped mentions found but all were "
                + ("ESG/BRSR data restatements" if esg_only_hit else "nil-valued Schedule III boilerplate")
                + ", confirmed unrelated to the financial statements"
            ),
            document_id=document_id,
        ),
        ExtractedField(
            field_name="restatement_search_retrieval_tier",
            value=RetrievalTier.PRIMARY,
            confidence=Confidence.HIGH,
            extraction_method=ExtractionMethod.NATIVE_TEXT,
            source=source_filename,
            period=period,
            basis=basis,
            page=None,
            raw_snippet="Sourced per Rules §8.4-D: targeted search + Emphasis of Matter review",
            document_id=document_id,
        ),
    ]
    if esg_only_hit:
        fields.append(
            ExtractedField(
                field_name="restatement_esg_only_excluded",
                value=True,
                confidence=Confidence.HIGH,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=None,
                raw_snippet="An ESG/BRSR-context restatement mention was found and confirmed unrelated to the financial statements (Rules §8.4-D)",
                document_id=document_id,
            )
        )
    return fields


# ---------------------------------------------------------------------------
# Regulatory action (Section A Q1 / Rules §8.4-A) — the primary source is a
# direct SEBI enforcement-archive query, which this PDF-only pipeline cannot
# reach; no such adapter exists yet (see registry). This is therefore always
# a FALLBACK-tier reading, scanning the AR's own Board's Report / Secretarial
# Audit annexure for an explicit clean disclosure or a positive finding — the
# same fallback path Rules §8.4-A itself describes when the SEBI portal can't
# be reached, so it is tagged and downstream-disclosed exactly the same way.
# ---------------------------------------------------------------------------

_REGULATOR_NAMES = r"(?:SEBI|RBI|SFIO|ED|CBI|EOW|Enforcement Directorate|Serious Fraud Investigation Office)"
_NO_REGULATORY_ACTION = re.compile(
    r"no\s+fraud[^.]{0,120}?(?:noticed|reported)"
    r"|not\s+been\s+subject(?:ed)?\s+to\s+any[^.]{0,60}?(?:penalty|action|proceeding)"
    r"|no\s+(?:show[\s-]cause|penalty|adjudication)[^.]{0,80}?" + _REGULATOR_NAMES,
    re.IGNORECASE,
)
_YES_REGULATORY_ACTION = re.compile(
    _REGULATOR_NAMES + r"[^.]{0,150}?(?:penalty|debarr|fraud|show[\s-]cause|adjudication order|siphon|manipulat)",
    re.IGNORECASE,
)


def extract_regulatory_action_from_doc(
    doc: fitz.Document,
    source_filename: str,
    period: str,
    basis: ReportingBasis,
    document_id: Optional[str] = None,
) -> Optional[ExtractedField]:
    for page_idx in range(len(doc)):
        text = _page_text(doc[page_idx])
        norm = re.sub(r"\s+", " ", normalize_quotes(text))
        m = _NO_REGULATORY_ACTION.search(norm)
        if m:
            snippet = norm[max(0, m.start() - 20): m.end() + 40]
            return ExtractedField(
                field_name="regulatory_action",
                value=RegulatoryActionInput(
                    active_or_past_5y=False,
                    nature=RegulatoryNature.NONE,
                    retrieval_tier=RetrievalTier.FALLBACK,
                ),
                confidence=Confidence.MEDIUM,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=(
                    f"AR-sourced fallback (Rules §8.4-A — SEBI registry not queried): {snippet.strip()}"
                ),
                document_id=document_id,
            )

    for page_idx in range(len(doc)):
        text = _page_text(doc[page_idx])
        norm = re.sub(r"\s+", " ", normalize_quotes(text))
        m = _YES_REGULATORY_ACTION.search(norm)
        if m:
            snippet = norm[max(0, m.start() - 20): m.end() + 100]
            return ExtractedField(
                field_name="regulatory_action",
                value=RegulatoryActionInput(
                    active_or_past_5y=True,
                    nature=None,
                    retrieval_tier=RetrievalTier.FALLBACK,
                ),
                # LOW, not MEDIUM: an unclassified positive hit must never
                # silently clear the assembler's confidence floor and enter
                # the automated verdict — nature=None wouldn't fail Check 1
                # on its own, so a human must classify this before it's used.
                confidence=Confidence.LOW,
                extraction_method=ExtractionMethod.NATIVE_TEXT,
                source=source_filename,
                period=period,
                basis=basis,
                page=page_idx + 1,
                raw_snippet=(
                    f"AR-sourced fallback (Rules §8.4-A — SEBI registry not queried), nature not "
                    f"machine-classified, flag for analyst review: {snippet.strip()}"
                ),
                document_id=document_id,
            )

    return None
