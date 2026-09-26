"""YAML-backed rule configuration (CLAUDE.md: "local SQLite plus YAML
configuration files"). This is what turns "rules are data, not code" into
something a user can actually toggle/edit and have persist: the file is a
plain list of {id, enabled, severity, params}, and the settings UI's
generated forms (rostify.ui.panels.settings_panel) read and write through
this module, never by touching a Rule subclass's source.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from rostify.rules.base import Rule, Severity
from rostify.rules.engine import RuleEngine
from rostify.rules.registry import RuleRegistry


def default_rules_config(registry: RuleRegistry) -> list[dict[str, Any]]:
    """Every discovered rule, enabled, at its own default severity — the
    config a first run should end up with.
    """
    entries = []
    for rule_id, rule_cls in sorted(registry.all_rule_classes().items()):
        entries.append(
            {
                "id": rule_id,
                "enabled": True,
                "severity": rule_cls.default_severity.value,
                "params": {f.name: f.default for f in rule_cls.param_schema},
            }
        )
    return entries


def load_rules_config(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("rules", [])


def save_rules_config(path: str | Path, entries: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"rules": entries}, f, sort_keys=False, allow_unicode=True)


def build_rule_engine(registry: RuleRegistry, config_path: str | Path) -> RuleEngine:
    """Load config (writing out sensible defaults on first run) and build a
    ready-to-use RuleEngine from it.
    """
    config_path = Path(config_path)
    entries = load_rules_config(config_path)
    if not entries:
        entries = default_rules_config(registry)
        save_rules_config(config_path, entries)

    rules: list[Rule] = []
    for entry in entries:
        rule_cls = registry.all_rule_classes().get(entry["id"])
        if rule_cls is None:
            continue  # config references a rule that no longer exists
        rule = rule_cls(
            params=entry.get("params", {}),
            severity=Severity(entry.get("severity", rule_cls.default_severity.value)),
            enabled=entry.get("enabled", True),
        )
        rules.append(rule)
    return RuleEngine(rules)
