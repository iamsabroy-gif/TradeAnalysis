"""
Persistence store for Phase 2 Gatekeeper evaluation results.
"""

from typing import Dict, Optional
from backend.app.models.phase2_schemas import CompanyPhase2Input, Phase2Result


class Phase2Store:
    """In-memory store for Phase 2 evaluation results and inputs."""

    def __init__(self) -> None:
        self._results: Dict[str, Phase2Result] = {}
        self._inputs: Dict[str, CompanyPhase2Input] = {}
        self._ticker_latest: Dict[str, str] = {}

    def save_result(self, result: Phase2Result, company_input: CompanyPhase2Input) -> None:
        self._results[result.result_id] = result
        self._inputs[result.result_id] = company_input
        self._ticker_latest[result.ticker.upper()] = result.result_id

    def get_result(self, result_id: str) -> Optional[Phase2Result]:
        return self._results.get(result_id)

    def get_input(self, result_id: str) -> Optional[CompanyPhase2Input]:
        return self._inputs.get(result_id)

    def latest_result_id_for_ticker(self, ticker: str) -> Optional[str]:
        return self._ticker_latest.get(ticker.upper())


_PHASE2_STORE = Phase2Store()


def get_phase2_store() -> Phase2Store:
    return _PHASE2_STORE
