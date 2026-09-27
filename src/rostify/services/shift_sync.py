"""Keeps SHIFT-layer assignments in step with the Template timings they
came from.

A shift assignment stores its own start/end (the rule engine needs real
times), copied from the day's Template when the Shift ID was picked. Before
this module existed nothing refreshed that copy, so changing a day's
Template — or a timing in the Templates tab — left every already-assigned
shift on its old hours, and the Day view highlighted the wrong slots.

Every place that changes a day's template or a timing calls in here.
No Qt imports — see CLAUDE.md's layer boundaries.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import ShiftSegment, ShiftTiming


class ShiftError(Exception):
    """A shift that cannot be assigned; the message says why, in words the
    user can act on. `missing_timing` is set when the fix is to give the
    Shift ID a timing in the day's template — the UI offers a jump there."""

    def __init__(self, message: str, group: str = "", code: str = "", day: date | None = None,
                 missing_timing: bool = False) -> None:
        super().__init__(message)
        self.group = group
        self.code = code
        self.day = day
        self.missing_timing = missing_timing


def schedule_group(assignment: Assignment, employee: Employee | None) -> str:
    """Whose schedule a shift is on: its own `subdepartment` when set (a
    supervisor placed on the dealers' schedule), else the employee's."""
    if assignment.subdepartment:
        return assignment.subdepartment
    return employee.subdepartment if employee is not None else ""


def day_timings(repository, subdepartment: str, day: date) -> dict[str, ShiftTiming]:
    """Shift code -> timing, from the Template assigned to this
    subdepartment on this day. Empty when the day has no template."""
    template_assignment = repository.load_template_assignment(subdepartment, day)
    if template_assignment is None:
        return {}
    codes = {s.id: s.code for s in repository.load_shift_ids(subdepartment)}
    return {
        codes[t.shift_id]: t
        for t in repository.load_shift_timings(template_assignment.template_id)
        if t.segments and t.shift_id in codes
    }


def segment_times(segment: ShiftSegment, day: date) -> tuple[datetime, datetime]:
    midnight = datetime.combine(day, datetime.min.time())
    return midnight + timedelta(minutes=segment.start_minutes), midnight + timedelta(minutes=segment.end_minutes)


def timing_span(timing: ShiftTiming, day: date) -> tuple[datetime, datetime]:
    """First start to last finish — what a shift assignment stores."""
    midnight = datetime.combine(day, datetime.min.time())
    start = min(s.start_minutes for s in timing.segments)
    end = max(s.end_minutes for s in timing.segments)
    return midnight + timedelta(minutes=start), midnight + timedelta(minutes=end)


def shift_assignments(schedule: Schedule, subdepartment: str, day: date) -> list[Assignment]:
    """The SHIFT assignments on this subdepartment's schedule for the day,
    including guests from other subdepartments."""
    return [
        a
        for a in schedule.assignments(on=day, layer=Layer.SHIFT)
        if schedule_group(a, schedule.get_employee(a.employee_id)) == subdepartment
    ]


def retime_day(schedule: Schedule, repository, subdepartment: str, day: date) -> list[Assignment]:
    """Re-copy start/end from the day's current Template onto every shift on
    that schedule. A shift whose code has no timing in the new template is
    left as it was. Returns the assignments that changed."""
    timings = day_timings(repository, subdepartment, day)
    changed = []
    for assignment in shift_assignments(schedule, subdepartment, day):
        timing = timings.get(assignment.resource)
        if timing is None:
            continue
        start, end = timing_span(timing, day)
        if (assignment.start, assignment.end) != (start, end):
            assignment.start, assignment.end = start, end
            repository.save_assignment(assignment)
            changed.append(assignment)
    return changed


def retime_template(schedule: Schedule, repository, template_id: str) -> list[Assignment]:
    """After a timing in this template changed: re-time every day that
    uses it."""
    changed = []
    for template_assignment in repository.load_template_days(template_id):
        changed.extend(retime_day(schedule, repository, template_assignment.subdepartment, template_assignment.date))
    return changed


def rename_shift_code(schedule: Schedule, repository, subdepartment: str, old_code: str, new_code: str) -> int:
    """A Shift ID's code was renamed: carry every shift on that schedule
    over to the new code. Returns how many changed."""
    count = 0
    for assignment in schedule.assignments(layer=Layer.SHIFT):
        if assignment.resource != old_code:
            continue
        if schedule_group(assignment, schedule.get_employee(assignment.employee_id)) != subdepartment:
            continue
        assignment.resource = new_code
        repository.save_assignment(assignment)
        count += 1
    return count


def shift_on_day(schedule: Schedule, employee_id: str, day: date) -> Assignment | None:
    """The employee's SHIFT assignment starting on this day, if any. One
    per day: a person is on one schedule at a time."""
    matches = schedule.assignments(employee_id=employee_id, on=day, layer=Layer.SHIFT)
    return matches[0] if matches else None


def code_holder(schedule: Schedule, group: str, day: date, code: str) -> Employee | None:
    """Who already has Shift ID `code` on `group`'s schedule that day. A
    Shift ID is one person's slot: two people off are OFF1 and OFF2."""
    for assignment in shift_assignments(schedule, group, day):
        if assignment.resource == code:
            return schedule.get_employee(assignment.employee_id)
    return None


def duplicate_codes(schedule: Schedule, group: str, day: date) -> set[str]:
    """Codes held by more than one person that day — only possible in data
    entered before the one-person-per-Shift-ID check existed."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for assignment in shift_assignments(schedule, group, day):
        (duplicates if assignment.resource in seen else seen).add(assignment.resource)
    return duplicates


def assign_shift(
    schedule: Schedule, repository, employee: Employee, group: str, day: date, code: str
) -> Assignment:
    """Put the employee on shift `code` of `group`'s schedule for the day,
    timed from that day's Template. Replaces any shift they already had
    that day. Raises ShiftError (changing nothing) when the day's template
    has no timing for the code, or someone else already has it."""
    timing = day_timings(repository, group, day).get(code)
    if timing is None:
        if repository.load_template_assignment(group, day) is None:
            raise ShiftError(f"{group} has no template on {day:%a %d %b} — pick one for that day first.")
        raise ShiftError(
            f"Shift '{code}' has no timing in {group}'s template for {day:%a %d %b}.",
            group=group,
            code=code,
            day=day,
            missing_timing=True,
        )
    holder = code_holder(schedule, group, day, code)
    if holder is not None and holder.id != employee.id:
        raise ShiftError(
            f"Shift '{code}' on {day:%a %d %b} is already taken by {holder.full_name}. "
            f"A Shift ID is one person's slot — use another code (e.g. OFF1, OFF2)."
        )
    clear_shift(schedule, repository, employee.id, day)
    start, end = timing_span(timing, day)
    assignment = Assignment(
        employee_id=employee.id,
        start=start,
        end=end,
        resource=code,
        layer=Layer.SHIFT,
        department=employee.department,
        subdepartment="" if group == employee.subdepartment else group,
    )
    schedule.add_assignment(assignment)
    repository.save_assignment(assignment)
    return assignment


def clear_shift(schedule: Schedule, repository, employee_id: str, day: date) -> bool:
    existing = shift_on_day(schedule, employee_id, day)
    if existing is None:
        return False
    schedule.remove_assignment(existing.id)
    repository.delete_assignment(existing.id)
    return True


def shift_periods(repository, assignment: Assignment, group: str) -> list[tuple[datetime, datetime]]:
    """The worked periods of a shift: its template segments (a split shift
    has two), or the assignment's own span when the timing is gone."""
    day = assignment.start.date()
    timing = day_timings(repository, group, day).get(assignment.resource)
    if timing is None:
        return [(assignment.start, assignment.end)]
    return [segment_times(segment, day) for segment in timing.segments]


def hours_between(periods: list[tuple[datetime, datetime]], start: datetime, end: datetime) -> float:
    """Hours of `periods` falling between start and end."""
    total = 0.0
    for period_start, period_end in periods:
        overlap = (min(period_end, end) - max(period_start, start)).total_seconds()
        if overlap > 0:
            total += overlap / 3600
    return total


def employee_hours(schedule: Schedule, repository, employee: Employee, first: date, last: date) -> float:
    """Scheduled shift hours for the employee over first..last."""
    total = 0.0
    day = first
    while day <= last:
        shift = shift_on_day(schedule, employee.id, day)
        if shift is not None:
            periods = shift_periods(repository, shift, schedule_group(shift, employee))
            total += sum((end - start).total_seconds() for start, end in periods) / 3600
        day += timedelta(days=1)
    return total


def today_hours(schedule: Schedule, repository, employee: Employee, now: datetime) -> tuple[float, float] | None:
    """(already worked, still to go) for today's shift, or None."""
    shift = shift_on_day(schedule, employee.id, now.date())
    if shift is None:
        return None
    periods = shift_periods(repository, shift, schedule_group(shift, employee))
    far_past, far_future = datetime.min, datetime.max
    return hours_between(periods, far_past, now), hours_between(periods, now, far_future)
