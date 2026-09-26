"""Position-rotation eligibility.

In this domain, layer B (Position — table rotation) is only ever given by a
supervisor to a dealer being moved table-to-table, or put on break — not to
supervisors, cashiers, technicians, managers or hosts. Scoped to layer
POSITION only; layer SHIFT assignments are unaffected.

The allowed list is a param, not a hardcoded check against "Dealers", so it
stays correct once `Employee.department`/`subdepartment` grows beyond a
single Casino department (see core/models.py).
"""

from __future__ import annotations

from rostify.core.models import Assignment, Layer
from rostify.core.schedule import Schedule

from ..base import ParamField, Rule, RuleViolation, Severity


class PositionRotationEligibilityRule(Rule):
    id = "position_rotation_eligibility"
    name = "Position rotation eligibility"
    description = (
        "Flags a Position-layer (table rotation) assignment given to an "
        "employee outside the allowed subdepartments."
    )
    default_severity = Severity.HARD
    param_schema = [
        ParamField(
            name="allowed_subdepartments",
            type="str",
            label="Allowed subdepartments (comma-separated)",
            default="Dealers",
            help_text="Only employees in these subdepartments may receive rotation/position assignments.",
        ),
    ]

    def evaluate(self, assignment: Assignment, schedule: Schedule) -> list[RuleViolation]:
        if assignment.layer != Layer.POSITION:
            return []

        allowed = {s.strip() for s in self.params["allowed_subdepartments"].split(",") if s.strip()}
        employee = schedule.get_employee(assignment.employee_id)
        if employee is None or employee.subdepartment in allowed:
            return []

        return [
            self.violation(
                f"{employee.full_name} is in subdepartment '{employee.subdepartment}', "
                f"not eligible for a position/rotation assignment "
                f"(allowed: {', '.join(sorted(allowed))}).",
                assignment_id=assignment.id,
            )
        ]
