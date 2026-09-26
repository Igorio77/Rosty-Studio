"""Schedule page: Year -> Month -> Custom -> Day, one scale switcher over
one shared idea — "what's the plan for this subdepartment on this day/
range". Reference: reference/RostaStudioSchedule.jsx's top-bar ScaleSelector
(Year/Month/Week/Day/Custom) — "Week" is dropped here since Rostify's
existing Custom view (a date-range roster grid) already covers picking an
arbitrary period, per the user's own call.

Year and Month are new (`calendar_views.py`); Custom and Day are the
already-built CustomViewPanel/DayViewPanel, reused unchanged — this panel
only hosts them and wires Year/Month's drill-down clicks to jump scale.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QTabWidget, QWidget

from rostify.core.schedule import Schedule
from rostify.rules.engine import RuleEngine
from rostify.services.persistence import Repository

from ..theme import COLORS
from .calendar_views import MonthGridView, YearGridView
from .custom_view_panel import CustomViewPanel
from .day_view_panel import DayViewPanel

YEAR, MONTH, CUSTOM, DAY = range(4)


def _date_to_qdate(day: date) -> QDate:
    return QDate(day.year, day.month, day.day)


class ScheduleCalendarPanel(QTabWidget):
    def __init__(
        self,
        schedule: Schedule,
        repository: Repository,
        rule_engine: RuleEngine | None = None,
        accent_hex: str | None = None,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.year_view = YearGridView(repository, accent_hex=accent_hex)
        self.month_view = MonthGridView(repository, on_change=on_change, accent_hex=accent_hex)
        self.custom_view = CustomViewPanel(schedule, repository, on_change=on_change)
        self.day_view = DayViewPanel(schedule, repository, rule_engine=rule_engine, on_change=on_change)

        self.addTab(self.year_view, "Year")
        self.addTab(self.month_view, "Month")
        self.addTab(self.custom_view, "Custom")
        self.addTab(self.day_view, "Day")
        self.setCurrentIndex(MONTH)  # Month is the default landing scale, per the reference

        self.year_view.month_requested.connect(self._go_to_month)
        self.year_view.day_requested.connect(self._go_to_day)
        self.month_view.day_requested.connect(self._go_to_day)

    def _go_to_month(self, anchor: date) -> None:
        self.month_view.set_anchor(anchor)
        self.setCurrentIndex(MONTH)

    def _go_to_day(self, day: date) -> None:
        self.day_view.date_edit.setDate(_date_to_qdate(day))
        self.setCurrentIndex(DAY)
