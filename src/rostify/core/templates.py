"""Scheduling template data: Templates, Shift IDs and their timings, plus
the Location ID catalog.

This is the layer above a single `Assignment` (core/models.py): a Template
is a named day-plan for one subdepartment (e.g. "Open_at_9:00_AM" for
Dealers); a Shift ID (e.g. "1", "CL1") is a slot identity shared by *every*
template in that subdepartment; a ShiftTiming is one (template, shift id)
cell — the actual Start/Finish segment(s), since a shift can be split.

None of this replaces Assignment/Schedule — a Shift ID's timing is layer A
(SHIFT) material, and turning "employee X takes shift id 4 on 2026-09-25"
into a real Assignment row is future work (the Custom view). LocationCode
is layer B (POSITION) material: the admin-editable catalog that used to be
a frozen JSON seed (services/seed_data.py's position_codes.json) — kept
here because it's scheduling master data of the same kind, not a business
rule and not part of the Employee/Assignment shape.

No Qt imports here — see CLAUDE.md's layer boundaries.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class ShiftSegment:
    """One Start/Finish pair within a shift's timing. A shift with two
    segments is a split shift (e.g. work, long break, work again).

    Both values are minutes since the template-day's midnight. `end_minutes`
    is allowed to exceed 1440 to mean "runs into the next day" (e.g. an
    11:00 PM - 2:00 AM segment is start=1380, end=1560) — no separate
    overnight flag needed.
    """

    start_minutes: int
    end_minutes: int


#: Fixed 5-color palette for template chips and shift badges (per
#: reference/RostaStudioSchedule.jsx's TEMPLATE_COLORS) — a closed set, not
#: free-text, so calendar/badge legends stay readable.
TEMPLATE_COLORS = ["blue", "green", "amber", "red", "purple"]


@dataclass(slots=True)
class ShiftId:
    """A slot identity (e.g. "1", "4", "CL1"), scoped to one subdepartment
    and shared by every Template in it — adding one adds a column to every
    template's matrix row at once. `color` is its own badge color (the
    reference gives each shift its own color, independent of the template
    it's timed under — the Custom view's shift badge uses this, not the
    template's color).
    """

    subdepartment: str
    code: str
    color: str = "blue"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(slots=True)
class Template:
    """A named day-plan, scoped to one subdepartment (e.g. "Open_at_9:00_AM"
    for Dealers). `color` is one of TEMPLATE_COLORS — cosmetic only, used to
    tell templates apart at a glance on the Month/Year calendar."""

    subdepartment: str
    name: str
    subtitle: str = ""
    color: str = "blue"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(slots=True)
class ShiftTiming:
    """One matrix cell: this Template's timing for one ShiftId."""

    template_id: str
    shift_id: str
    segments: list[ShiftSegment] = field(default_factory=list)
    comment: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(slots=True)
class LocationCode:
    """Admin-editable catalog entry. Four distinct fields, confirmed by the
    domain expert as genuinely separate (not two names for one value):

      abbreviation   short code, e.g. "B1" — the primary key, and what a
                     future Day-view grid cell actually lets a supervisor
                     pick (has to fit a ~5-character cell) — it's what an
                     Assignment's `resource` field holds on layer POSITION.
      location_code  fuller code, e.g. "BJ-01".
      description    e.g. "Gaming Position".
      group          e.g. "Blackjack".
    """

    abbreviation: str
    location_code: str = ""
    description: str = ""
    group: str = ""


@dataclass(slots=True)
class SubdepartmentOption:
    """One entry in the admin-managed Subdepartment list (Settings ->
    List Control), scoped to a Department so the Staff/Templates dropdowns
    can cascade Department -> Subdepartment."""

    department: str
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(slots=True)
class TemplateAssignment:
    """Which Template is "the plan" for one subdepartment on one calendar
    day — the Custom view's "one Template per subdepartment per day" rule.
    Picking a day's Template is what makes its Shift IDs (and their
    Template-defined timings) available to assign employees onto that day;
    an actual employee-to-Shift-ID pick becomes a real SHIFT-layer
    Assignment (core/models.py), not a field on this class — this only
    records the day's plan, not who's on it.
    """

    subdepartment: str
    date: date
    template_id: str
