import tempfile
from datetime import date
from pathlib import Path

import pytest

from rostify.core.models import Layer
from rostify.services.app_settings import AppSettings, load_app_settings, save_app_settings
from rostify.services.persistence import Repository
from rostify.services.seed_data import demo_employees, seed_first_run, seed_templates


@pytest.fixture()
def repository():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repository(Path(tmp) / "test.db")
        yield repo
        repo.close()


def test_demo_roster_matches_workbook_headcount():
    counts: dict[str, int] = {}
    for employee in demo_employees():
        counts[employee.subdepartment] = counts.get(employee.subdepartment, 0) + 1
    assert counts == {"Dealers": 22, "Supervisors": 13, "Cashiers": 4, "Technicians": 9, "Hosts": 3, "Managers": 3}


def test_demo_ids_are_numeric_and_unique():
    ids = [e.id for e in demo_employees()]
    assert len(ids) == len(set(ids))
    assert all(i.isdigit() for i in ids)


def test_every_subdepartment_gets_templates_with_valid_timings():
    shift_ids, templates, timings = seed_templates()
    subdepartments = {t.subdepartment for t in templates}
    assert subdepartments == {"Dealers", "Supervisors", "Cashiers", "Technicians", "Hosts", "Managers"}
    for timing in timings:
        assert timing.segments
        for segment in timing.segments:
            assert 0 <= segment.start_minutes < segment.end_minutes


def test_seed_first_run_fills_every_page(repository):
    schedule = repository.load_schedule()
    seed_first_run(repository, schedule, today=date(2026, 9, 26))

    reloaded = repository.load_schedule()
    assert len(reloaded.employees()) == 54
    assert len(repository.load_subdepartments()) == 6
    shifts = reloaded.assignments(layer=Layer.SHIFT)
    assert {reloaded.get_employee(a.employee_id).subdepartment for a in shifts} == {
        "Dealers", "Supervisors", "Cashiers", "Technicians", "Hosts", "Managers"
    }
    assert reloaded.assignments(layer=Layer.POSITION)
    assert repository.load_template_assignment("Hosts", date(2026, 9, 21)) is not None


def test_app_settings_round_trip_and_bad_values_fall_back(tmp_path):
    path = tmp_path / "app.yaml"
    assert load_app_settings(path) == AppSettings()

    save_app_settings(path, AppSettings(theme_mode="light", accent="rose", workspace_name="Ship A"))
    assert load_app_settings(path) == AppSettings(theme_mode="light", accent="rose", workspace_name="Ship A")

    path.write_text("theme_mode: sepia\naccent: neon\nworkspace_name: ''\n", encoding="utf-8")
    assert load_app_settings(path) == AppSettings()
