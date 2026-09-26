"""Field length limit — ported from the xlsb's export-time check
(docs/01-analysis.md R7: Last Name/First Name/Location capped at 50 chars,
shift description at 100). Here it checks `Assignment.resource` and
`Assignment.comment`, the two free-text fields on the unified model.
"""

from __future__ import annotations

from rostify.core.models import Assignment
from rostify.core.schedule import Schedule

from ..base import ParamField, Rule, RuleViolation, Severity


class MaxLengthRule(Rule):
    id = "max_length"
    name = "Maximum field length"
    description = (
        "Flags position/resource codes or comments that exceed a configured "
        "length. Matches the production workbook's export-blocking check on "
        "Last Name / First Name / Location (50 chars) and shift description "
        "(100 chars)."
    )
    default_severity = Severity.HARD
    param_schema = [
        ParamField(
            name="resource_max_len",
            type="int",
            label="Max length — position/resource code",
            default=50,
            min_value=1,
            max_value=500,
        ),
        ParamField(
            name="comment_max_len",
            type="int",
            label="Max length — comment",
            default=100,
            min_value=1,
            max_value=2000,
        ),
    ]

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        resource_max = self.params["resource_max_len"]
        comment_max = self.params["comment_max_len"]

        if len(assignment.resource) > resource_max:
            violations.append(
                self.violation(
                    f"Position/resource code is {len(assignment.resource)} characters "
                    f"(max {resource_max}).",
                    assignment_id=assignment.id,
                )
            )
        if len(assignment.comment) > comment_max:
            violations.append(
                self.violation(
                    f"Comment is {len(assignment.comment)} characters (max {comment_max}).",
                    assignment_id=assignment.id,
                )
            )
        return violations
