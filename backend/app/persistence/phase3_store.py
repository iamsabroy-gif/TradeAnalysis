"""
Persistence store for Phase 3 Gatekeeper evaluation results.
"""

from typing import Dict, Optional
from backend.app.models.phase3_schemas import CompanyPhase3Input, Phase3Result


class Phase3Store:
    """In-memory store for Phase 3 evaluation results and inputs."""

    def __init__(self) -> None:
        self._results: Dict[str, Phase3Result] = {}
        self._inputs: Dict[str, CompanyPhase3Input] = {}
        self._ticker_latest: Dict[str, str] = {}

    def save_result(self, result: Phase3Result, company_input: CompanyPhase3Input) -> None:
        self._results[result.result_id] = result
        self._inputs[result.result_id] = company_input
        self._ticker_latest[result.ticker.upper()] = result.result_id

    def get_result(self, result_id: str) -> Optional[Phase3Result]:
        return self._results.get(result_id)

    def get_input(self, result_id: str) -> Optional[CompanyPhase3Input]:
        return self._inputs.get(result_id)

    def latest_result_id_for_ticker(self, ticker: str) -> Optional[str]:
        return self._ticker_latest.get(ticker.upper())


_PHASE3_STORE = Phase3Store()


def get_phase3_store() -> Phase3Store:
    return _PHASE3_STORE
