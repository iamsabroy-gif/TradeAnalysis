"""
Screener.in Adapter for Phase 1 Gatekeeper.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §5.
Fetches consolidated or standalone HTML and extracts Phase C fields.
"""

from typing import Any, Dict, FrozenSet, List, Optional

from backend.app.acquisition.base import SourceAdapter
from backend.app.acquisition.http_client import SourceHttpClient
from backend.app.acquisition.types import (
    AdapterResult,
    CompanyIdentity,
    RawPage,
)
from backend.app.models.enums import ReportingBasis
from .parsers.screener_tables import parse_screener_html


class ScreenerAdapter(SourceAdapter):
    name = "ScreenerAdapter"
    owns_fields: FrozenSet[str] = frozenset(
        {
            "cfo_last_5y",
            "pat_last_5y",
            "promoter_holding_pct_of_company",
            "govt_shareholding_pct",
            "pledged_pct_of_promoter_holding",
            "pledged_pct_history_last_4q",
            "revenue",
            "net_worth",
            "years_of_track_record_available",
        }
    )

    def __init__(self, http_client: Optional[SourceHttpClient] = None):
        self.http_client = http_client or SourceHttpClient()

    def fetch(self, ident: CompanyIdentity, basis: ReportingBasis) -> List[RawPage]:
        """
        Fetches the company page matching declared basis.
        """
        code = ident.screener_code or ident.ticker
        base_url = f"https://www.screener.in/company/{code}/"
        url = f"{base_url}consolidated/" if basis == ReportingBasis.CONSOLIDATED else base_url

        page = self.http_client.fetch_page(source="screener", url=url, basis=basis)
        return [page]

    def parse(self, pages: List[RawPage]) -> AdapterResult:
        if not pages:
            return AdapterResult(adapter=self.name)
        return parse_screener_html(
            html_content=pages[0].content,
            source_url=pages[0].url,
            basis=pages[0].basis,
        )

    def health_check(self) -> Dict[str, Any]:
        state = self.http_client.get_circuit_state("screener")
        return {
            "status": "healthy" if state == "CLOSED" else "degraded",
            "circuit_breaker": state,
        }
