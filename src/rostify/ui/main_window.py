"""Main window: wires the core Schedule aggregate, the rule engine, and
persistence into Rostify's pages, navigated from a left sidebar (see
`sidebar.py` — this replaced the earlier top QTabWidget so the app's shell
matches reference/RostaStudioSchedule.jsx's look, per CLAUDE.md).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from rostify.core.schedule import Schedule
from rostify.core.templates import LocationCode
from rostify.io.exporters.csv_export import export_schedule_csv
from rostify.rules.engine import RuleEngine
from rostify.services.app_settings import AppSettings
from rostify.services.persistence import Repository

from .panels.schedule_calendar_panel import ScheduleCalendarPanel
from .panels.schedule_panel import SchedulePanel
from .panels.settings_panel import SettingsPanel
from .panels.staff_panel import StaffPanel
from .panels.templates_panel import TemplatesPanel
from .sidebar import NAV_ITEMS, Sidebar
from .theme import COLORS


class MainWindow(QMainWindow):
    def __init__(
        self,
        schedule: Schedule,
        rule_engine: RuleEngine,
        location_codes: list[LocationCode],
        repository: Repository,
        rules_config_path: Path,
        app_settings: AppSettings | None = None,
        app_settings_path: Path | None = None,
        on_appearance_change: Callable[[], None] | None = None,
    ) -> None:
        """`on_appearance_change` is called after the user picks a new mode
        or accent in Settings. The owner (main.py) applies the new theme and
        builds a fresh window, because many widgets bake their colors in at
        construction time."""
        super().__init__()
        self._app_settings = app_settings or AppSettings()
        self._set_title(self._app_settings.workspace_name)
        self.resize(1420, 820)  # +220px over the old tab-bar layout's size, to cover the sidebar's own width

        self._schedule = schedule
        self._repository = repository

        self.staff_panel = StaffPanel(schedule, repository, on_change=self._persist)
        self.templates_panel = TemplatesPanel(repository)
        self.schedule_calendar_panel = ScheduleCalendarPanel(
            schedule, repository, rule_engine=rule_engine, accent_hex=COLORS["accent"], on_change=self._persist
        )
        # Kept alive but not mounted in the sidebar/stack — the old flat
        # assignment-list audit view. The plan is a dedicated Assignments
        # Log later with its own logic; this stays only so
        # `_refresh_location_codes` below still has something to update.
        self.schedule_panel = SchedulePanel(
            schedule, rule_engine, location_codes, repository=repository, on_change=self._persist
        )
        self.settings_panel = SettingsPanel(
            rule_engine,
            rules_config_path,
            repository,
            app_settings=self._app_settings,
            app_settings_path=app_settings_path,
            on_location_codes_change=self._refresh_location_codes,
        )
        self.settings_panel.workspace_changed.connect(self._on_workspace_changed)
        if on_appearance_change is not None:
            self.settings_panel.appearance_changed.connect(lambda _mode, _accent: on_appearance_change())

        # Page order must match sidebar.NAV_ITEMS's order — that list is the
        # one place the key -> page mapping is defined.
        self.stack = QStackedWidget()
        self.stack.addWidget(self.staff_panel)
        self.stack.addWidget(self.templates_panel)
        self.stack.addWidget(self.schedule_calendar_panel)
        self.stack.addWidget(self.settings_panel)

        self.sidebar = Sidebar(icon_color=COLORS["text_secondary"], workspace_name=self._app_settings.workspace_name)
        self.sidebar.page_selected.connect(self._on_nav_selected)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.stack, stretch=1)
        self.setCentralWidget(body)

        self._build_menu()

    def _on_nav_selected(self, key: str) -> None:
        keys = [item_key for item_key, _, _ in NAV_ITEMS]
        self.stack.setCurrentIndex(keys.index(key))

    def show_page(self, key: str) -> None:
        self.sidebar.select(key)

    def current_page(self) -> str:
        return NAV_ITEMS[self.stack.currentIndex()][0]

    def _set_title(self, workspace_name: str) -> None:
        self.setWindowTitle(f"Rostify — {workspace_name}" if workspace_name else "Rostify")

    def _on_workspace_changed(self, name: str) -> None:
        self._set_title(name)
        self.sidebar.set_workspace_name(name)

    def _build_menu(self) -> None:
        menu_bar: QMenuBar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        export_action = file_menu.addAction("Export schedule to CSV…")
        export_action.triggered.connect(self._export_csv)

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export schedule to CSV", "", "CSV (*.csv)")
        if not path:
            return
        rows = export_schedule_csv(self._schedule, path)
        QMessageBox.information(self, "Export complete", f"Wrote {rows} assignment(s) to {path}")

    def _persist(self) -> None:
        self._repository.save_schedule(self._schedule)

    def _refresh_location_codes(self) -> None:
        self.schedule_panel.set_location_codes(self._repository.load_location_codes())
        self.schedule_calendar_panel.day_view.reload()
