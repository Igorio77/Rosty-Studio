from datetime import datetime

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule


def make_assignment(employee_id="E1", start_hour=8, end_hour=16, layer=Layer.SHIFT, resource="S1"):
    return Assignment(
        employee_id=employee_id,
        start=datetime(2026, 1, 1, start_hour),
        end=datetime(2026, 1, 1, end_hour),
        resource=resource,
        layer=layer,
    )


def test_overlaps_true_for_overlapping_ranges():
    a = make_assignment(start_hour=8, end_hour=16)
    b = make_assignment(start_hour=14, end_hour=20)
    assert a.overlaps(b)
    assert b.overlaps(a)


def test_overlaps_false_for_adjacent_ranges():
    a = make_assignment(start_hour=8, end_hour=16)
    b = make_assignment(start_hour=16, end_hour=20)
    assert not a.overlaps(b)


def test_schedule_add_and_query_employee():
    schedule = Schedule()
    employee = Employee(id="E1", first_name="Alex", last_name="Rivera", subdepartment="Dealers")
    schedule.add_employee(employee)
    assert schedule.get_employee("E1") is employee
    assert schedule.employees() == [employee]


def test_schedule_remove_employee():
    schedule = Schedule()
    employee = Employee(id="E1", first_name="Alex", last_name="Rivera", subdepartment="Dealers")
    schedule.add_employee(employee)

    schedule.remove_employee("E1")

    assert schedule.get_employee("E1") is None
    assert schedule.employees(active_only=False) == []


def test_schedule_remove_employee_missing_id_is_a_noop():
    schedule = Schedule()
    schedule.remove_employee("does-not-exist")  # must not raise


def test_schedule_overlapping_only_matches_same_employee_and_layer():
    schedule = Schedule()
    a1 = make_assignment(employee_id="E1", start_hour=8, end_hour=16, layer=Layer.SHIFT)
    a2 = make_assignment(employee_id="E1", start_hour=10, end_hour=12, layer=Layer.SHIFT)
    a3 = make_assignment(employee_id="E2", start_hour=10, end_hour=12, layer=Layer.SHIFT)
    a4 = make_assignment(employee_id="E1", start_hour=10, end_hour=12, layer=Layer.POSITION)

    schedule.add_assignment(a1)
    schedule.add_assignment(a3)
    schedule.add_assignment(a4)

    clashes = schedule.overlapping(a2)
    assert clashes == [a1]


def test_schedule_query_by_date_and_layer():
    schedule = Schedule()
    shift = make_assignment(layer=Layer.SHIFT)
    position = make_assignment(layer=Layer.POSITION)
    schedule.add_assignment(shift)
    schedule.add_assignment(position)

    assert schedule.assignments(layer=Layer.SHIFT) == [shift]
    assert schedule.assignments(on=shift.start.date()) == [shift, position]
