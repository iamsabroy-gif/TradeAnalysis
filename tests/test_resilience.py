"""
Unit tests for caching, circuit breaker, and rate-limiting.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §4.
"""

from datetime import datetime, timezone
import time
import pytest

from backend.app.acquisition.cache import FileCache
from backend.app.acquisition.http_client import CircuitBreaker, RateLimiter, SourceHttpClient
from backend.app.acquisition.types import TickerNotFoundError
from backend.app.models.enums import ReportingBasis


def test_file_cache(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    now = datetime.now(timezone.utc)

    # 1. Miss initially
    hit = cache.get("test_source", "https://example.com/company", ReportingBasis.CONSOLIDATED)
    assert hit is None

    # 2. Set cache with 10 second TTL
    cache.set(
        "test_source",
        "https://example.com/company",
        ReportingBasis.CONSOLIDATED,
        "<html>test</html>",
        fetched_at=now,
        ttl_seconds=10,
    )

    # 3. Hit
    hit = cache.get("test_source", "https://example.com/company", ReportingBasis.CONSOLIDATED)
    assert hit is not None
    content, fetched_at = hit
    assert content == "<html>test</html>"
    assert fetched_at == now

    # 4. Mismatched basis is a miss
    hit_sa = cache.get("test_source", "https://example.com/company", ReportingBasis.STANDALONE)
    assert hit_sa is None


def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=1)
    assert cb.state == "CLOSED"
    assert cb.can_request() is True

    # 2 failures
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "CLOSED"

    # 3rd failure trips breaker
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.can_request() is False

    # Wait cooldown
    time.sleep(1.1)
    assert cb.can_request() is True
    assert cb.state == "HALF_OPEN"

    # Success closes breaker
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.consecutive_failures == 0


def test_circuit_breaker_reset():
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=600)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.seconds_until_retry() > 0

    cb.reset()
    assert cb.state == "CLOSED"
    assert cb.can_request() is True
    assert cb.seconds_until_retry() == 0


def test_404_does_not_trip_breaker(tmp_path, monkeypatch):
    """An unknown ticker is a caller mistake and must not take the source offline."""

    class _Resp:
        status_code = 404
        text = ""
        url = "https://www.screener.in/company/NOPE/"

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr("backend.app.acquisition.http_client.httpx.Client", _FakeClient)

    client = SourceHttpClient(
        cache=FileCache(cache_dir=tmp_path),
        rate_limit_seconds=0.0,
        enforce_robots=False,
    )

    for _ in range(10):
        with pytest.raises(TickerNotFoundError):
            client.fetch_page(
                source="screener",
                url="https://www.screener.in/company/NOPE/",
                basis=ReportingBasis.CONSOLIDATED,
            )

    assert client.get_circuit_state("screener") == "CLOSED"


def test_reset_circuit_reopens_source(tmp_path):
    client = SourceHttpClient(cache=FileCache(cache_dir=tmp_path), enforce_robots=False)
    breaker = client._get_breaker("screener")
    for _ in range(breaker.failure_threshold):
        breaker.record_failure()
    assert client.get_circuit_state("screener") == "OPEN"

    assert client.reset_circuit("screener") == "CLOSED"
