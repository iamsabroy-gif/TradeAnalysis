"""
Caching layer for Data Acquisition.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §4.
Keys: sha256(source | canonical_url | basis)
Stores true fetched_at timestamp as value so provenance reflects reality even on cache hits.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Optional, Protocol, Tuple

from backend.app.models.enums import ReportingBasis


class CacheBackend(Protocol):
    def get(self, source: str, canonical_url: str, basis: ReportingBasis) -> Optional[Tuple[str, datetime]]:
        ...

    def set(
        self,
        source: str,
        canonical_url: str,
        basis: ReportingBasis,
        content: str,
        fetched_at: datetime,
        ttl_seconds: int = 86400,
    ) -> None:
        ...


class FileCache:
    """File-backed local cache under var/cache/."""

    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parent.parent.parent.parent / "var" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, source: str, canonical_url: str, basis: ReportingBasis) -> str:
        raw = f"{source}|{canonical_url}|{basis.value}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def get(self, source: str, canonical_url: str, basis: ReportingBasis) -> Optional[Tuple[str, datetime]]:
        key = self._make_key(source, canonical_url, basis)
        filepath = self.cache_dir / f"{key}.json"
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            expires_at = datetime.fromisoformat(data["expires_at"])
            now = datetime.now(timezone.utc)
            if now > expires_at:
                return None  # Expired

            content = data["content"]
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            return content, fetched_at
        except Exception:
            return None

    def set(
        self,
        source: str,
        canonical_url: str,
        basis: ReportingBasis,
        content: str,
        fetched_at: datetime,
        ttl_seconds: int = 86400,
    ) -> None:
        key = self._make_key(source, canonical_url, basis)
        filepath = self.cache_dir / f"{key}.json"

        now = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)

        data = {
            "source": source,
            "url": canonical_url,
            "basis": basis.value,
            "content": content,
            "fetched_at": fetched_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass
