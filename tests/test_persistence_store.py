"""
Unit tests for the result store, focusing on graceful degradation when the
primary (e.g. Supabase) store fails. A persistence outage must not turn an
evaluation into a 500 — the report is returned inline, so the store failure is
logged and served from an in-memory fallback instead.
"""

import pytest

from backend.app.persistence.store import (
    InMemoryResultStore,
    ResilientResultStore,
)


class BrokenStore:
    """Primary store whose every operation raises, e.g. missing table / bad key."""

    def save_result(self, *args, **kwargs):
        raise RuntimeError('relation "phase1_results" does not exist')

    def get_result(self, *args, **kwargs):
        raise RuntimeError("network unreachable")

    def latest_result_id_for_ticker(self, *args, **kwargs):
        raise RuntimeError("network unreachable")


def _sample():
    return ("rid-1", "TCS", {"result_id": "rid-1"}, {"ticker": "TCS"})


def test_save_does_not_raise_when_primary_fails():
    store = ResilientResultStore(BrokenStore())
    # Must not propagate the primary's exception.
    store.save_result(*_sample())


def test_read_back_from_fallback_after_failed_primary_save():
    store = ResilientResultStore(BrokenStore())
    rid, ticker, result, company_input = _sample()
    store.save_result(rid, ticker, result, company_input)

    record = store.get_result(rid)
    assert record is not None
    assert record["result"] == result
    assert record["company_input"] == company_input

    assert store.latest_result_id_for_ticker(ticker) == rid


def test_missing_result_returns_none_not_error():
    store = ResilientResultStore(BrokenStore())
    assert store.get_result("does-not-exist") is None
    assert store.latest_result_id_for_ticker("NOPE") is None


def test_primary_success_is_passed_through():
    primary = InMemoryResultStore()
    store = ResilientResultStore(primary)
    rid, ticker, result, company_input = _sample()
    store.save_result(rid, ticker, result, company_input)

    # Served from the primary, and the primary really holds it.
    assert store.get_result(rid)["result"] == result
    assert primary.get_result(rid)["result"] == result
    assert store.latest_result_id_for_ticker(ticker) == rid
