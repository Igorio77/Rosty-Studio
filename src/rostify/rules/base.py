"""Rule base classes.

CLAUDE.md's second architectural rule: scheduling rules are data, not code.
A rule is a small plugin class that declares its own parameters through
`param_schema`; the settings UI builds its edit form from that schema alone
(rostify.ui.panels.settings_panel), so adding a new rule never means
touching UI code — only adding one file under `rules/builtin/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from rostify.core.models import Assignment
from rostify.core.schedule import Schedule


class Severity(str, Enum):
    HARD = "hard"  # blocks the action
    SOFT = "soft"  # warns only


@dataclass(slots=True)
class RuleViolation:
    rule_id: str
    severity: Severity
    message: str
    assignment_id: str | None = None


@dataclass(slots=True)
class ParamField:
    """One editable parameter of a rule, as data the settings UI reads to
    build a form control — never as a UI widget itself (that would put Qt
    knowledge in this package, which CLAUDE.md's layer boundaries forbid).
    """

    name: str
    type: str  # "int" | "float" | "str" | "bool" | "choice"
    label: str
    default: Any
    help_text: str = ""
    min_value: float | None = None
    max_value: float | None = None
    choices: list[str] = field(default_factory=list)


class Rule(ABC):
    """Base class every builtin (and, later, user-authored) rule extends."""

    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str] = ""
    default_severity: ClassVar[Severity] = Severity.SOFT
    param_schema: ClassVar[list[ParamField]] = []

    def __init__(
        self,
        params: dict[str, Any] | None = None,
        *,
        severity: Severity | None = None,
        enabled: bool = True,
    ) -> None:
        schema_defaults = {f.name: f.default for f in self.param_schema}
        self.params: dict[str, Any] = {**schema_defaults, **(params or {})}
        self.severity = severity or self.default_severity
        self.enabled = enabled

    @abstractmethod
    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        """Check `assignment` (which is being added/edited) against
        `schedule` (the rest of the current data). Return zero or more
        violations; the caller (RuleEngine) stamps each with this rule's
        current `severity`.
        """
        raise NotImplementedError

    def violation(self, message: str, *, assignment_id: str | None = None) -> RuleViolation:
        """Convenience constructor so builtin rules don't repeat
        `rule_id=self.id, severity=self.severity` at every call site.
        """
        return RuleViolation(
            rule_id=self.id,
            severity=self.severity,
            message=message,
            assignment_id=assignment_id,
        )
