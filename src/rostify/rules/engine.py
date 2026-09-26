"""Runs the currently-enabled rules against a candidate assignment.

This is the one rule engine CLAUDE.md's first architectural rule calls for
— it does not care whether `assignment.layer` is SHIFT or POSITION, and
neither does any individual rule unless it explicitly chooses to filter on
layer.
"""

from __future__ import annotations

from rostify.core.models import Assignment
from rostify.core.schedule import Schedule

from .base import Rule, RuleViolation, Severity


class RuleEngine:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules: list[Rule] = rules or []

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            violations.extend(rule.evaluate(assignment, schedule))
        return violations

    def has_hard_violation(self, violations: list[RuleViolation]) -> bool:
        return any(v.severity == Severity.HARD for v in violations)
