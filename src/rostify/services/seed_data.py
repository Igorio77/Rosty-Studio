"""First-run seed data.

Position codes: copied from the real production workbook's `Abbreviation`
sheet (see reference/CASINO_SCHEDULE_MASTER_2026_V3.6.xlsb, docs/01-analysis
.md §1.1) — this is a generic game/task-type catalog, not personal data, so
it's safe to ship as-is.

Demo employees: deliberately fictional. The production workbook contains
real crew names and ids; those must never be copied into this codebase's
seed/demo data, so this module invents a handful of obviously-fake people
instead, only for local development and first-run UI testing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.templates import LocationCode, ShiftId, ShiftSegment, ShiftTiming, SubdepartmentOption, Template

_DATA_DIR = Path(__file__).parent / "data"


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


# (department, [subdepartments]) pairs matching demo_employees() exactly, so
# first-run List Control dropdowns aren't empty or out of sync with the
# seeded Staff rows.
_SEED_DEPARTMENTS = ["Casino"]
_SEED_SUBDEPARTMENTS = ["Dealers", "Supervisors", "Cashiers", "Technicians", "Hosts", "Managers"]
_SEED_POSITIONS = ["Dealer", "Pit Supervisor", "Cashier", "Technician", "Host", "Floor Manager"]


def seed_lookup_lists() -> tuple[list[str], list[SubdepartmentOption], list[str]]:
    """First-run seed for the List Control lists (Settings -> List Control)."""
    subdepartments = [SubdepartmentOption(department="Casino", name=name) for name in _SEED_SUBDEPARTMENTS]
    return list(_SEED_DEPARTMENTS), subdepartments, list(_SEED_POSITIONS)


def seed_templates() -> tuple[list[ShiftId], list[Template], list[ShiftTiming]]:
    """First-run seed for the Templates tab: a handful of Shift IDs and
    Templates for Dealers and Supervisors, so the matrix isn't empty on
    first launch. Timings loosely mirror the reference workbook's shape
    (a plain shift, a later shift, and one split shift with a long break).
    """
    shift_ids = [
        ShiftId(subdepartment="Dealers", code="1", color="blue"),
        ShiftId(subdepartment="Dealers", code="2", color="amber"),
        ShiftId(subdepartment="Dealers", code="3", color="green"),
        ShiftId(subdepartment="Supervisors", code="SUP1", color="purple"),
        ShiftId(subdepartment="Supervisors", code="SUP2", color="red"),
    ]
    dealer_ids = {s.code: s.id for s in shift_ids if s.subdepartment == "Dealers"}
    sup_ids = {s.code: s.id for s in shift_ids if s.subdepartment == "Supervisors"}

    day_9to5 = Template(subdepartment="Dealers", name="Day_9to5", color="blue")
    swing_12to8 = Template(subdepartment="Dealers", name="Swing_12to8", color="amber")
    split_am_pm = Template(subdepartment="Dealers", name="Split_AM_PM", subtitle="Long break mid-shift", color="purple")
    day_sup = Template(subdepartment="Supervisors", name="Day_Sup", color="green")
    night_sup = Template(subdepartment="Supervisors", name="Night_Sup", color="red")
    templates = [day_9to5, swing_12to8, split_am_pm, day_sup, night_sup]

    def timing(template_id: str, shift_id: str, *segments: tuple[int, int], comment: str = "") -> ShiftTiming:
        return ShiftTiming(
            template_id=template_id,
            shift_id=shift_id,
            segments=[ShiftSegment(start_minutes=s, end_minutes=e) for s, e in segments],
            comment=comment,
        )

    timings = [
        timing(day_9to5.id, dealer_ids["1"], (540, 1020)),  # 9:00-17:00
        timing(day_9to5.id, dealer_ids["2"], (540, 1020)),
        timing(day_9to5.id, dealer_ids["3"], (600, 1080)),  # 10:00-18:00
        timing(swing_12to8.id, dealer_ids["1"], (720, 1200)),  # 12:00-20:00
        timing(swing_12to8.id, dealer_ids["2"], (720, 1200)),
        timing(swing_12to8.id, dealer_ids["3"], (780, 1260)),  # 13:00-21:00
        timing(split_am_pm.id, dealer_ids["1"], (540, 780), (1020, 1260), comment="Split - long break"),
        timing(split_am_pm.id, dealer_ids["3"], (660, 1140)),  # 11:00-19:00
        timing(day_sup.id, sup_ids["SUP1"], (480, 960)),  # 8:00-16:00
        timing(day_sup.id, sup_ids["SUP2"], (540, 1020)),  # 9:00-17:00
        timing(night_sup.id, sup_ids["SUP1"], (960, 1440)),  # 16:00-24:00
        timing(night_sup.id, sup_ids["SUP2"], (1320, 1800), comment="Overnight coverage"),  # 22:00-06:00
    ]
    return shift_ids, templates, timings


def demo_assignments(on: date | None = None) -> list[Assignment]:
    """A handful of layer-SHIFT and layer-POSITION assignments for the demo
    roster, dated `on` (defaults to today) — so the Schedule tab isn't empty
    on first launch either. Deliberately small: just enough to show both
    layers and a live conflict-free example.
    """
    day = on or date.today()

    def at(hour: int, minute: int = 0) -> datetime:
        return datetime.combine(day, datetime.min.time()) + timedelta(hours=hour, minutes=minute)

    return [
        Assignment(employee_id="DEMO001", start=at(9), end=at(17), resource="1", layer=Layer.SHIFT, department="Casino"),
        Assignment(employee_id="DEMO002", start=at(9), end=at(17), resource="2", layer=Layer.SHIFT, department="Casino"),
        Assignment(employee_id="DEMO003", start=at(8), end=at(16), resource="SUP1", layer=Layer.SHIFT, department="Casino"),
        Assignment(employee_id="DEMO001", start=at(12), end=at(12, 15), resource="BR", layer=Layer.POSITION, department="Casino"),
    ]


def demo_employees() -> list[Employee]:
    """A small, obviously-fictional roster for local dev/first-run only."""
    people = [
        ("DEMO001", "Alex", "Rivera", "Dealers", "Dealer"),
        ("DEMO002", "Sam", "Okafor", "Dealers", "Dealer"),
        ("DEMO003", "Jordan", "Lindqvist", "Supervisors", "Pit Supervisor"),
        ("DEMO004", "Taylor", "Nakamura", "Cashiers", "Cashier"),
        ("DEMO005", "Morgan", "Haddad", "Technicians", "Technician"),
        ("DEMO006", "Casey", "Dubois", "Hosts", "Host"),
        ("DEMO007", "Riley", "Petrov", "Managers", "Floor Manager"),
    ]
    return [
        Employee(id=id_, first_name=first, last_name=last, subdepartment=subdept, position=pos)
        for id_, first, last, subdept, pos in people
    ]
