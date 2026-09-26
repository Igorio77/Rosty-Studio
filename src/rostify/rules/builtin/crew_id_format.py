"""Employee id format check — ported from the xlsb's export-time check
(docs/01-analysis.md R7: Crew ID must be numeric).

Kept configurable rather than hardcoded to digits-only, since a future
customer's employee id format is exactly the kind of thing README.md's
"customizable data model" principle says shouldn't be assumed by the vendor.
"""

from __future__ import annotations

import re

from rostify.core.models import Assignment
from rostify.core.schedule import Schedule

from ..base import ParamField, Rule, RuleViolation, Severity


class CrewIdFormatRule(Rule):
    id = "crew_id_format"
    name = "Employee id format"
    description = "Flags assignments whose employee id doesn't match the configured pattern."
    default_severity = Severity.HARD
    param_schema = [
        ParamField(
            name="pattern",
            type="str",
            label="Regex pattern",
            default=r"^[0-9]+$",
            help_text="Production default is digits-only, matching the source workbook's Crew ID rule.",
        ),
    ]

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        pattern = self.params["pattern"]
        if not re.match(pattern, assignment.employee_id):
            return [
                self.violation(
                    f"Employee id '{assignment.employee_id}' does not match "
                    f"the required pattern '{pattern}'.",
                    assignment_id=assignment.id,
                )
            ]
        return []
