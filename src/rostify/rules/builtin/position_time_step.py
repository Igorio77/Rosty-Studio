"""Position rotation time-step alignment.

Supervisors rotate a dealer table-to-table (and to breaks) on a fixed time
grid — commonly every 15 or 20 minutes, but this varies by casino, so the
step itself must stay a setting, not a constant. This is the same gap
docs/01-analysis.md §4.1 flags under "Time-step whitelist": the xlsb only
validates a fixed [15, 20] pair at the voyage level; here the job is
validating each Position assignment against whatever step is configured.

Defaults to SOFT (warn, not block) since this is a new interpretation of
that gap, not a straight port — flip to HARD in Settings once it's proven
out against real rosters. Scoped to layer POSITION only.
"""

from __future__ import annotations

from rostify.core.models import Assignment, Layer
from rostify.core.schedule import Schedule

from ..base import ParamField, Rule, RuleViolation, Severity


class PositionTimeStepRule(Rule):
    id = "position_time_step"
    name = "Position rotation time step"
    description = (
        "Flags a Position-layer assignment whose start time or duration "
        "doesn't align to the configured rotation time step."
    )
    default_severity = Severity.SOFT
    param_schema = [
        ParamField(
            name="time_step_minutes",
            type="int",
            label="Time step (minutes)",
            default=15,
            min_value=5,
            max_value=60,
            help_text="The rotation grid dealers are moved/broken on (e.g. 15 or 20 minutes).",
        ),
    ]

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        if assignment.layer != Layer.POSITION:
            return []

        step = self.params["time_step_minutes"]
        duration_minutes = (assignment.end - assignment.start).total_seconds() / 60

        violations: list[RuleViolation] = []
        if assignment.start.minute % step != 0:
            violations.append(
                self.violation(
                    f"Start time {assignment.start:%H:%M} doesn't align to the "
                    f"{step}-minute rotation step.",
                    assignment_id=assignment.id,
                )
            )
        if duration_minutes % step != 0:
            violations.append(
                self.violation(
                    f"Duration {duration_minutes:.0f} min isn't a multiple of the "
                    f"{step}-minute rotation step.",
                    assignment_id=assignment.id,
                )
            )
        return violations
