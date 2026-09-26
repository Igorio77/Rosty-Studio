"""Core domain models.

Departments, positions and field names are intentionally plain strings, not
fixed enums — the product's whole premise (see README.md /
reference/README_rosta_web_LEGACY.md) is a user-defined data model, not one
the vendor hardcodes. The one exception is `Layer`, which is a structural
concept from CLAUDE.md's unified model, not a business concept a user
customizes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Layer(str, Enum):
    """The two planning levels the unified Assignment model serves.

    SHIFT    = layer A — a day shift (who works when).
    POSITION = layer B — position/station rotation within a shift
               (e.g. B1 / BJ2 / BRK / FLOAT — see
               reference/abbreviation_table.json for the real code catalog).
    """

    SHIFT = "A"
    POSITION = "B"


@dataclass(slots=True)
class Employee:
    """A staff member.

    `id` is the crew/employee id used as the join key everywhere — the audit
    (docs/01-analysis.md, "Needs rework") flagged that the legacy sources
    joined on display name or loosely-typed text instead; this model doesn't
    repeat that mistake.

    Two-level org field, added when the first rule needed to know who's a
    dealer: `department` is the top-level org unit (currently always
    "Casino" — the product starts single-department, expanding to others
    like Housekeeping/F&B is a later phase). `subdepartment` is what this
    model used to call `department`: the six real crew groups from the xlsb's
    `staff data` sheet (Dealers/Supervisors/Cashiers/Technicians/Hosts/
    Managers, see docs/01-analysis.md §1.1) — rules like
    `position_rotation_eligibility` key off this field.
    """

    id: str
    first_name: str
    last_name: str
    subdepartment: str
    department: str = "Casino"
    position: str = ""
    email: str = ""
    password_hash: str = ""
    active: bool = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass(slots=True)
class Assignment:
    """One row of the unified schedule model.

    `resource` means different things depending on `layer`:
      - layer SHIFT:    a shift/template identifier (e.g. "CL1", "S1").
      - layer POSITION: a position/station code (e.g. "B3", "RW1", "OFF").
    One rule engine and one conflict detector operate on this same shape for
    both layers — see CLAUDE.md, "Two core architectural rules".
    """

    employee_id: str
    start: datetime
    end: datetime
    resource: str
    layer: Layer
    department: str = ""
    comment: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def overlaps(self, other: "Assignment") -> bool:
        """True if this assignment's time range overlaps `other`'s."""
        return self.start < other.end and other.start < self.end

    def same_day(self, other: "Assignment") -> bool:
        return self.start.date() == other.start.date()
