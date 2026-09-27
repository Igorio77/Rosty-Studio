"""Schedule page: Year -> Month -> Custom -> Day, one scale switcher over
one shared idea — "what's the plan for this subdepartment on this day/
range". Reference: reference/RostaStudioSchedule.jsx's top-bar ScaleSelector.

One top row serves all four views, left to right:

    [Subdepartment] [Year | Month | Custom | Day]  [period] ........ [zoom]

The subdepartment is shared by Year, Month and Custom; the Day view shows
several subdepartments at once, so on that tab the left control becomes its
tick-list. The period controls (and zoom, for the two grids) belong to
whichever view is open. The department itself is chosen once, in
Settings -> General. Each view keeps a second row of its own below.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QStackedWidget, QTabBar, QVBoxLayout, QWidget

from rostify.core.schedule import Schedule
from rostify.rules.engine import RuleEngine
from rostify.services.app_settings import AppSettings
from rostify.services.persistence import Repository

from .calendar_views import MonthGridView, YearGridView
from .custom_view_panel import CustomViewPanel
from .day_view_panel import DayViewPanel

YEAR, MONTH, CUSTOM, DAY = range(4)

_TABS = [
    ("Year", "The whole year at a glance: which days have a template"),
    ("Month", "Assign a template to each day — drag them from the panel on the right"),
    ("Custom", "Who works which shift, over a range of days"),
    ("Day", "Position rotation for one day, slot by slot"),
]


def _date_to_qdate(day: date) -> QDate:
    return QDate(day.year, day.month, day.day)


class ScheduleCalendarPanel(QWidget):
    #: Month view's "Open in Templates": show the Templates page for this
    #: subdepartment.
    templates_requested = Signal(str)
    #: "Open in Templates" from a missing-timing message: (group, code, day).
    timing_requested = Signal(str, str, object)

    def __init__(
        self,
        schedule: Schedule,
        repository: Repository,
        rule_engine: RuleEngine | None = None,
        accent_hex: str | None = None,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
        app_settings: AppSettings | None = None,
        save_settings: Callable[[], None] | None = None,
    ) -> None:
        """`app_settings` carries the department, the remembered zoom levels
        and the Month panel's open/closed state; `save_settings` writes them
        back when they change."""
        super().__init__(parent)
        settings = app_settings or AppSettings()
        self._settings = settings
        self._save_settings = save_settings or (lambda: None)
        department = settings.department

        def remember(field: str):
            def store(value) -> None:
                setattr(settings, field, value)
                self._save_settings()
            return store

        self.year_view = YearGridView(repository, accent_hex=accent_hex)
        self.month_view = MonthGridView(
            repository,
            on_change=on_change,
            accent_hex=accent_hex,
            schedule=schedule,
            panel_open=settings.month_templates_panel,
            on_panel_toggled=remember("month_templates_panel"),
        )
        self.custom_view = CustomViewPanel(
            schedule,
            repository,
            on_change=on_change,
            zoom=settings.custom_zoom,
            on_zoom_changed=remember("custom_zoom"),
            on_open_timing=self.timing_requested.emit,
        )
        self.day_view = DayViewPanel(
            schedule,
            repository,
            rule_engine=rule_engine,
            on_change=on_change,
            zoom=settings.day_zoom,
            on_zoom_changed=remember("day_zoom"),
            department=department,
            on_open_timing=self.timing_requested.emit,
        )
        self._views = [self.year_view, self.month_view, self.custom_view, self.day_view]
        self.month_view.templates_requested.connect(self.templates_requested.emit)

        self.subdepartment_combo = QComboBox()
        self.subdepartment_combo.setToolTip("Subdepartment whose schedule is shown")
        self.subdepartment_combo.addItems([o.name for o in repository.load_subdepartments(department or None)])
        self.subdepartment_combo.currentTextChanged.connect(self._on_subdepartment_changed)

        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        for index, (label, tip) in enumerate(_TABS):
            self.tabs.addTab(label)
            self.tabs.setTabToolTip(index, tip)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.subdepartment_combo)
        header.addWidget(self.day_view.subdepartment_button)
        header.addSpacing(8)
        header.addWidget(self.tabs)
        header.addSpacing(16)
        for view in self._views:
            header.addWidget(view.period_controls)
        header.addStretch(1)
        header.addWidget(self.custom_view.zoom_control)
        header.addWidget(self.day_view.zoom_control)

        self.stack = QStackedWidget()
        for view in self._views:
            self.stack.addWidget(view)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.addLayout(header)
        layout.addWidget(self.stack, stretch=1)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.year_view.month_requested.connect(self._go_to_month)
        self.year_view.day_requested.connect(self._go_to_day)
        self.month_view.day_requested.connect(self._go_to_day)

        self._on_subdepartment_changed(self.subdepartment_combo.currentText())
        self.tabs.setCurrentIndex(MONTH)  # Month is the default landing scale, per the reference
        self._on_tab_changed(MONTH)

    # --- the old QTabWidget interface, still used by MainWindow and tools --

    def currentIndex(self) -> int:  # noqa: N802
        return self.tabs.currentIndex()

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        self.tabs.setCurrentIndex(index)

    # --- wiring ---------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for position, view in enumerate(self._views):
            view.period_controls.setVisible(position == index)
        day = index == DAY
        self.subdepartment_combo.setVisible(not day)
        self.day_view.subdepartment_button.setVisible(day)
        self.custom_view.zoom_control.setVisible(index == CUSTOM)
        self.day_view.zoom_control.setVisible(day)

    def _on_subdepartment_changed(self, name: str) -> None:
        for view in (self.year_view, self.month_view, self.custom_view):
            view.set_subdepartment(name)

    def select_subdepartment(self, name: str) -> None:
        index = self.subdepartment_combo.findText(name)
        if index >= 0:
            self.subdepartment_combo.setCurrentIndex(index)

    def _go_to_month(self, anchor: date) -> None:
        self.month_view.set_anchor(anchor)
        self.setCurrentIndex(MONTH)

    def _go_to_day(self, day: date) -> None:
        self.day_view.date_edit.setDate(_date_to_qdate(day))
        self.setCurrentIndex(DAY)
