"""
Result store interface and implementations.

The store deals in plain JSON-safe dicts (produced by ``model_dump(mode="json")``)
so it stays decoupled from the Pydantic models. Callers reconstruct
``Phase1Result`` / ``CompanyInput`` with ``model_validate`` on read.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)


class ResultStore(Protocol):
    """Storage contract for Phase 1 evaluation results."""

    def save_result(
        self,
        result_id: str,
        ticker: str,
        result: Dict[str, Any],
        company_input: Dict[str, Any],
    ) -> None:
        """Persist (or overwrite) a result and its originating input."""
        ...

    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Return ``{"result": ..., "company_input": ...}`` or ``None`` if unknown."""
        ...

    def latest_result_id_for_ticker(self, ticker: str) -> Optional[str]:
        """Return the ``result_id`` of the most recently saved result for a ticker."""
        ...


class InMemoryResultStore:
    """Process-local store. Not durable across serverless invocations."""

    def __init__(self) -> None:
        self._results: Dict[str, Dict[str, Any]] = {}
        self._inputs: Dict[str, Dict[str, Any]] = {}
        self._ticker_latest: Dict[str, str] = {}

    def save_result(
        self,
        result_id: str,
        ticker: str,
        result: Dict[str, Any],
        company_input: Dict[str, Any],
    ) -> None:
        self._results[result_id] = result
        self._inputs[result_id] = company_input
        self._ticker_latest[ticker] = result_id

    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        if result_id not in self._results:
            return None
        return {
            "result": self._results[result_id],
            "company_input": self._inputs.get(result_id),
        }

    def latest_result_id_for_ticker(self, ticker: str) -> Optional[str]:
        return self._ticker_latest.get(ticker)


# --- Store selection ---------------------------------------------------------

_STORE_SINGLETON: Optional[ResultStore] = None


def _build_store() -> ResultStore:
    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_SECRET_KEY")
    )
    if url and key:
        try:
            from .supabase_store import SupabaseResultStore

            store = SupabaseResultStore(url, key)
            logger.info("Using SupabaseResultStore for result persistence.")
            return store
        except Exception:  # pragma: no cover - defensive fallback
            logger.exception(
                "Failed to initialise SupabaseResultStore; "
                "falling back to in-memory storage."
            )
    else:
        logger.info(
            "SUPABASE_URL / service key not set; using in-memory result storage."
        )
    return InMemoryResultStore()


def get_store() -> ResultStore:
    """Return the process-wide result store, building it on first use."""
    global _STORE_SINGLETON
    if _STORE_SINGLETON is None:
        _STORE_SINGLETON = _build_store()
    return _STORE_SINGLETON


def reset_store_cache() -> None:
    """Clear the cached store. Primarily for tests that toggle env vars."""
    global _STORE_SINGLETON
    _STORE_SINGLETON = None
