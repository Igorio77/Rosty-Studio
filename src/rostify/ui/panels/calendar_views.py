"""Month and Year calendar views — the Schedule page's "Year -> Month ->
Custom -> Day" drill-down (see CLAUDE.md, "Reference material": this scale
switcher and the day-cell "template chip" look come from
reference/RostaStudioSchedule.jsx's Month/Year views, ported as design only).

A day cell's chip is a `Template` assigned to (subdepartment, date) via
`core.templates.TemplateAssignment` — the same record the Custom view reads
and writes. This is deliberately just a second, calendar-shaped way to see
and set the same day-plan data, not a new entity.

Working-draft interaction: click a day cell to assign/clear its Template via
a small dialog; click a day number to jump to Day view for that date; click
a month title (Year view) to jump to Month view. No drag-and-drop yet, same
"click first, drag later" precedent as Custom view and Day view.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable
from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from rostify.core.templates import Template, TemplateAssignment
from rostify.services.persistence import Repository

from ..theme import COLORS, TEMPLATE_COLOR_HEX
from .widgets import DepartmentSubdepartmentSelector

_WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]  # weekStartsOn = Sunday, per the reference
_NO_TEMPLATE = "— none —"


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _sunday_on_or_before(day: date) -> date:
    # Python's Monday=0..Sunday=6; days back to the most recent Sunday.
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _add_months(day: date, delta: int) -> date:
    month_index = day.month - 1 + delta
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


class _AssignTemplateDialog(QDialog):
    def __init__(self, templates: list[Template], current: Template | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Assign template")
        self.combo = QComboBox()
        self.combo.addItem(_NO_TEMPLATE)
        self.combo.addItems([t.name for t in templates])
        if current is not None:
            index = self.combo.findText(current.name)
            if index >= 0:
                self.combo.setCurrentIndex(index)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Template for this day"))
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

    def chosen_name(self) -> str:
        return self.combo.currentText()


class _MonthDayCell(QFrame):
    day_clicked = Signal(date)
    chip_clicked = Signal(date)
    remove_requested = Signal(date)

    def __init__(self, day: date, in_month: bool, is_today: bool, accent_hex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.day = day
        self._has_template = False
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumSize(90, 70)
        # "Grey grid": a faint border per cell, so the month reads as an
        # actual grid instead of loose floating chips.
        cell_bg = COLORS["bg_surface"] if in_month else COLORS["bg_app"]
        self.setStyleSheet(
            f"background: {cell_bg}; border: 1px solid {COLORS['border_subtle']}; border-radius: 8px;"
        )

        self.day_button = QPushButton(str(day.day))
        self.day_button.setFlat(True)
        self.day_button.setFixedSize(24, 24)
        self.day_button.setCursor(Qt.PointingHandCursor)
        self.day_button.clicked.connect(lambda: self.day_clicked.emit(self.day))
        # padding: 0 is load-bearing here — the app-wide QPushButton rule
        # pads 6px/14px, which leaves zero content room (and so an
        # invisible digit) inside a hard setFixedSize(24, 24) button.
        if is_today:
            self.day_button.setStyleSheet(
                f"border: none; padding: 0px; border-radius: 12px; background: {accent_hex}; "
                f"color: {COLORS['accent_on']}; font-weight: 700;"
            )
        else:
            muted = COLORS["text_tertiary"] if not in_month else COLORS["text_secondary"]
            self.day_button.setStyleSheet(f"border: none; padding: 0px; border-radius: 12px; color: {muted};")

        # Hover-only edit/remove icons (reference: "on hover, pencil + trash
        # icon appear") — hidden until enterEvent, only meaningful once a
        # template is actually assigned (see set_template/set_empty).
        self.edit_icon = QPushButton("✎")
        self.remove_icon = QPushButton("\U0001f5d1")
        for icon_button in (self.edit_icon, self.remove_icon):
            icon_button.setFlat(True)
            icon_button.setFixedSize(18, 18)
            icon_button.setCursor(Qt.PointingHandCursor)
            icon_button.setStyleSheet(
                f"border: none; padding: 0px; font-size: 10px; border-radius: 4px; "
                f"background: {COLORS['bg_active']}; color: {COLORS['text_primary']};"
            )
            icon_button.hide()
        self.edit_icon.setToolTip("Edit this day's template")
        self.remove_icon.setToolTip("Remove template from this day")
        self.edit_icon.clicked.connect(lambda: self.chip_clicked.emit(self.day))
        self.remove_icon.clicked.connect(lambda: self.remove_requested.emit(self.day))

        self.chip_button = QPushButton("")
        self.chip_button.setFlat(True)
        self.chip_button.setCursor(Qt.PointingHandCursor)
        self.chip_button.clicked.connect(lambda: self.chip_clicked.emit(self.day))
        self.chip_button.setMinimumHeight(38)
        self.chip_button.setStyleSheet("border: none; text-align: left; padding: 4px 6px; border-radius: 6px;")

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addWidget(self.day_button)
        top_row.addStretch(1)
        top_row.addWidget(self.edit_icon)
        top_row.addWidget(self.remove_icon)

        # 1/3 of the cell's height for the date row, 2/3 for the template
        # chip — explicit stretch factors, not just natural sizing.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(top_row, stretch=1)
        layout.addWidget(self.chip_button, stretch=2)

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        if self._has_template:
            self.edit_icon.show()
            self.remove_icon.show()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self.edit_icon.hide()
        self.remove_icon.hide()

    def set_empty(self) -> None:
        self._has_template = False
        self.chip_button.setText("+")
        self.chip_button.setStyleSheet(
            f"text-align: center; padding: 4px; border-radius: 6px; color: {COLORS['text_tertiary']}; "
            f"border: 1px dashed {COLORS['border_strong']};"
        )

    def set_template(self, template: Template) -> None:
        self._has_template = True
        hex_color = TEMPLATE_COLOR_HEX.get(template.color, TEMPLATE_COLOR_HEX["blue"])
        text = template.name if not template.subtitle else f"{template.name}\n{template.subtitle}"
        self.chip_button.setText(text)
        self.chip_button.setStyleSheet(
            f"border: none; text-align: left; padding: 4px 6px; border-radius: 6px; font-weight: 600; "
            f"background: {_hex_to_rgba(hex_color, 0.18)}; color: {hex_color};"
        )


class MonthGridView(QWidget):
    day_requested = Signal(date)

    def __init__(
        self,
        repository: Repository,
        on_change: Callable[[], None] | None = None,
        accent_hex: str = COLORS["accent"],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._on_change = on_change
        self._accent_hex = accent_hex
        self._anchor = date.today().replace(day=1)
        self._templates: list[Template] = []
        self._assignments: dict[date, str] = {}  # date -> template_id

        self.selector = DepartmentSubdepartmentSelector(repository)
        self.selector.subdepartment_changed.connect(lambda _: self._render())

        prev_button = QPushButton("<")
        prev_button.setFixedWidth(32)
        prev_button.clicked.connect(lambda: self._step(-1))
        next_button = QPushButton(">")
        next_button.setFixedWidth(32)
        next_button.clicked.connect(lambda: self._step(1))
        today_button = QPushButton("Today")
        today_button.clicked.connect(self._go_today)
        self.period_label = QLabel()
        self.period_label.setStyleSheet("font-weight: 600; font-size: 14px;")

        nav_row = QHBoxLayout()
        nav_row.addWidget(prev_button)
        nav_row.addWidget(self.period_label)
        nav_row.addWidget(next_button)
        nav_row.addWidget(today_button)
        nav_row.addStretch(1)

        top_row = QHBoxLayout()
        top_row.addWidget(self.selector)
        top_row.addStretch(1)
        top_row.addLayout(nav_row)

        self.grid_frame = QFrame()
        self.grid_frame.setObjectName("monthGridFrame")
        # Scoped by object name (not a bare "QFrame" selector) so this
        # border doesn't cascade onto the _MonthDayCell frames nested inside.
        self.grid_frame.setStyleSheet(
            f"QFrame#monthGridFrame {{ border: 1px solid {COLORS['border_default']}; border-radius: 12px; }}"
        )
        self.grid = QGridLayout(self.grid_frame)
        self.grid.setSpacing(2)
        self.grid.setContentsMargins(10, 10, 10, 10)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self.grid_frame, stretch=1)

        self._render()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.selector.reload()
        self._render()

    def set_anchor(self, day: date) -> None:
        self._anchor = day.replace(day=1)
        self._render()

    def _step(self, delta_months: int) -> None:
        self._anchor = _add_months(self._anchor, delta_months)
        self._render()

    def _go_today(self) -> None:
        self._anchor = date.today().replace(day=1)
        self._render()

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render(self) -> None:
        self._clear_grid()
        self.period_label.setText(self._anchor.strftime("%B %Y"))

        subdepartment = self.selector.current_subdepartment()
        self._templates = self._repository.load_templates(subdepartment) if subdepartment else []
        templates_by_id = {t.id: t for t in self._templates}

        # Column 0 is the week-number gutter; weekday headers/days start at 1.
        week_head = QLabel("Wk")
        week_head.setAlignment(Qt.AlignCenter)
        week_head.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_tertiary']};")
        self.grid.addWidget(week_head, 0, 0)
        for col, label in enumerate(_WEEKDAY_LABELS):
            # Uppercased here, not in QSS: Qt ignores `text-transform`.
            head = QLabel(label.upper())
            head.setAlignment(Qt.AlignCenter)
            head.setStyleSheet(
                f"font-size: 10px; font-weight: 700; color: {COLORS['text_tertiary']};"
            )
            self.grid.addWidget(head, 0, col + 1)

        start = _sunday_on_or_before(self._anchor)
        weeks = 6
        self._assignments = {}
        if subdepartment:
            range_end = start + timedelta(days=weeks * 7 - 1)
            for ta in self._repository.load_template_assignments_range(subdepartment, start, range_end):
                self._assignments[ta.date] = ta.template_id

        today = date.today()
        next_month = _add_months(self._anchor, 1)
        for week in range(weeks):
            week_start = start + timedelta(days=week * 7)
            week_number = QLabel(str(week_start.isocalendar()[1]))
            week_number.setAlignment(Qt.AlignCenter)
            week_number.setStyleSheet(f"font-weight: 700; color: {COLORS['text_tertiary']};")
            self.grid.addWidget(week_number, week + 1, 0)
            for weekday in range(7):
                day = start + timedelta(days=week * 7 + weekday)
                in_month = self._anchor <= day < next_month
                cell = _MonthDayCell(day, in_month, day == today, self._accent_hex)
                cell.day_clicked.connect(self.day_requested.emit)
                cell.chip_clicked.connect(self._on_chip_clicked)
                cell.remove_requested.connect(self._on_remove_clicked)
                template_id = self._assignments.get(day)
                template = templates_by_id.get(template_id) if template_id else None
                if template is not None:
                    cell.set_template(template)
                else:
                    cell.set_empty()
                self.grid.addWidget(cell, week + 1, weekday + 1)

    def _on_chip_clicked(self, day: date) -> None:
        subdepartment = self.selector.current_subdepartment()
        if not subdepartment:
            return
        current_id = self._assignments.get(day)
        current = next((t for t in self._templates if t.id == current_id), None)
        dialog = _AssignTemplateDialog(self._templates, current, self)
        if dialog.exec() != QDialog.Accepted:
            return
        chosen_name = dialog.chosen_name()
        if chosen_name == _NO_TEMPLATE:
            self._repository.delete_template_assignment(subdepartment, day)
        else:
            template = next((t for t in self._templates if t.name == chosen_name), None)
            if template is None:
                return
            self._repository.save_template_assignment(
                TemplateAssignment(subdepartment=subdepartment, date=day, template_id=template.id)
            )
        self._render()
        if self._on_change:
            self._on_change()

    def _on_remove_clicked(self, day: date) -> None:
        subdepartment = self.selector.current_subdepartment()
        if not subdepartment:
            return
        self._repository.delete_template_assignment(subdepartment, day)
        self._render()
        if self._on_change:
            self._on_change()


class _MiniMonth(QFrame):
    month_clicked = Signal(date)
    day_clicked = Signal(date)

    def __init__(self, year: int, month: int, accent_hex: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._first_of_month = date(year, month, 1)
        self._accent_hex = accent_hex

        # Frame around the full month, per the reference mock: a bordered
        # rounded card with the month name and a rule stretching beside it.
        # Scoped by object name so it doesn't cascade onto the day buttons
        # and the title-rule QFrame nested inside.
        self.setObjectName("miniMonthFrame")
        self.setStyleSheet(
            f"QFrame#miniMonthFrame {{ border: 1px solid {COLORS['border_default']}; border-radius: 12px; }}"
        )

        title = QPushButton(calendar.month_name[month])
        title.setFlat(True)
        title.setCursor(Qt.PointingHandCursor)
        title.setStyleSheet("font-weight: 700; font-size: 12px; text-align: left; border: none;")
        title.clicked.connect(lambda: self.month_clicked.emit(self._first_of_month))

        rule = QFrame()
        rule.setFrameShape(QFrame.HLine)
        rule.setStyleSheet(f"color: {COLORS['border_default']}; background: {COLORS['border_default']};")
        rule.setFixedHeight(1)
        rule.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(title)
        title_row.addWidget(rule, stretch=1)

        self.grid = QGridLayout()
        self.grid.setSpacing(1)
        # Column 0 is the week-number gutter, matching Month view.
        self.grid.addWidget(QLabel(""), 0, 0)
        for col, label in enumerate(_WEEKDAY_LABELS):
            head = QLabel(label[0])
            head.setAlignment(Qt.AlignCenter)
            head.setStyleSheet(f"font-size: 10px; color: {COLORS['text_tertiary']}; border: none;")
            self.grid.addWidget(head, 0, col + 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.addLayout(title_row)
        layout.addLayout(self.grid)

    def render_days(self, assigned_colors: dict[date, str]) -> None:
        start = _sunday_on_or_before(self._first_of_month)
        next_month = _add_months(self._first_of_month, 1)
        today = date.today()
        for week in range(6):
            week_start = start + timedelta(days=week * 7)
            week_number = QLabel(str(week_start.isocalendar()[1]))
            week_number.setAlignment(Qt.AlignCenter)
            week_number.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_tertiary']}; border: none;")
            self.grid.addWidget(week_number, week + 1, 0)
            for weekday in range(7):
                day = start + timedelta(days=week * 7 + weekday)
                in_month = self._first_of_month <= day < next_month
                button = QPushButton(str(day.day))
                button.setFlat(True)
                button.setFixedSize(22, 22)
                button.setCursor(Qt.PointingHandCursor)
                button.clicked.connect(lambda _=False, d=day: self.day_clicked.emit(d))
                # padding: 0 is load-bearing — see _MonthDayCell's day_button
                # comment: without it, a setFixedSize(22, 22) button has no
                # room left for its digit once the app-wide QPushButton
                # padding is applied, and the text silently doesn't paint.
                if not in_month:
                    button.setEnabled(False)
                    button.setStyleSheet(
                        f"border: none; padding: 0px; color: {COLORS['bg_active']}; font-size: 10px;"
                    )
                elif day == today:
                    button.setStyleSheet(
                        f"border: none; padding: 0px; border-radius: 11px; background: {self._accent_hex}; "
                        f"color: {COLORS['accent_on']}; font-size: 10px; font-weight: 700;"
                    )
                else:
                    hex_color = assigned_colors.get(day)
                    if hex_color:
                        button.setStyleSheet(
                            f"border: none; padding: 0px; font-size: 10px; border-bottom: 2px solid {hex_color}; "
                            f"border-radius: 0px; color: {COLORS['text_primary']};"
                        )
                    else:
                        button.setStyleSheet(
                            f"border: none; padding: 0px; font-size: 10px; color: {COLORS['text_secondary']};"
                        )
                self.grid.addWidget(button, week + 1, weekday + 1)


class YearGridView(QWidget):
    month_requested = Signal(date)
    day_requested = Signal(date)

    def __init__(
        self, repository: Repository, accent_hex: str = COLORS["accent"], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._accent_hex = accent_hex
        self._year = date.today().year

        prev_button = QPushButton("<")
        prev_button.setFixedWidth(32)
        prev_button.clicked.connect(lambda: self._step(-1))
        next_button = QPushButton(">")
        next_button.setFixedWidth(32)
        next_button.clicked.connect(lambda: self._step(1))
        self.year_label = QLabel()
        self.year_label.setStyleSheet("font-weight: 600; font-size: 14px;")

        self.selector = DepartmentSubdepartmentSelector(repository)
        self.selector.subdepartment_changed.connect(lambda _: self._render())

        nav_row = QHBoxLayout()
        nav_row.addWidget(prev_button)
        nav_row.addWidget(self.year_label)
        nav_row.addWidget(next_button)
        nav_row.addStretch(1)

        top_row = QHBoxLayout()
        top_row.addWidget(self.selector)
        top_row.addStretch(1)
        top_row.addLayout(nav_row)

        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(12)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self.grid_container, stretch=1)

        self._render()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.selector.reload()
        self._render()

    def _step(self, delta_years: int) -> None:
        self._year += delta_years
        self._render()

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render(self) -> None:
        self._clear_grid()
        self.year_label.setText(str(self._year))

        subdepartment = self.selector.current_subdepartment()
        templates_by_id = {}
        assigned_colors: dict[date, str] = {}
        if subdepartment:
            templates_by_id = {t.id: t for t in self._repository.load_templates(subdepartment)}
            year_start = date(self._year, 1, 1)
            year_end = date(self._year, 12, 31)
            for ta in self._repository.load_template_assignments_range(subdepartment, year_start, year_end):
                template = templates_by_id.get(ta.template_id)
                if template is not None:
                    assigned_colors[ta.date] = TEMPLATE_COLOR_HEX.get(template.color, TEMPLATE_COLOR_HEX["blue"])

        for index in range(12):
            month = index + 1
            mini = _MiniMonth(self._year, month, self._accent_hex)
            mini.month_clicked.connect(self.month_requested.emit)
            mini.day_clicked.connect(self.day_requested.emit)
            mini.render_days(assigned_colors)
            self.grid.addWidget(mini, index // 4, index % 4)
