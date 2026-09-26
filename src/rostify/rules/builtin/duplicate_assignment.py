"""Overlap / duplicate-entry check.

Generalizes the xlsb's "duplicate Crew ID within the same day tab" export
check (docs/01-analysis.md R7) into a same-employee, same-layer, overlapping
-time-range check on the unified Assignment model. This is the closest thing
to a real "no double-booking" rule either source actually enforces anywhere
— true double-booking prevention across *different* layers, minimum rest
between shifts, and max-hours rules are an explicit, still-open gap (see
docs/01-analysis.md §4.3) and are not implemented here.
"""

from __future__ import annotations

from rostify.core.models import Assignment
from rostify.core.schedule import Schedule

from ..base import Rule, RuleViolation, Severity


class DuplicateAssignmentRule(Rule):
    id = "duplicate_assignment"
    name = "Overlapping assignment"
    description = (
        "Flags a new assignment that overlaps an existing one for the same "
        "employee on the same layer (shift or position)."
    )
    default_severity = Severity.HARD
    param_schema = []

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        clashes = schedule.overlapping(assignment)
        if not clashes:
            return []
        return [
            self.violation(
                f"Overlaps {len(clashes)} existing assignment(s) for the same "
                f"employee on layer {assignment.layer.value}.",
                assignment_id=assignment.id,
            )
        ]
