"""Main window: wires the core Schedule aggregate, the rule engine, and
persistence into Rostify's pages, navigated from a left sidebar (see
`sidebar.py` — this replaced the earlier top QTabWidget so the app's shell
matches reference/RostaStudioSchedule.jsx's look, per CLAUDE.md).

No menu bar: the old File -> Export CSV moves to a future Print Center page
(the exporter itself stays in io/exporters/).
"""

from __future__ import annotations

from pathlib import Path

import shiboken6
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from rostify.core.schedule import Schedule
from rostify.core.templates import LocationCode
from rostify.rules.engine import RuleEngine
from rostify.services.app_settings import AppSettings, save_app_settings
from rostify.services.persistence import Repository

from .panels.schedule_calendar_panel import ScheduleCalendarPanel
from .panels.schedule_panel import SchedulePanel
from .panels.settings_panel import SettingsPanel
from .panels.staff_panel import StaffPanel
from .panels.templates_panel import TemplatesPanel
from .sidebar import NAV_ITEMS, Sidebar
from .theme import COLORS, apply_theme, stylesheet


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
    ) -> None:
        super().__init__()
        self._app_settings = app_settings or AppSettings()
        self._app_settings_path = app_settings_path
        self._set_title(self._app_settings.workspace_name)
        self.resize(1420, 820)  # +220px over the old tab-bar layout's size, to cover the sidebar's own width

        self._schedule = schedule
        self._repository = repository
        self._rule_engine = rule_engine
        self._rules_config_path = rules_config_path
        self._resolve_department()

        # Kept alive but not mounted in the sidebar/stack — the old flat
        # assignment-list audit view. The plan is a dedicated Assignments
        # Log later with its own logic; this stays only so
        # `_refresh_location_codes` below still has something to update.
        self.schedule_panel = SchedulePanel(
            schedule, rule_engine, location_codes, repository=repository, on_change=self._persist
        )

        self._build_body()

    def _resolve_department(self) -> None:
        """The workspace plans one department (Settings -> General). Fall
        back to the first one in Settings -> Lists when none is saved or the
        saved one was removed."""
        departments = self._repository.load_departments()
        if departments and self._app_settings.department not in departments:
            self._app_settings.department = departments[0]

    def _build_body(self) -> None:
        """Sidebar plus every page. Built once at start, and again after a
        theme or department switch — many widgets bake their colors in when
        they are built, so rebuilding them is the one reliable way to
        repaint everything. The window itself stays open, so it does not
        move, resize or flash."""
        department = self._app_settings.department
        self.staff_panel = StaffPanel(
            self._schedule,
            self._repository,
            on_change=self._persist,
            department=department,
            zoom=self._app_settings.team_zoom,
            on_zoom_changed=lambda zoom: self._remember("team_zoom", zoom),
        )
        self.templates_panel = TemplatesPanel(
            self._repository,
            self._schedule,
            on_change=self._persist,
            department=department,
            zoom=self._app_settings.templates_zoom,
            on_zoom_changed=lambda zoom: self._remember("templates_zoom", zoom),
        )
        self.schedule_calendar_panel = ScheduleCalendarPanel(
            self._schedule,
            self._repository,
            rule_engine=self._rule_engine,
            accent_hex=COLORS["accent"],
            on_change=self._persist,
            app_settings=self._app_settings,
            save_settings=self._save_settings,
        )
        self.schedule_calendar_panel.templates_requested.connect(self._open_templates)
        self.schedule_calendar_panel.timing_requested.connect(self._open_timing)
        self.settings_panel = SettingsPanel(
            self._rule_engine,
            self._rules_config_path,
            self._repository,
            app_settings=self._app_settings,
            app_settings_path=self._app_settings_path,
            on_location_codes_change=self._refresh_location_codes,
        )
        self.settings_panel.workspace_changed.connect(self._on_workspace_changed)
        self.settings_panel.appearance_changed.connect(self._on_rebuild_needed)
        self.settings_panel.department_changed.connect(self._on_rebuild_needed)

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

    def _remember(self, field: str, value) -> None:
        setattr(self._app_settings, field, value)
        self._save_settings()

    def _save_settings(self) -> None:
        if self._app_settings_path is not None:
            save_app_settings(self._app_settings_path, self._app_settings)

    def _open_templates(self, subdepartment: str) -> None:
        self.templates_panel.select_subdepartment(subdepartment)
        self.show_page("templates")

    def _open_timing(self, group: str, code: str, day) -> None:
        """Jump to a Shift ID's timing in that day's template, ready to set."""
        self.show_page("templates")
        self.templates_panel.open_timing(group, code, day)

    def _on_rebuild_needed(self, *_args) -> None:
        # Deferred: this runs inside a click on a widget that the rebuild
        # is about to delete.
        QTimer.singleShot(0, self._rebuild_body)

    def _rebuild_body(self) -> None:
        page = self.current_page()
        category = self.settings_panel.current_category()
        schedule_tab = self.schedule_calendar_panel.currentIndex()

        self.setUpdatesEnabled(False)
        try:
            # Delete the old pages *before* the new stylesheet goes in, so Qt
            # doesn't spend time restyling widgets that are about to go.
            old = self.takeCentralWidget()
            if old is not None:
                shiboken6.delete(old)
            apply_theme(self._app_settings.theme_mode, self._app_settings.accent)
            QApplication.instance().setStyleSheet(stylesheet())
            self._resolve_department()
            self._build_body()
            self.schedule_calendar_panel.setCurrentIndex(schedule_tab)
            self.settings_panel.select_category(category)
            self.show_page(page)
        finally:
            self.setUpdatesEnabled(True)

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

    def _persist(self) -> None:
        self._repository.save_schedule(self._schedule)

    def _refresh_location_codes(self) -> None:
        self.schedule_panel.set_location_codes(self._repository.load_location_codes())
        self.schedule_calendar_panel.day_view.reload()
