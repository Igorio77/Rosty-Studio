"""First-run seed data.

Everything here fills an empty database so every page has something real
to show on first launch, for all six subdepartments.

Where each piece comes from:

* Position codes: copied from the production workbook's `Abbreviation`
  sheet (reference/CASINO_SCHEDULE_MASTER_2026_V3.6.xlsb, docs/01-analysis
  .md §1.1). A generic game/task catalog, not personal data.
* Shift IDs, Templates and their timings: `data/demo_shift_tables.json`,
  extracted once from the same workbook's per-subdepartment shift tables
  (`dst`, `sst`, `cst`, `tst`, `hstt`, `mst`). Shift times only. Cells the
  workbook left as placeholders ("test ok") or that did not parse as clean
  times were dropped during extraction.
* Headcount per subdepartment: matches the workbook's `staff data` sheet
  (Dealers 22, Supervisors 13, Cashiers 4, Technicians 9, Hosts 3,
  Managers 3).
* Employees: deliberately fictional. The workbook holds real crew names and
  ids; those must never be copied into this codebase, so names here are
  invented and ids start at 900001.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import (
    TEMPLATE_COLORS,
    LocationCode,
    ShiftId,
    ShiftSegment,
    ShiftTiming,
    SubdepartmentOption,
    Template,
    TemplateAssignment,
)

_DATA_DIR = Path(__file__).parent / "data"

DEPARTMENT = "Casino"

# (subdepartment, headcount, [positions, first one is the most common])
_SUBDEPARTMENTS = [
    ("Dealers", 22, ["Dealer", "Senior Dealer"]),
    ("Supervisors", 13, ["Pit Supervisor", "Senior Supervisor"]),
    ("Cashiers", 4, ["Cashier", "Senior Cashier"]),
    ("Technicians", 9, ["Technician", "Senior Technician"]),
    ("Hosts", 3, ["Host"]),
    ("Managers", 3, ["Casino Manager", "Assistant Casino Manager", "Floor Manager"]),
]

_FIRST_NAMES = [
    "Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
    "Avery", "Quinn", "Parker", "Rowan", "Skyler", "Reese", "Dakota", "Emerson",
    "Finley", "Harper", "Kendall", "Logan", "Micah", "Noel", "Oakley", "Peyton",
]
_LAST_NAMES = [
    "Rivera", "Okafor", "Lindqvist", "Nakamura", "Haddad", "Dubois", "Petrov",
    "Moreau", "Kowalski", "Santos", "Novak", "Eriksen", "Tanaka", "Mensah",
    "Horvat", "Castillo", "Varga", "Jansen", "Kaplan", "Silva", "Ivanova",
    "Brennan", "Oliveira", "Fischer",
]

# Position-layer demo: dealers rotate through these table codes in
# 30-minute blocks, with a break every fourth block.
_DEALER_ROTATION = ["B1", "B2", "B3", "BR"]
_ROTATION_BLOCK_MINUTES = 30
_ROTATION_HOURS = 3

# How many days of demo schedule to build, starting on this week's Monday.
_DEMO_DAYS = 14


@dataclass(slots=True)
class PositionCode:
    category: str
    task_name: str
    code: str
    entry_rule: str


def load_position_codes() -> list[PositionCode]:
    with (_DATA_DIR / "position_codes.json").open("r", encoding="utf-8") as f:
        rows = json.load(f)
    return [PositionCode(**row) for row in rows]


def seed_location_codes() -> list[LocationCode]:
    """First-run seed for the `location_codes` table, built from the same
    JSON as `load_position_codes()`, deduped by abbreviation (the JSON has
    one row per category/task, but the code is the Location ID's actual
    identity). `location_code` (the fuller "BJ-01"-style code) has no real
    source in this catalog, so it's left blank for admin to fill in.
    """
    seen: dict[str, LocationCode] = {}
    for pc in load_position_codes():
        seen.setdefault(
            pc.code, LocationCode(abbreviation=pc.code, description=pc.task_name, group=pc.category)
        )
    return list(seen.values())


def seed_lookup_lists() -> tuple[list[str], list[SubdepartmentOption], list[str]]:
    """First-run seed for the Department / Subdepartment / Position lists."""
    subdepartments = [SubdepartmentOption(department=DEPARTMENT, name=name) for name, _, _ in _SUBDEPARTMENTS]
    positions: list[str] = []
    for _, _, subdepartment_positions in _SUBDEPARTMENTS:
        positions.extend(p for p in subdepartment_positions if p not in positions)
    return [DEPARTMENT], subdepartments, positions


def _load_shift_tables() -> list[dict]:
    with (_DATA_DIR / "demo_shift_tables.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _opening_minutes(template_name: str) -> int:
    """"Open_at_3:30_PM" -> 930. Used to sort templates and to pick the
    evening ones for the demo calendar."""
    clock, meridiem = template_name.removeprefix("Open_at_").rsplit("_", 1)
    hours, minutes = (int(part) for part in clock.split(":"))
    return (hours % 12 + (12 if meridiem.upper() == "PM" else 0)) * 60 + minutes


def seed_templates() -> tuple[list[ShiftId], list[Template], list[ShiftTiming]]:
    """Shift IDs, Templates and timings for every subdepartment, from the
    workbook's shift tables."""
    shift_ids: list[ShiftId] = []
    templates: list[Template] = []
    timings: list[ShiftTiming] = []

    for table in _load_shift_tables():
        subdepartment = table["subdepartment"]
        ids_by_code: dict[str, str] = {}
        for index, code in enumerate(table["shift_codes"]):
            shift_id = ShiftId(
                subdepartment=subdepartment, code=code, color=TEMPLATE_COLORS[index % len(TEMPLATE_COLORS)]
            )
            shift_ids.append(shift_id)
            ids_by_code[code] = shift_id.id

        for index, row in enumerate(sorted(table["templates"], key=lambda t: _opening_minutes(t["name"]))):
            template = Template(
                subdepartment=subdepartment,
                name=row["name"],
                color=TEMPLATE_COLORS[index % len(TEMPLATE_COLORS)],
            )
            templates.append(template)
            for code, cell in row["timings"].items():
                timings.append(
                    ShiftTiming(
                        template_id=template.id,
                        shift_id=ids_by_code[code],
                        segments=[ShiftSegment(start_minutes=s, end_minutes=e) for s, e in cell["segments"]],
                        comment=cell["comment"],
                    )
                )
    return shift_ids, templates, timings


def demo_employees() -> list[Employee]:
    """Fictional roster sized like the workbook's `staff data` sheet."""
    employees: list[Employee] = []
    number = 0
    for subdepartment, headcount, positions in _SUBDEPARTMENTS:
        for index in range(headcount):
            first = _FIRST_NAMES[number % len(_FIRST_NAMES)]
            last = _LAST_NAMES[(number * 7) % len(_LAST_NAMES)]
            # The first person in each group gets the senior title, the
            # rest the common one — enough variety for filters to matter.
            position = positions[1] if index == 0 and len(positions) > 1 else positions[0]
            if subdepartment == "Managers":
                position = positions[index % len(positions)]
            employees.append(
                Employee(
                    id=str(900001 + number),
                    first_name=first,
                    last_name=last,
                    subdepartment=subdepartment,
                    department=DEPARTMENT,
                    position=position,
                    email=f"{first}.{last}@example.com".lower(),
                )
            )
            number += 1
    return employees


def _week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def demo_schedule(
    employees: list[Employee],
    shift_ids: list[ShiftId],
    templates: list[Template],
    timings: list[ShiftTiming],
    today: date | None = None,
) -> tuple[list[TemplateAssignment], list[Assignment]]:
    """Two weeks of plan for every subdepartment, starting this Monday.

    Each day gets one of the subdepartment's evening templates (the casino
    opens in the evening on most days), rotated day to day. Each employee
    keeps roughly the same shift slot all fortnight, so rest between shifts
    stays realistic, and takes one fixed day off per week. Today also gets
    a position rotation for the dealers, so the Day view is not empty.
    """
    today = today or date.today()
    first_day = _week_start(today)
    code_by_id = {s.id: s.code for s in shift_ids}

    template_assignments: list[TemplateAssignment] = []
    assignments: list[Assignment] = []

    for subdepartment, _, _ in _SUBDEPARTMENTS:
        people = [e for e in employees if e.subdepartment == subdepartment]
        own_templates = sorted(
            (t for t in templates if t.subdepartment == subdepartment), key=lambda t: _opening_minutes(t.name)
        )
        evening = [t for t in own_templates if _opening_minutes(t.name) >= 15 * 60] or own_templates
        if not evening:
            continue

        for day_index in range(_DEMO_DAYS):
            day = first_day + timedelta(days=day_index)
            template = evening[day_index % len(evening)]
            template_assignments.append(TemplateAssignment(subdepartment=subdepartment, date=day, template_id=template.id))

            day_timings = [t for t in timings if t.template_id == template.id and t.segments]
            day_timings.sort(key=lambda t: min(s.start_minutes for s in t.segments))
            if not day_timings:
                continue

            day_start = datetime.combine(day, datetime.min.time())
            for person_index, person in enumerate(people):
                if person_index % 7 == day_index % 7:
                    continue  # this person's weekly day off
                if person_index >= len(day_timings):
                    continue  # more people than slots on this template
                timing = day_timings[person_index]
                start = min(s.start_minutes for s in timing.segments)
                end = max(s.end_minutes for s in timing.segments)
                assignments.append(
                    Assignment(
                        employee_id=person.id,
                        start=day_start + timedelta(minutes=start),
                        end=day_start + timedelta(minutes=end),
                        resource=code_by_id[timing.shift_id],
                        layer=Layer.SHIFT,
                        department=person.department,
                    )
                )
                if subdepartment == "Dealers" and day == today:
                    assignments.extend(_dealer_rotation(person, day_start + timedelta(minutes=start), person_index))

    return template_assignments, assignments


def _dealer_rotation(person: Employee, shift_start: datetime, offset: int) -> list[Assignment]:
    """The first few hours of one dealer's shift as position-layer blocks.
    `offset` staggers dealers so they are not all on the same table."""
    blocks = []
    for block in range(_ROTATION_HOURS * 60 // _ROTATION_BLOCK_MINUTES):
        start = shift_start + timedelta(minutes=block * _ROTATION_BLOCK_MINUTES)
        blocks.append(
            Assignment(
                employee_id=person.id,
                start=start,
                end=start + timedelta(minutes=_ROTATION_BLOCK_MINUTES),
                resource=_DEALER_ROTATION[(block + offset) % len(_DEALER_ROTATION)],
                layer=Layer.POSITION,
                department=person.department,
            )
        )
    return blocks


def seed_first_run(repository, schedule: Schedule, today: date | None = None) -> None:
    """Fill an empty database with the full demo workspace. `repository` is
    a `services.persistence.Repository` (not type-hinted here only to keep
    this module importable without it)."""
    departments, subdepartments, positions = seed_lookup_lists()
    for department in departments:
        repository.save_department(department)
    for subdepartment in subdepartments:
        repository.save_subdepartment(subdepartment)
    for position in positions:
        repository.save_position(position)

    shift_ids, templates, timings = seed_templates()
    for shift_id in shift_ids:
        repository.save_shift_id(shift_id)
    for template in templates:
        repository.save_template(template)
    for timing in timings:
        repository.save_shift_timing(timing)

    employees = demo_employees()
    template_assignments, assignments = demo_schedule(employees, shift_ids, templates, timings, today)
    for employee in employees:
        schedule.add_employee(employee)
    for assignment in assignments:
        schedule.add_assignment(assignment)
    repository.save_schedule(schedule)
    for template_assignment in template_assignments:
        repository.save_template_assignment(template_assignment)
