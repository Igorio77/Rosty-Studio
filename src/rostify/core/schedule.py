"""The Schedule aggregate: holds employees + assignments for one workbook /
voyage, and is the single place both layers (shift and position) are
queried and mutated through.

Deliberately does not import from `rostify.rules` — that would make this
module depend on the plugin layer instead of the other way around. Callers
that want validation pass a `validator` callable in (see `add_assignment`);
`rostify.services` is what actually wires a `RuleEngine` into that slot.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date

from .models import Assignment, Employee, Layer

# A validator takes the candidate assignment and the schedule it would be
# added to, and returns a list of violations (empty means "no objection").
# Kept as `object` here to avoid importing rules.base.RuleViolation from
# core — see module docstring.
Validator = Callable[[Assignment, "Schedule"], list[object]]


class Schedule:
    def __init__(self) -> None:
        self._employees: dict[str, Employee] = {}
        self._assignments: dict[str, Assignment] = {}

    # --- employees ---------------------------------------------------

    def add_employee(self, employee: Employee) -> None:
        self._employees[employee.id] = employee

    def get_employee(self, employee_id: str) -> Employee | None:
        return self._employees.get(employee_id)

    def remove_employee(self, employee_id: str) -> None:
        """Removes the employee record. Mirrors `remove_assignment`: no
        cascade into that employee's assignments — deciding what should
        happen to their existing schedule on removal is caller/UI policy,
        not core's job.
        """
        self._employees.pop(employee_id, None)

    def employees(self, *, active_only: bool = True) -> list[Employee]:
        out = list(self._employees.values())
        if active_only:
            out = [e for e in out if e.active]
        return out

    # --- assignments ---------------------------------------------------

    def add_assignment(
        self, assignment: Assignment, *, validator: Validator | None = None
    ) -> list[object]:
        """Add an assignment. If `validator` is given, runs it first and
        returns whatever violations it reports — the caller decides whether
        a HARD violation should stop the add (this method does not decide
        that itself, since "what counts as HARD" is rule-engine policy, not
        core policy).
        """
        violations: list[object] = []
        if validator is not None:
            violations = validator(assignment, self)
        self._assignments[assignment.id] = assignment
        return violations

    def remove_assignment(self, assignment_id: str) -> None:
        self._assignments.pop(assignment_id, None)

    def assignment(self, assignment_id: str) -> Assignment | None:
        return self._assignments.get(assignment_id)

    def assignments(
        self,
        *,
        employee_id: str | None = None,
        on: date | None = None,
        layer: Layer | None = None,
    ) -> list[Assignment]:
        out: Iterable[Assignment] = self._assignments.values()
        if employee_id is not None:
            out = (a for a in out if a.employee_id == employee_id)
        if on is not None:
            out = (a for a in out if a.start.date() == on)
        if layer is not None:
            out = (a for a in out if a.layer == layer)
        return list(out)

    def overlapping(self, assignment: Assignment) -> list[Assignment]:
        """Existing assignments for the same employee + layer that overlap
        the given assignment's time range. Used by the duplicate/overlap
        builtin rule; exposed here because "what overlaps" is a query the
        aggregate is naturally responsible for.
        """
        return [
            a
            for a in self._assignments.values()
            if a.id != assignment.id
            and a.employee_id == assignment.employee_id
            and a.layer == assignment.layer
            and a.overlaps(assignment)
        ]
