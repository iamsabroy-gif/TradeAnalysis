"""
Resilience HTTP client for Data Acquisition.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §4.
Includes rate limiting, caching, exponential backoff, and circuit breaker.
"""

from datetime import datetime, timezone
import logging
import random
import time
from typing import Dict, Optional, Tuple
import httpx

from backend.app.models.enums import ReportingBasis
from .cache import CacheBackend, FileCache
from .robots import check_robots
from .types import RawPage, SourceUnavailableError, TickerNotFoundError

logger = logging.getLogger("phase1.acquisition.http")


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 600):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def reset(self):
        """Manually clears the breaker (e.g. operator retry after a bad ticker)."""
        self.consecutive_failures = 0
        self.state = "CLOSED"
        self.last_failure_time = None

    def seconds_until_retry(self) -> int:
        """Remaining cooldown before the breaker will probe again."""
        if self.state != "OPEN" or self.last_failure_time is None:
            return 0
        return max(0, int(self.cooldown_seconds - (time.time() - self.last_failure_time)))

    def record_success(self):
        self.consecutive_failures = 0
        self.state = "CLOSED"
        self.last_failure_time = None

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker tripped OPEN after {self.consecutive_failures} consecutive failures. "
                f"Cooldown: {self.cooldown_seconds}s"
            )

    def can_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure_time and (time.time() - self.last_failure_time > self.cooldown_seconds):
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN probe state")
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return True


class RateLimiter:
    """Token bucket / interval rate limiter per source."""

    def __init__(self, interval_seconds: float = 1.5):
        self.interval_seconds = interval_seconds
        self.last_request_time: float = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.interval_seconds:
            sleep_time = self.interval_seconds - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()


class SourceHttpClient:
    def __init__(
        self,
        user_agent: str = "Phase1Gatekeeper/1.0 (+research@antigravity.internal)",
        cache: Optional[CacheBackend] = None,
        rate_limit_seconds: float = 1.5,
        enforce_robots: bool = True,
    ):
        self.user_agent = user_agent
        self.cache: CacheBackend = cache or FileCache()
        self.rate_limiter = RateLimiter(interval_seconds=rate_limit_seconds)
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.enforce_robots = enforce_robots

    def _get_breaker(self, source: str) -> CircuitBreaker:
        if source not in self.breakers:
            self.breakers[source] = CircuitBreaker()
        return self.breakers[source]

    def get_circuit_state(self, source: str) -> str:
        return self._get_breaker(source).state

    def reset_circuit(self, source: str) -> str:
        """Force a source's breaker back to CLOSED so the next call is attempted."""
        self._get_breaker(source).reset()
        return self._get_breaker(source).state

    def fetch_page(
        self,
        source: str,
        url: str,
        basis: ReportingBasis,
        bypass_cache: bool = False,
        timeout: float = 10.0,
    ) -> RawPage:
        """
        Fetches page with caching, rate limiting, retries, and circuit breaker.
        """
        breaker = self._get_breaker(source)
        if not breaker.can_request():
            raise SourceUnavailableError(
                f"Source '{source}' is currently unavailable (circuit breaker is OPEN due to repeated errors). "
                f"Retrying automatically in {breaker.seconds_until_retry()}s."
            )

        # 1. Check cache
        if not bypass_cache:
            hit = self.cache.get(source, url, basis)
            if hit is not None:
                content, fetched_at = hit
                return RawPage(
                    source=source,
                    url=url,
                    content=content,
                    fetched_at=fetched_at,
                    from_cache=True,
                    basis=basis,
                )

        # 2. Check robots.txt
        if self.enforce_robots:
            check_robots(url, user_agent=self.user_agent)

        # 3. Rate limiting
        self.rate_limiter.wait()

        # 4. HTTP fetch with exponential backoff
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        }

        attempts = 0
        max_attempts = 3
        last_err = None

        while attempts < max_attempts:
            attempts += 1
            try:
                with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        breaker.record_success()
                        now = datetime.now(timezone.utc)
                        content = resp.text
                        self.cache.set(source, str(resp.url), basis, content, now)
                        return RawPage(
                            source=source,
                            url=str(resp.url),
                            content=content,
                            fetched_at=now,
                            from_cache=False,
                            basis=basis,
                        )
                    elif resp.status_code in (429, 503):
                        wait_time = (2 ** attempts) + random.uniform(0.1, 0.5)
                        logger.warning(f"Source '{source}' returned HTTP {resp.status_code}. Backing off {wait_time:.1f}s (attempt {attempts}/{max_attempts})")
                        time.sleep(wait_time)
                        last_err = f"HTTP {resp.status_code}"
                    elif resp.status_code == 404:
                        # Unknown ticker/company: a caller mistake, not a source outage.
                        raise TickerNotFoundError(
                            f"No page found at {url} (HTTP 404) - check the ticker or Screener code"
                        )
                    elif 400 <= resp.status_code < 500:
                        # Other client errors are request-specific; they say nothing about
                        # source health, so they must not count toward the breaker.
                        raise SourceUnavailableError(f"HTTP {resp.status_code} from {url}")
                    else:
                        breaker.record_failure()
                        raise SourceUnavailableError(f"HTTP {resp.status_code} from {url}")
            except httpx.RequestError as e:
                last_err = str(e)
                wait_time = (2 ** attempts) + random.uniform(0.1, 0.5)
                logger.warning(f"Request error for '{url}': {e}. Retrying in {wait_time:.1f}s")
                time.sleep(wait_time)

        breaker.record_failure()
        raise SourceUnavailableError(f"Failed to fetch {url} after {max_attempts} attempts: {last_err}")
