"""
Tests for the Tier 1 narrative extractors added for auditor_resigned_mid_
tenure_last_3y, cfo_changes_last_3y, restatement_of_past_accounts, and
regulatory_action, plus the AnnualReportAdapter's "not found" reporting.
"""

import pymupdf as fitz

from backend.app.acquisition.adapters.pdf.text_tier import (
    extract_auditor_resignation_from_doc,
    extract_cfo_changes_from_doc,
    extract_regulatory_action_from_doc,
    extract_restatement_from_doc,
)
from backend.app.models.enums import Confidence, RegulatoryNature, ReportingBasis, RetrievalTier


def _doc(*page_texts: str) -> fitz.Document:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 550, 750), text)
    return doc


# --- Auditor resignation -----------------------------------------------------

def test_auditor_resignation_no_resignation_clause():
    doc = _doc(
        "Report on Other Legal and Regulatory Requirements\n"
        "(xviii) There has been no resignation of the statutory auditors during the year. "
        "Accordingly, clause 3(xviii) of the Order is not applicable."
    )
    f = extract_auditor_resignation_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is not None
    assert f.value is False
    assert f.confidence == Confidence.HIGH
    assert "current FY only" in f.raw_snippet


def test_auditor_resignation_positive_disclosure():
    doc = _doc(
        "During the year, the statutory auditors have resigned citing personal reasons "
        "and a new firm was appointed by the Board."
    )
    f = extract_auditor_resignation_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is not None
    assert f.value is True


def test_auditor_resignation_no_clause_found_returns_none():
    doc = _doc("This page has no CARO clause about auditor resignation at all.")
    f = extract_auditor_resignation_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is None


# --- CFO changes -------------------------------------------------------------

def test_cfo_changes_roster_only_is_not_a_change_log():
    doc = _doc(
        "Key Managerial Personnel\n"
        "The following are the Key Managerial Personnel of the Company: "
        "Mr. A, Managing Director; Ms. B, Chief Financial Officer; Mr. C, Company Secretary."
    )
    f = extract_cfo_changes_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is None  # no change verbs -> a roster, not a log; must not read as 0


def test_cfo_changes_log_with_no_cfo_mention_is_zero():
    doc = _doc(
        "Changes in Key Managerial Personnel\n"
        "During the year, Mr. D was appointed as Company Secretary with effect from "
        "1 June 2025, following the resignation of Mr. E from the said position."
    )
    f = extract_cfo_changes_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is not None
    assert f.value == 0
    assert f.confidence == Confidence.MEDIUM


def test_cfo_changes_log_with_cfo_event():
    doc = _doc(
        "Changes in Key Managerial Personnel\n"
        "Mr. F, Chief Financial Officer, resigned effective 31 March 2026 and "
        "Ms. G was appointed as Chief Financial Officer with effect from 1 April 2026."
    )
    f = extract_cfo_changes_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is not None
    assert f.value >= 1
    assert f.confidence == Confidence.MEDIUM


def test_cfo_changes_unrelated_page_mention_does_not_leak_in():
    # Regression: TCS FY26 AR page 39 — a "Key Managerial Personnel" board-
    # overview mention shares a page with unrelated "appointed"/"incorporated"
    # language about subsidiary formations. Must not be read as a change log.
    doc = _doc(
        "Key Managerial Personnel\n"
        "The Board of Directors comprises distinguished professionals of proven "
        "integrity and competence, who provide strategic direction, guidance and "
        "leadership to the Company.\n"
        "Tata Consultancy Services Netherlands B.V., a wholly owned subsidiary, "
        "incorporated a new entity in the Kingdom of Saudi Arabia as a wholly "
        "owned subsidiary, and the Board appointed a local representative."
    )
    f = extract_cfo_changes_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is None  # no "Changes in..." heading and no effective-date pattern


# --- Restatement --------------------------------------------------------------

def test_restatement_no_mention_anywhere():
    doc = _doc("Ordinary narrative text with nothing relevant on this page.")
    fields = extract_restatement_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    by_name = {f.field_name: f for f in fields}
    assert by_name["restatement_of_past_accounts"].value is False
    assert by_name["restatement_of_past_accounts"].confidence == Confidence.HIGH
    assert by_name["restatement_search_retrieval_tier"].value == RetrievalTier.PRIMARY


def test_restatement_esg_only_excluded():
    doc = _doc(
        "BRSR Disclosures\n"
        "The water withdrawal figure for the prior year has been restated to reflect "
        "a revised measurement methodology under the Business Responsibility and "
        "Sustainability Report."
    )
    fields = extract_restatement_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    by_name = {f.field_name: f for f in fields}
    assert by_name["restatement_of_past_accounts"].value is False
    assert by_name["restatement_esg_only_excluded"].value is True


def test_restatement_genuine_disclosure():
    doc = _doc(
        "Notes to the financial statements\n"
        "The comparative figures for the previous year have been restated to correct "
        "an error in the classification of certain lease liabilities, resulting in a "
        "prior period error of Rs. 42 crore being adjusted against opening retained earnings."
    )
    fields = extract_restatement_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    by_name = {f.field_name: f for f in fields}
    assert by_name["restatement_of_past_accounts"].value is True


def test_restatement_socie_boilerplate_excluded_even_on_continuation_page():
    # Regression: TCS FY26 AR — "Statement of Changes in Equity" title only
    # appears on the table's first page; a continuation page ("B. OTHER
    # EQUITY") repeats the mandated "prior period errors" column with no nil
    # value nearby and no heading of its own. Must not read as a disclosure.
    doc = _doc(
        "Consolidated Statement of Changes in Equity\n"
        "Balance as at April 1, 2025\n"
        "Changes in equity share capital due to prior period errors\n"
        "Restated balance as at April 1, 2025\n"
        "362 - 362",
        "Statutory Reports\nFinancial Statements\nB. OTHER EQUITY\n"
        "Balance as at April 1, 2025\n"
        "Changes in accounting policy / prior period errors\n"
        "75 444 1,085 88,777 - - - - -",
        "Notes forming part of consolidated financial statements\n16) Finance costs",
    )
    fields = extract_restatement_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.CONSOLIDATED)
    by_name = {f.field_name: f for f in fields}
    assert by_name["restatement_of_past_accounts"].value is False
    assert "restatement_esg_only_excluded" not in by_name


def test_restatement_forex_retranslation_not_a_financial_restatement():
    # Regression: TCS FY26 AR accounting-policy note — "restatement" is also
    # Ind AS 21 vocabulary for period-end foreign-currency retranslation.
    doc = _doc(
        "Foreign currency translation\n"
        "Monetary assets and liabilities are retranslated at the exchange "
        "rate prevailing on the balance sheet date and exchange gains and "
        "losses arising on settlement and restatement are recognised in "
        "the statement of profit and loss."
    )
    fields = extract_restatement_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.CONSOLIDATED)
    by_name = {f.field_name: f for f in fields}
    assert by_name["restatement_of_past_accounts"].value is False


def test_restatement_emphasis_of_matter_wins():
    doc = _doc(
        "Emphasis of Matter\n"
        "We draw attention to Note 45 regarding the restatement of prior period figures "
        "on account of a material error identified during the year. Our opinion is not "
        "modified in respect of this matter."
    )
    fields = extract_restatement_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    by_name = {f.field_name: f for f in fields}
    assert by_name["restatement_of_past_accounts"].value is True
    assert by_name["restatement_search_retrieval_tier"].value == RetrievalTier.PRIMARY


# --- Regulatory action --------------------------------------------------------

def test_regulatory_action_clean_disclosure():
    doc = _doc(
        "Secretarial Audit Report\n"
        "During the year under review, the Company has not been subjected to any "
        "penalty by SEBI, RBI or any other regulatory authority."
    )
    f = extract_regulatory_action_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is not None
    assert f.value.active_or_past_5y is False
    assert f.value.nature == RegulatoryNature.NONE
    assert f.value.retrieval_tier == RetrievalTier.FALLBACK
    assert f.confidence == Confidence.MEDIUM


def test_regulatory_action_positive_hit_is_low_confidence():
    doc = _doc(
        "Board's Report\n"
        "SEBI issued an adjudication order imposing a penalty of Rs. 12 lakh on the "
        "Company during the year for delayed disclosure."
    )
    f = extract_regulatory_action_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is not None
    assert f.value.active_or_past_5y is True
    assert f.confidence == Confidence.LOW  # forces manual review, never a silent pass-through


def test_regulatory_action_no_mention_returns_none():
    doc = _doc("This page never mentions any regulator at all.")
    f = extract_regulatory_action_from_doc(doc, "ar.pdf", "FY26", ReportingBasis.STANDALONE)
    assert f is None
