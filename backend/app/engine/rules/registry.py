"""
In-memory registry managing the active rules configuration and sector resolution.
"""

from typing import Optional, Tuple
from threading import Lock

from backend.app.models.enums import Phase2Sector
from backend.app.engine.rules.config import (
    RulesConfiguration,
    create_default_rules_configuration,
)


class RulesRegistry:
    """Thread-safe manager for the active dynamic rules configuration."""

    def __init__(self):
        self._lock = Lock()
        self._active_config: RulesConfiguration = create_default_rules_configuration()

    def get_config(self) -> RulesConfiguration:
        with self._lock:
            return self._active_config

    def set_config(self, config: RulesConfiguration) -> None:
        with self._lock:
            self._active_config = config

    def reset_to_default(self) -> RulesConfiguration:
        with self._lock:
            self._active_config = create_default_rules_configuration()
            return self._active_config


# Global singleton registry
_REGISTRY = RulesRegistry()


def get_active_rules_config() -> RulesConfiguration:
    """Returns the currently active rules configuration."""
    return _REGISTRY.get_config()


def set_active_rules_config(config: RulesConfiguration) -> None:
    """Updates the active rules configuration."""
    _REGISTRY.set_config(config)


def reset_to_default_config() -> RulesConfiguration:
    """Resets the rules configuration to baseline defaults."""
    return _REGISTRY.reset_to_default()


def resolve_sector_from_keyword(
    keyword_or_name: str,
    config: Optional[RulesConfiguration] = None,
) -> Tuple[Phase2Sector, Optional[str]]:
    """
    Looks up a sector profile given an industry keyword, company name, or description.
    Uses substring and exact keyword matching against the active Sector_Mapping sheet.
    Returns (ResolvedSector, MatchedKeywordOrNote).
    Defaults to Phase2Sector.STANDARD if no keyword matches.
    """
    if not keyword_or_name:
        return Phase2Sector.STANDARD, None

    cfg = config or get_active_rules_config()
    target_lower = keyword_or_name.lower().strip()

    # 1. Exact match check
    for item in cfg.sector_mappings:
        if item.keyword.lower() == target_lower:
            return item.sector, f"Exact match for keyword '{item.keyword}'"

    # 2. Substring match check (e.g., 'Tech Mahindra Software' matches 'Software')
    for item in cfg.sector_mappings:
        kw_lower = item.keyword.lower()
        if kw_lower in target_lower or target_lower in kw_lower:
            return item.sector, f"Matched keyword '{item.keyword}' in '{keyword_or_name}'"

    return Phase2Sector.STANDARD, None
