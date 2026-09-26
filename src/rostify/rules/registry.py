"""Discovers Rule subclasses under `rostify.rules.builtin` so the engine and
the settings UI never need a hardcoded import list. Adding a new rule means
adding one file under `rules/builtin/` — nothing here changes.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from . import builtin
from .base import Rule


class RuleRegistry:
    def __init__(self) -> None:
        self._classes: dict[str, type[Rule]] = {}
        self._discover()

    def _discover(self) -> None:
        for module_info in pkgutil.iter_modules(builtin.__path__, prefix=f"{builtin.__name__}."):
            module = importlib.import_module(module_info.name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Rule)
                    and obj is not Rule
                    and getattr(obj, "id", None)
                    and obj.__module__ == module.__name__
                ):
                    self._classes[obj.id] = obj

    def all_rule_classes(self) -> dict[str, type[Rule]]:
        return dict(self._classes)

    def get(self, rule_id: str) -> type[Rule]:
        return self._classes[rule_id]
