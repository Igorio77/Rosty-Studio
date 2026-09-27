import tempfile
from pathlib import Path

import pytest

from rostify.core.templates import PositionOption, SubdepartmentOption
from rostify.services.persistence import Repository


@pytest.fixture()
def repository():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repository(Path(tmp) / "test.db")
        yield repo
        repo.close()


def test_department_round_trip_and_rename(repository):
    repository.save_department("Casino")
    assert repository.load_departments() == ["Casino"]

    repository.rename_department("Casino", "Casino Ops")
    assert repository.load_departments() == ["Casino Ops"]

    repository.delete_department("Casino Ops")
    assert repository.load_departments() == []


def test_position_belongs_to_department(repository):
    dealer = PositionOption(department="Casino", name="Dealer")
    repository.save_position(dealer)
    repository.save_position(PositionOption(department="Housekeeping", name="Room Attendant"))

    assert [p.name for p in repository.load_positions("Casino")] == ["Dealer"]
    assert len(repository.load_positions()) == 2

    repository.save_position(PositionOption(id=dealer.id, department="Casino", name="Dealer I"))
    assert [p.name for p in repository.load_positions("Casino")] == ["Dealer I"]

    repository.delete_position(dealer.id)
    assert repository.load_positions("Casino") == []


def test_same_position_name_allowed_in_two_departments(repository):
    repository.save_position(PositionOption(department="Casino", name="Manager"))
    repository.save_position(PositionOption(department="Hotel", name="Manager"))
    assert len(repository.load_positions()) == 2


def test_renaming_department_moves_its_positions(repository):
    repository.save_department("Casino")
    repository.save_position(PositionOption(department="Casino", name="Dealer"))
    repository.rename_department("Casino", "Gaming")
    assert [p.name for p in repository.load_positions("Gaming")] == ["Dealer"]


def test_old_flat_positions_table_is_migrated():
    import sqlite3

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "old.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE departments (name TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO departments VALUES ('Casino')")
        conn.execute("CREATE TABLE positions (name TEXT PRIMARY KEY)")
        conn.executemany("INSERT INTO positions VALUES (?)", [("Dealer",), ("Supervisor",)])
        conn.commit()
        conn.close()

        repo = Repository(db)
        loaded = repo.load_positions()
        repo.close()
        assert sorted((p.department, p.name) for p in loaded) == [("Casino", "Dealer"), ("Casino", "Supervisor")]


def test_subdepartment_round_trip_and_filter_by_department(repository):
    repository.save_subdepartment(SubdepartmentOption(department="Casino", name="Dealers"))
    repository.save_subdepartment(SubdepartmentOption(department="Casino", name="Supervisors"))
    repository.save_subdepartment(SubdepartmentOption(department="Housekeeping", name="Room Attendants"))

    casino_only = repository.load_subdepartments("Casino")
    assert sorted(o.name for o in casino_only) == ["Dealers", "Supervisors"]

    everything = repository.load_subdepartments()
    assert len(everything) == 3


def test_subdepartment_edit_keeps_same_id(repository):
    option = SubdepartmentOption(department="Casino", name="Dealers")
    repository.save_subdepartment(option)

    renamed = SubdepartmentOption(id=option.id, department="Casino", name="Table Games")
    repository.save_subdepartment(renamed)

    loaded = repository.load_subdepartments("Casino")
    assert len(loaded) == 1
    assert loaded[0].name == "Table Games"


def test_subdepartment_delete(repository):
    option = SubdepartmentOption(department="Casino", name="Dealers")
    repository.save_subdepartment(option)
    repository.delete_subdepartment(option.id)
    assert repository.load_subdepartments("Casino") == []
