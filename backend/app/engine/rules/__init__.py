"""
Rule Engine Dynamic Configuration Package.
Provides decoupled, user-configurable rules via Excel upload.
"""

from backend.app.engine.rules.config import (
    Phase1RuleConfig,
    SectorThresholdConfig,
    Phase2MatrixConfig,
    SectorKeywordItem,
    RulesConfiguration,
    create_default_rules_configuration,
)
from backend.app.engine.rules.registry import (
    get_active_rules_config,
    set_active_rules_config,
    reset_to_default_config,
    resolve_sector_from_keyword,
)
from backend.app.engine.rules.excel_io import (
    generate_default_rules_workbook,
    parse_rules_config_workbook,
)

__all__ = [
    "Phase1RuleConfig",
    "SectorThresholdConfig",
    "Phase2MatrixConfig",
    "SectorKeywordItem",
    "RulesConfiguration",
    "create_default_rules_configuration",
    "get_active_rules_config",
    "set_active_rules_config",
    "reset_to_default_config",
    "resolve_sector_from_keyword",
    "generate_default_rules_workbook",
    "parse_rules_config_workbook",
]
