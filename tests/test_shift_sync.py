import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import (
    CellNote,
    ShiftId,
    ShiftSegment,
    ShiftTiming,
    Template,
    TemplateAssignment,
    natural_key,
)
from rostify.services.persistence import Repository
from rostify.services.shift_sync import rename_shift_code, retime_day, retime_template

DAY = date(2026, 9, 26)


@pytest.fixture()
def setup():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repository(Path(tmp) / "test.db")
        schedule = Schedule()
        schedule.add_employee(Employee(id="E1", first_name="A", last_name="B", subdepartment="Dealers"))
        schedule.add_employee(Employee(id="S1", first_name="C", last_name="D", subdepartment="Supervisors"))
        repo.save_schedule(schedule)  # assignments reference employees in the database
        shift = ShiftId(subdepartment="Dealers", code="1")
        repo.save_shift_id(shift)
        early = Template(subdepartment="Dealers", name="Early")
        late = Template(subdepartment="Dealers", name="Late")
        repo.save_template(early)
        repo.save_template(late)
        repo.save_shift_timing(ShiftTiming(template_id=early.id, shift_id=shift.id, segments=[ShiftSegment(600, 900)]))
        repo.save_shift_timing(ShiftTiming(template_id=late.id, shift_id=shift.id, segments=[ShiftSegment(1080, 1500)]))
        repo.save_template_assignment(TemplateAssignment(subdepartment="Dealers", date=DAY, template_id=early.id))
        yield repo, schedule, shift, early, late
        repo.close()


def _shift(employee_id, subdepartment=""):
    return Assignment(
        employee_id=employee_id,
        start=datetime(2026, 9, 26, 10),
        end=datetime(2026, 9, 26, 15),
        resource="1",
        layer=Layer.SHIFT,
        subdepartment=subdepartment,
    )


def test_changing_the_day_template_retimes_its_shifts(setup):
    repo, schedule, _, _, late = setup
    dealer = _shift("E1")
    guest = _shift("S1", subdepartment="Dealers")  # a supervisor on the dealers' schedule
    schedule.add_assignment(dealer)
    schedule.add_assignment(guest)

    repo.save_template_assignment(TemplateAssignment(subdepartment="Dealers", date=DAY, template_id=late.id))
    changed = retime_day(schedule, repo, "Dealers", DAY)

    assert len(changed) == 2
    assert dealer.start == datetime(2026, 9, 26, 18)
    assert dealer.end == datetime(2026, 9, 27, 1)
    assert guest.start == datetime(2026, 9, 26, 18)


def test_editing_a_timing_retimes_every_day_that_uses_it(setup):
    repo, schedule, shift, early, _ = setup
    dealer = _shift("E1")
    schedule.add_assignment(dealer)

    repo.save_shift_timing(
        ShiftTiming(
            id=repo.load_shift_timings(early.id)[0].id,
            template_id=early.id,
            shift_id=shift.id,
            segments=[ShiftSegment(540, 1020)],
        )
    )
    retime_template(schedule, repo, early.id)
    assert dealer.start == datetime(2026, 9, 26, 9)
    assert dealer.end == datetime(2026, 9, 26, 17)


def test_supervisor_on_own_schedule_is_left_alone(setup):
    repo, schedule, _, _, late = setup
    own = _shift("S1")  # Supervisors schedule, not Dealers
    schedule.add_assignment(own)
    repo.save_template_assignment(TemplateAssignment(subdepartment="Dealers", date=DAY, template_id=late.id))
    assert retime_day(schedule, repo, "Dealers", DAY) == []
    assert own.start == datetime(2026, 9, 26, 10)


def test_renaming_a_shift_code_carries_assignments(setup):
    repo, schedule, _, _, _ = setup
    dealer = _shift("E1")
    schedule.add_assignment(dealer)
    assert rename_shift_code(schedule, repo, "Dealers", "1", "1A") == 1
    assert dealer.resource == "1A"


def test_natural_sort():
    assert sorted(["10", "2", "CL10", "CL2", "1"], key=natural_key) == ["1", "2", "10", "CL2", "CL10"]


def test_unavailable_period_and_archive_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repository(Path(tmp) / "t.db")
        employee = Employee(
            id="E9",
            first_name="X",
            last_name="Y",
            subdepartment="Dealers",
            active=False,
            unavailable_from=date(2026, 10, 1),
            unavailable_to=date(2026, 10, 5),
        )
        repo.save_employee(employee)
        loaded = repo.load_employees()[0]
        repo.close()
    assert loaded.archived
    assert loaded.is_unavailable_on(date(2026, 10, 3))
    assert not loaded.is_unavailable_on(date(2026, 10, 6))


def test_cell_notes_and_orders_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repository(Path(tmp) / "t.db")
        at = datetime(2026, 9, 26, 10, 15)
        repo.save_cell_note(CellNote(employee_id="E1", at=at, text="late"))
        assert repo.load_cell_notes(datetime(2026, 9, 26), datetime(2026, 9, 27))[0].text == "late"
        repo.delete_cell_note("E1", at)
        assert repo.load_cell_notes(datetime(2026, 9, 26), datetime(2026, 9, 27)) == []

        repo.save_day_row_order("Dealers", DAY, ["E3", "E1", "E2"])
        assert repo.load_day_row_order("Dealers", DAY) == ["E3", "E1", "E2"]
        repo.save_employee_order("Dealers", ["E2", "E1"])
        assert repo.load_employee_order("Dealers") == ["E2", "E1"]
        repo.close()


def test_assign_guest_shift_and_replace(setup):
    from rostify.services.shift_sync import assign_shift, shift_on_day

    repo, schedule, _, _, _ = setup
    supervisor = schedule.get_employee("S1")
    placed = assign_shift(schedule, repo, supervisor, "Dealers", DAY, "1")
    assert placed is not None and placed.subdepartment == "Dealers"
    assert placed.start == datetime(2026, 9, 26, 10)
    from rostify.services.shift_sync import ShiftError

    with pytest.raises(ShiftError):
        assign_shift(schedule, repo, supervisor, "Dealers", DAY, "NOPE")
    assert shift_on_day(schedule, "S1", DAY) is placed


def test_a_shift_id_is_one_persons_slot(setup):
    from rostify.services.shift_sync import ShiftError, assign_shift

    repo, schedule, _, _, _ = setup
    assign_shift(schedule, repo, schedule.get_employee("E1"), "Dealers", DAY, "1")
    with pytest.raises(ShiftError, match="already taken"):
        assign_shift(schedule, repo, schedule.get_employee("S1"), "Dealers", DAY, "1")
    # Re-assigning the same person to their own code is fine.
    assign_shift(schedule, repo, schedule.get_employee("E1"), "Dealers", DAY, "1")


def test_transfer_for_a_period_and_back(setup):
    from datetime import timedelta

    from rostify.services.roster import effective_subdepartment, end_transfer, transfer_for_period

    repo, schedule, _, _, _ = setup
    supervisor = schedule.get_employee("S1")
    transfer_for_period(schedule, repo, supervisor, "Dealers", DAY, DAY + timedelta(days=6))
    transfers = repo.load_transfers()
    assert effective_subdepartment(supervisor, DAY + timedelta(days=3), transfers) == "Dealers"
    assert effective_subdepartment(supervisor, DAY + timedelta(days=7), transfers) == "Supervisors"

    end_transfer(repo, "S1", "Dealers", DAY + timedelta(days=2), DAY + timedelta(days=3))
    transfers = repo.load_transfers()
    assert effective_subdepartment(supervisor, DAY + timedelta(days=2), transfers) == "Supervisors"
    assert effective_subdepartment(supervisor, DAY + timedelta(days=5), transfers) == "Dealers"


def test_move_permanently_keeps_old_shifts_on_old_schedule(setup):
    from rostify.services.roster import move_permanently
    from rostify.services.shift_sync import schedule_group

    repo, schedule, _, _, _ = setup
    past = _shift("S1")  # on DAY
    later = _shift("S1")
    later.start, later.end = datetime(2026, 9, 28, 10), datetime(2026, 9, 28, 15)
    schedule.add_assignment(past)
    schedule.add_assignment(later)
    supervisor = schedule.get_employee("S1")
    position = supervisor.position
    move_permanently(schedule, repo, supervisor, "Dealers", from_day=date(2026, 9, 27))
    assert supervisor.subdepartment == "Dealers"
    assert supervisor.position == position
    assert schedule_group(past, supervisor) == "Supervisors"  # history stays on the old schedule
    assert schedule.assignment(later.id) is None  # from the move on: removed


def test_hours(setup):
    from rostify.services.shift_sync import assign_shift, employee_hours, today_hours

    repo, schedule, _, _, _ = setup
    dealer = schedule.get_employee("E1")
    assign_shift(schedule, repo, dealer, "Dealers", DAY, "1")  # 10:00-15:00
    assert employee_hours(schedule, repo, dealer, DAY, DAY) == 5.0
    worked, to_go = today_hours(schedule, repo, dealer, datetime(2026, 9, 26, 12))
    assert (worked, to_go) == (2.0, 3.0)
