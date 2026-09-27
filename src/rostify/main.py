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
from rostify.services.app_settings import load_app_settings
from rostify.services.config import build_rule_engine
from rostify.services.persistence import Repository
from rostify.services.seed_data import seed_first_run, seed_location_codes
from rostify.ui.main_window import MainWindow
from rostify.ui.theme import apply_theme, stylesheet


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

    if not schedule.employees(active_only=False):
        seed_first_run(repository, schedule)

    registry = RuleRegistry()
    rules_config_path = data_dir / "rules.yaml"
    rule_engine = build_rule_engine(registry, rules_config_path)

    location_codes = repository.load_location_codes()
    if not location_codes:
        for location_code in seed_location_codes():
            repository.save_location_code(location_code)
        location_codes = repository.load_location_codes()

    app_settings_path = data_dir / "app.yaml"
    app_settings = load_app_settings(app_settings_path)

    app = QApplication(sys.argv)
    apply_theme(app_settings.theme_mode, app_settings.accent)
    app.setStyleSheet(stylesheet())

    # A theme switch later on is handled inside the window itself
    # (MainWindow._rebuild_for_theme), so it never closes and reopens.
    window = MainWindow(
        schedule,
        rule_engine,
        location_codes,
        repository,
        rules_config_path,
        app_settings=app_settings,
        app_settings_path=app_settings_path,
    )
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
