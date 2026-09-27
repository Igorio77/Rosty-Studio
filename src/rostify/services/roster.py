"""Which subdepartment an employee belongs to on a given day, and moving
people between subdepartments — for a period (a Transfer) or for good.

No Qt imports — see CLAUDE.md's layer boundaries.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from rostify.core.models import Employee, Layer, Transfer
from rostify.core.schedule import Schedule


def effective_subdepartment(employee: Employee, day: date, transfers: list[Transfer]) -> str:
    """The subdepartment the employee works in that day: a transfer's, if
    one covers the day, else their own."""
    for transfer in transfers:
        if transfer.employee_id == employee.id and transfer.covers(day):
            return transfer.subdepartment
    return employee.subdepartment


def shifts_in_period(schedule: Schedule, employee_id: str, start: date, end: date) -> list:
    return [
        a
        for a in schedule.assignments(employee_id=employee_id, layer=Layer.SHIFT)
        if start <= a.start.date() <= end
    ]


def transfer_for_period(
    schedule: Schedule, repository, employee: Employee, subdepartment: str, start: date, end: date
) -> Transfer:
    """Put the employee in `subdepartment` from start to end. Their shifts
    in that period are on their old schedule's Shift IDs, which mean
    nothing on the new one, so they are removed — the caller warns first."""
    for assignment in shifts_in_period(schedule, employee.id, start, end):
        schedule.remove_assignment(assignment.id)
        repository.delete_assignment(assignment.id)
    # A new transfer replaces any overlapping one for the same person.
    for existing in repository.load_transfers():
        if existing.employee_id == employee.id and existing.start <= end and start <= existing.end:
            repository.delete_transfer(existing.id)
    transfer = Transfer(employee_id=employee.id, subdepartment=subdepartment, start=start, end=end)
    repository.save_transfer(transfer)
    return transfer


def future_shifts(schedule: Schedule, employee: Employee, from_day: date) -> list:
    """Their shifts on their own schedule from `from_day` on."""
    return [
        a
        for a in schedule.assignments(employee_id=employee.id, layer=Layer.SHIFT)
        if a.start.date() >= from_day and a.subdepartment in ("", employee.subdepartment)
    ]


def move_permanently(
    schedule: Schedule, repository, employee: Employee, subdepartment: str, from_day: date | None = None
) -> None:
    """Change the employee's own subdepartment (their position stays as it
    is). Shifts on the old schedule from `from_day` (default today) on are
    removed — those Shift IDs mean nothing on the new one — so the person
    does not linger in the old list. Earlier shifts stay, as history."""
    from_day = from_day or date.today()
    for assignment in future_shifts(schedule, employee, from_day):
        schedule.remove_assignment(assignment.id)
        repository.delete_assignment(assignment.id)
    old = employee.subdepartment
    for assignment in schedule.assignments(employee_id=employee.id, layer=Layer.SHIFT):
        if not assignment.subdepartment:
            assignment.subdepartment = old
            repository.save_assignment(assignment)
    employee.subdepartment = subdepartment
    repository.save_employee(employee)


def end_transfer(repository, employee_id: str, subdepartment: str, start: date, end: date) -> int:
    """Send the employee back home for start..end: transfers into
    `subdepartment` overlapping that range are cut back or removed."""
    changed = 0
    for transfer in repository.load_transfers():
        if transfer.employee_id != employee_id or transfer.subdepartment != subdepartment:
            continue
        if transfer.end < start or end < transfer.start:
            continue
        repository.delete_transfer(transfer.id)
        # Keep the parts outside the range.
        if transfer.start < start:
            repository.save_transfer(
                Transfer(employee_id=employee_id, subdepartment=subdepartment, start=transfer.start, end=start - timedelta(days=1))
            )
        if transfer.end > end:
            repository.save_transfer(
                Transfer(employee_id=employee_id, subdepartment=subdepartment, start=end + timedelta(days=1), end=transfer.end)
            )
        changed += 1
    return changed


def _short(day: date) -> str:
    return f"{day.day} {day.strftime('%b')}"


def describe_employee(
    schedule: Schedule,
    repository,
    employee: Employee,
    first: date,
    last: date,
    transfers: list[Transfer],
    now: datetime | None = None,
) -> str:
    """The hover text for an employee's name: who they are, where they are
    working, and their hours — for the period on screen and for today."""
    from rostify.services.shift_sync import employee_hours, today_hours

    now = now or datetime.now()
    lines = [employee.full_name]
    if employee.position:
        lines.append(employee.position)
    lines.append(f"{employee.subdepartment} · ID {employee.id}")
    for transfer in transfers:
        if transfer.employee_id == employee.id and transfer.start <= last and first <= transfer.end:
            lines.append(f"In {transfer.subdepartment} {_short(transfer.start)} – {_short(transfer.end)}")
    if employee.is_unavailable_on(now.date()):
        lines.append("Temporarily not available today")
    period = "this day" if first == last else f"{_short(first)} – {_short(last)}"
    lines.append(f"Hours {period}: {employee_hours(schedule, repository, employee, first, last):.1f}")
    today = today_hours(schedule, repository, employee, now)
    if today is not None:
        worked, to_go = today
        lines.append(f"Today: {worked:.1f} h worked, {to_go:.1f} h to go")
    return "\n".join(lines)
