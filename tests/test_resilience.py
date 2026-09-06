"""
Unit tests for caching, circuit breaker, and rate-limiting.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §4.
"""

from datetime import datetime, timezone
import time
import pytest

from backend.app.acquisition.cache import FileCache
from backend.app.acquisition.http_client import CircuitBreaker, RateLimiter
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
