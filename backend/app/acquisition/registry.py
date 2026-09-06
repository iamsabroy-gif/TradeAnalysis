"""
Adapter Registry for Phase 1 Gatekeeper.
Maintains active adapters and powers /api/sources/health.
"""

from typing import Dict, List, Optional
from .base import SourceAdapter


class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, SourceAdapter] = {}
        self._enabled_sources: set[str] = set()

    def register(self, adapter: SourceAdapter, enabled: bool = True):
        self._adapters[adapter.name] = adapter
        if enabled:
            self._enabled_sources.add(adapter.name)

    def get_adapter(self, name: str) -> Optional[SourceAdapter]:
        return self._adapters.get(name)

    def get_enabled_adapters(self) -> List[SourceAdapter]:
        return [adapter for name, adapter in self._adapters.items() if name in self._enabled_sources]

    def set_enabled(self, name: str, enabled: bool):
        if enabled:
            self._enabled_sources.add(name)
        else:
            self._enabled_sources.discard(name)

    def is_enabled(self, name: str) -> bool:
        return name in self._enabled_sources

    def health_check_all(self) -> Dict[str, dict]:
        status = {}
        for name, adapter in self._adapters.items():
            status[name] = {
                "enabled": name in self._enabled_sources,
                "health": adapter.health_check(),
            }
        return status


# Global registry instance
registry = AdapterRegistry()
