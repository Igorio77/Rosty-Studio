import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.templates import LocationCode, ShiftId, ShiftSegment, ShiftTiming, Template, TemplateAssignment
from rostify.services.persistence import Repository


@pytest.fixture()
def repository():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repository(Path(tmp) / "test.db")
        yield repo
        repo.close()


def test_shift_id_round_trip(repository):
    shift_id = ShiftId(subdepartment="Dealers", code="CL1")
    repository.save_shift_id(shift_id)

    loaded = repository.load_shift_ids("Dealers")
    assert len(loaded) == 1
    assert loaded[0].id == shift_id.id
    assert loaded[0].code == "CL1"

    # a different subdepartment sees nothing
    assert repository.load_shift_ids("Supervisors") == []


def test_template_round_trip(repository):
    template = Template(subdepartment="Dealers", name="Open_at_9:00_AM", subtitle="Morning", color="amber")
    repository.save_template(template)

    loaded = repository.load_templates("Dealers")
    assert len(loaded) == 1
    assert loaded[0].name == "Open_at_9:00_AM"
    assert loaded[0].subtitle == "Morning"
    assert loaded[0].color == "amber"


def test_template_color_defaults_to_blue(repository):
    template = Template(subdepartment="Dealers", name="No color set")
    repository.save_template(template)
    assert repository.load_templates("Dealers")[0].color == "blue"


def test_shift_timing_round_trip_with_overnight_segment(repository):
    shift_id = ShiftId(subdepartment="Dealers", code="4")
    template = Template(subdepartment="Dealers", name="Open_at_9:00_AM")
    repository.save_shift_id(shift_id)
    repository.save_template(template)

    timing = ShiftTiming(
        template_id=template.id,
        shift_id=shift_id.id,
        segments=[
            ShiftSegment(start_minutes=9 * 60, end_minutes=13 * 60),
            ShiftSegment(start_minutes=23 * 60, end_minutes=26 * 60),  # 11pm - 2am next day
        ],
        comment="split shift",
    )
    repository.save_shift_timing(timing)

    loaded = repository.load_shift_timings(template.id)
    assert len(loaded) == 1
    assert loaded[0].comment == "split shift"
    assert len(loaded[0].segments) == 2
    assert loaded[0].segments[1].end_minutes == 26 * 60


def test_deleting_template_cascades_its_timings(repository):
    shift_id = ShiftId(subdepartment="Dealers", code="1")
    template = Template(subdepartment="Dealers", name="Open_at_9:00_AM")
    repository.save_shift_id(shift_id)
    repository.save_template(template)
    repository.save_shift_timing(
        ShiftTiming(template_id=template.id, shift_id=shift_id.id, segments=[ShiftSegment(540, 1020)])
    )

    repository.delete_template(template.id)

    assert repository.load_templates("Dealers") == []
    assert repository.load_shift_timings(template.id) == []


def test_location_code_round_trip(repository):
    repository.save_location_code(
        LocationCode(abbreviation="B1", location_code="BJ-01", description="Gaming Position", group="Blackjack")
    )
    repository.save_location_code(LocationCode(abbreviation="F1", location_code="FN-01", group="Fantan"))

    loaded = repository.load_location_codes()
    assert [lc.abbreviation for lc in loaded] == ["B1", "F1"]
    assert loaded[0].location_code == "BJ-01"
    assert loaded[0].description == "Gaming Position"
    assert loaded[0].group == "Blackjack"

    repository.delete_location_code("B1")
    assert [lc.abbreviation for lc in repository.load_location_codes()] == ["F1"]


def test_delete_assignment(repository):
    employee = Employee(id="E1", first_name="Alex", last_name="Rivera", subdepartment="Dealers")
    repository.save_employee(employee)
    assignment = Assignment(
        employee_id="E1", start=datetime(2026, 1, 1, 9), end=datetime(2026, 1, 1, 17), resource="1", layer=Layer.SHIFT
    )
    repository.save_assignment(assignment)
    assert len(repository.load_assignments()) == 1

    repository.delete_assignment(assignment.id)
    assert repository.load_assignments() == []


def test_template_assignment_round_trip(repository):
    template = Template(subdepartment="Dealers", name="Day_9to5")
    repository.save_template(template)

    ta = TemplateAssignment(subdepartment="Dealers", date=date(2026, 9, 25), template_id=template.id)
    repository.save_template_assignment(ta)

    loaded = repository.load_template_assignment("Dealers", date(2026, 9, 25))
    assert loaded is not None
    assert loaded.template_id == template.id

    assert repository.load_template_assignment("Dealers", date(2026, 9, 26)) is None
    assert repository.load_template_assignment("Supervisors", date(2026, 9, 25)) is None


def test_template_assignment_range_and_overwrite_and_delete(repository):
    day_template = Template(subdepartment="Dealers", name="Day_9to5")
    swing_template = Template(subdepartment="Dealers", name="Swing_12to8")
    repository.save_template(day_template)
    repository.save_template(swing_template)

    repository.save_template_assignment(TemplateAssignment(subdepartment="Dealers", date=date(2026, 9, 25), template_id=day_template.id))
    repository.save_template_assignment(TemplateAssignment(subdepartment="Dealers", date=date(2026, 9, 26), template_id=swing_template.id))

    in_range = repository.load_template_assignments_range("Dealers", date(2026, 9, 25), date(2026, 9, 26))
    assert [ta.template_id for ta in in_range] == [day_template.id, swing_template.id]

    # overwrite the first day's plan
    repository.save_template_assignment(TemplateAssignment(subdepartment="Dealers", date=date(2026, 9, 25), template_id=swing_template.id))
    assert repository.load_template_assignment("Dealers", date(2026, 9, 25)).template_id == swing_template.id

    repository.delete_template_assignment("Dealers", date(2026, 9, 25))
    assert repository.load_template_assignment("Dealers", date(2026, 9, 25)) is None
