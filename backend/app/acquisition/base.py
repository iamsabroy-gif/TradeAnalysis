"""
Abstract Base Class for Data Acquisition Adapters.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §3.2.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, FrozenSet, List

from backend.app.models.enums import ReportingBasis
from .types import AdapterResult, CompanyIdentity, RawPage


class SourceAdapter(ABC):
    """
    Abstract adapter interface.
    fetch() does all I/O; parse() does none (pure function).
    parse() never raises for missing optional fields.
    """
    name: str
    owns_fields: FrozenSet[str]

    @abstractmethod
    def fetch(self, ident: CompanyIdentity, basis: ReportingBasis) -> List[RawPage]:
        """Fetch raw HTML/JSON pages from network or storage."""
        pass

    @abstractmethod
    def parse(self, pages: List[RawPage]) -> AdapterResult:
        """Parse raw pages into ExtractedField list. Pure function, zero I/O."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check source connectivity or circuit breaker state."""
        pass
