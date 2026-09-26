import tempfile
from pathlib import Path

import pytest

from rostify.core.templates import SubdepartmentOption
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


def test_position_round_trip_and_rename(repository):
    repository.save_position("Dealer")
    repository.rename_position("Dealer", "Dealer I")
    assert repository.load_positions() == ["Dealer I"]

    repository.delete_position("Dealer I")
    assert repository.load_positions() == []


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
