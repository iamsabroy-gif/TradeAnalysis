"""
Core acquisition types and exceptions for Phase 1 Gatekeeper.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §3.1 & §3.3.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from backend.app.models.enums import Confidence, ExtractionMethod, ReportingBasis


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
class AdapterResult:
    adapter: str
    fields: List[ExtractedField] = field(default_factory=list)
    documents: List[DocumentRef] = field(default_factory=list)
    errors: List[AdapterError] = field(default_factory=list)
    pages: List[RawPage] = field(default_factory=list)


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
