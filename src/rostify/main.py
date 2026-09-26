"""Entry point: wires persistence, rules, and seed data together and shows
the main window.

Data location: `ROSTIFY_DATA_DIR` env var if set, else `<project>/data` next
to `src/` — good enough for Phase 0 development. Revisit once packaging
(PyInstaller --onedir, per CLAUDE.md) needs a real per-user app-data path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from rostify.rules.registry import RuleRegistry
from rostify.services.config import build_rule_engine
from rostify.services.persistence import Repository
from rostify.services.seed_data import (
    demo_assignments,
    demo_employees,
    seed_location_codes,
    seed_lookup_lists,
    seed_templates,
)
from rostify.ui.main_window import MainWindow
from rostify.ui.theme import stylesheet


def get_data_dir() -> Path:
    override = os.environ.get("ROSTIFY_DATA_DIR")
    if override:
        return Path(override)
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "data"


def main() -> int:
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    repository = Repository(data_dir / "rostify.db")
    schedule = repository.load_schedule()

    is_first_run = not schedule.employees(active_only=False)
    if is_first_run:
        for employee in demo_employees():
            schedule.add_employee(employee)
        for assignment in demo_assignments():
            schedule.add_assignment(assignment)
        repository.save_schedule(schedule)

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

    registry = RuleRegistry()
    rules_config_path = data_dir / "rules.yaml"
    rule_engine = build_rule_engine(registry, rules_config_path)

    location_codes = repository.load_location_codes()
    if not location_codes:
        for location_code in seed_location_codes():
            repository.save_location_code(location_code)
        location_codes = repository.load_location_codes()

    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet())

    window = MainWindow(schedule, rule_engine, location_codes, repository, rules_config_path)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
