"""Weekly hours threshold.

Not a cap — a warning. The domain expert wants a configurable
weekly-hours flag (e.g. 77h/week) that surfaces to a supervisor for review,
not a hard block, so this defaults to SOFT. In this UI, SOFT means the
existing "Add anyway?" confirmation in schedule_panel.py; a real push/email
notification to another role needs multi-user sync, which is a later phase
per CLAUDE.md.

Scoped to layer SHIFT only — Position-layer rotation slots happen inside
their own shift, so counting both would double-count hours.
"""

from __future__ import annotations

from rostify.core.models import Assignment, Layer
from rostify.core.schedule import Schedule

from ..base import ParamField, Rule, RuleViolation, Severity


class WeeklyHoursThresholdRule(Rule):
    id = "weekly_hours_threshold"
    name = "Weekly hours threshold"
    description = (
        "Warns when an employee's total shift hours for the calendar week "
        "reach a configured threshold, so a supervisor can review before "
        "hours climb further."
    )
    default_severity = Severity.SOFT
    param_schema = [
        ParamField(
            name="max_weekly_hours",
            type="float",
            label="Max hours per week",
            default=77.0,
            min_value=1.0,
            max_value=168.0,
            help_text="This warns when reached; it does not block the assignment.",
        ),
    ]

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        if assignment.layer != Layer.SHIFT:
            return []

        week_key = assignment.start.isocalendar()[:2]  # (iso_year, iso_week)
        same_week = [
            a
            for a in schedule.assignments(employee_id=assignment.employee_id, layer=Layer.SHIFT)
            if a.id != assignment.id and a.start.isocalendar()[:2] == week_key
        ]
        same_week.append(assignment)

        total_hours = sum((a.end - a.start).total_seconds() for a in same_week) / 3600
        threshold = self.params["max_weekly_hours"]
        if total_hours < threshold:
            return []

        return [
            self.violation(
                f"Employee reaches {total_hours:.1f}h this week "
                f"(threshold {threshold}h) — notify a supervisor.",
                assignment_id=assignment.id,
            )
        ]
