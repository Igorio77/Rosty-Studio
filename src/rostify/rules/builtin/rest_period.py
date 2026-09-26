"""Minimum rest between shifts.

Closes one of the explicit gaps in docs/01-analysis.md §4.3: neither the
xlsb nor the jsx prototype enforces any rest-period rule, they only display
hours. Scoped to layer SHIFT only — a Position (layer B) assignment is a
table-rotation slot inside its own shift, not a separate work block, so rest
is measured between shifts, not between rotation slots.
"""

from __future__ import annotations

from datetime import timedelta

from rostify.core.models import Assignment, Layer
from rostify.core.schedule import Schedule

from ..base import ParamField, Rule, RuleViolation, Severity


class RestPeriodRule(Rule):
    id = "rest_period"
    name = "Minimum rest between shifts"
    description = (
        "Flags a Shift-layer assignment that leaves less than the configured "
        "rest period before or after another shift for the same employee."
    )
    default_severity = Severity.HARD
    param_schema = [
        ParamField(
            name="min_rest_hours",
            type="float",
            label="Minimum rest (hours)",
            default=10.0,
            min_value=0.0,
            max_value=48.0,
            help_text="Gap required between the end of one shift and the start of the next.",
        ),
    ]

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        if assignment.layer != Layer.SHIFT:
            return []

        min_rest = timedelta(hours=self.params["min_rest_hours"])
        others = [
            a
            for a in schedule.assignments(employee_id=assignment.employee_id, layer=Layer.SHIFT)
            if a.id != assignment.id
        ]

        violations: list[RuleViolation] = []
        for other in others:
            if other.overlaps(assignment):
                continue  # duplicate_assignment's job, not this rule's

            if other.start >= assignment.end:
                gap = other.start - assignment.end
            else:
                gap = assignment.start - other.end

            if gap < min_rest:
                violations.append(
                    self.violation(
                        f"Only {gap} rest next to the shift on "
                        f"{other.start:%Y-%m-%d %H:%M}–{other.end:%H:%M} "
                        f"(minimum is {self.params['min_rest_hours']}h).",
                        assignment_id=assignment.id,
                    )
                )
        return violations
