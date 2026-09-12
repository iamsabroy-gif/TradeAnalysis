"""
Core acquisition types and exceptions for Phase 1 Gatekeeper.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §3.1 & §3.3.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from backend.app.models.enums import Confidence, ExtractionMethod, PdfClass, ReportingBasis


@dataclass(frozen=True)
class RawPage:
    source: str
    url: str
    content: str
    fetched_at: datetime
    from_cache: bool
    basis: ReportingBasis


@dataclass(frozen=True)
class ExtractedField:
    field_name: str
    value: Any
    confidence: Confidence
    extraction_method: ExtractionMethod
    source: str
    period: str
    basis: ReportingBasis
    raw_snippet: str
    page: Optional[int] = None
    document_id: Optional[str] = None
    source_page: Optional[int] = None

    def __post_init__(self):
        if self.page is None and self.source_page is not None:
            object.__setattr__(self, "page", self.source_page)
        elif self.source_page is None and self.page is not None:
            object.__setattr__(self, "source_page", self.page)



@dataclass
class SourceDocument:
    doc_id: str
    ticker: str
    filename: str
    fiscal_year: Optional[str]
    basis: ReportingBasis
    pdf_class: PdfClass
    page_count: int
    stored_path: str
    uploaded_at: str
    uploader: Optional[str] = None


@dataclass(frozen=True)
class DocumentRef:
    fiscal_year: str
    url: str
    title: str


@dataclass
class AdapterError:
    field_name: Optional[str]
    message: str
    fatal: bool = False


@dataclass
class NotFoundField:
    """
    Distinguishes "this adapter genuinely owns this field and searched for
    it in this document, but found nothing" from a field the adapter never
    attempts at all. A field with no NotFoundField AND no ExtractedField
    entry was never in scope for this adapter — that is not reported here,
    since reporting it would blur "not found" with "not attempted".
    """

    field_name: str
    reason: str


@dataclass
class AdapterResult:
    adapter: str
    fields: List[ExtractedField] = field(default_factory=list)
    documents: List[DocumentRef] = field(default_factory=list)
    errors: List[AdapterError] = field(default_factory=list)
    pages: List[RawPage] = field(default_factory=list)
    not_found: List[NotFoundField] = field(default_factory=list)


@dataclass(frozen=True)
class CompanyIdentity:
    ticker: str
    screener_code: str
    bse_scrip_code: Optional[str] = None
    nse_symbol: Optional[str] = None
    company_name: str = ""
    listing_date: Optional[str] = None


class AcquisitionError(Exception):
    """Base exception for data acquisition."""
    pass


class LayoutChangedError(AcquisitionError):
    """Raised when expected HTML/table structure does not match assertions."""
    pass


class SourceUnavailableError(AcquisitionError):
    """Raised when source network call fails or circuit breaker is open."""
    pass


class TickerNotFoundError(AcquisitionError):
    """Raised when a ticker cannot be found in the source master."""
    pass


class AmbiguousTickerError(AcquisitionError):
    """Raised when a ticker resolves to multiple distinct candidates."""
    def __init__(self, ticker: str, candidates: List[Any]):
        super().__init__(f"Ambiguous ticker '{ticker}': found candidates {candidates}")
        self.ticker = ticker
        self.candidates = candidates
