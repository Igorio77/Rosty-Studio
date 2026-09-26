"""Custom view tab: for one subdepartment and a date range, pick which
Template governs each day ("one Template per subdepartment per day" — the
Custom view's own rule, separate from the Templates tab's master data), then
assign each employee to one of that day's Shift IDs.

Working-draft pass: a dropdown per cell, not drag-and-drop yet (that's a
later interaction-polish pass on top of this same data).

Picking a Shift ID here writes a real layer-SHIFT `Assignment` (core/models)
spanning that Shift ID's full Template timing for the day — this is the
Custom view actually using the "one unified Assignment model" rule
(CLAUDE.md), not a separate entity. `core/templates.TemplateAssignment` only
records which Template is the day's plan, not who's on it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import ShiftId, ShiftTiming, Template, TemplateAssignment
from rostify.services.persistence import Repository

from ..theme import COLORS, TEMPLATE_COLOR_HEX
from .staff_panel import EmployeeDialog
from .widgets import chars_width, icon_button, shift_badge_button, three_line_row_height

_NO_TEMPLATE = "— none —"
_NO_SHIFT = "— none —"
_MAX_DAYS = 31  # keeps the grid from growing unusably wide by accident
_STICKY_HEADERS = ["#", "Last Name", "First Name", "Employee ID"]
_DAY_SUB_HEADERS = ["Schedule", "Shift", "Hrs"]


def _qdate_to_date(qd: QDate) -> date:
    return date(qd.year(), qd.month(), qd.day())


def _date_to_qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def _format_minutes(total_minutes: int) -> str:
    day_offset, minute_of_day = divmod(total_minutes, 1440)
    hh, mm = divmod(minute_of_day, 60)
    period = "AM" if hh < 12 else "PM"
    hh12 = hh % 12 or 12
    suffix = " (+1d)" if day_offset else ""
    return f"{hh12}:{mm:02d} {period}{suffix}"


def _schedule_text(timing: ShiftTiming | None) -> str:
    if timing is None or not timing.segments:
        return ""
    return "\n".join(f"{_format_minutes(s.start_minutes)}–{_format_minutes(s.end_minutes)}" for s in timing.segments)


def _timing_hours(timing: ShiftTiming | None) -> float:
    if timing is None or not timing.segments:
        return 0.0
    return sum((s.end_minutes - s.start_minutes) for s in timing.segments) / 60.0


class _DayTemplateDialog(QDialog):
    """Pick (or clear) this day's Template — opened by clicking the day
    banner cell, replacing what used to be an always-visible combo box so
    the header row reads like the reference's date/template card."""

    def __init__(self, templates: list[Template], current: Template | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Template for this day")
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
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

    def chosen_name(self) -> str:
        return self.combo.currentText()


class _ClickableFrame(QFrame):
    """A QFrame that can be a table cell widget and still be clickable as a
    whole — used for the day banner (date + template) and would need a real
    QPushButton to get a click signal otherwise, which can't hold this much
    nested layout cleanly."""

    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        self.clicked.emit()


class CustomViewPanel(QWidget):
    def __init__(
        self,
        schedule: Schedule,
        repository: Repository,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._schedule = schedule
        self._repository = repository
        self._on_change = on_change

        self._dates: list[date] = []
        self._templates: list[Template] = []
        self._day_template: dict[date, Template | None] = {}
        self._timings_by_template: dict[str, dict[str, ShiftTiming]] = {}  # template_id -> {shift_id_id: timing}
        self._shift_ids: list[ShiftId] = []
        self._employees: list[Employee] = []

        self.department_combo = QComboBox()
        self.department_combo.currentTextChanged.connect(self._reload_subdepartments)
        self.subdepartment_combo = QComboBox()
        # Bug fix: switching Subdepartment without touching Department (or
        # clicking Load) used to leave the old subdepartment's data on
        # screen, so every Shift dropdown looked empty for the new one.
        self.subdepartment_combo.currentTextChanged.connect(lambda _: self._reload())

        today = date.today()
        self.from_date = QDateEdit(_date_to_qdate(today))
        self.from_date.setCalendarPopup(True)
        self.to_date = QDateEdit(_date_to_qdate(today + timedelta(days=6)))
        self.to_date.setCalendarPopup(True)

        load_button = QPushButton("Load")
        load_button.clicked.connect(self._reload)

        # This grid's rows are the subdepartment's roster, which Team owns.
        # The button is here so adding a missing person doesn't mean leaving
        # the page — it opens Team's own dialog, prefilled with the
        # subdepartment already selected above.
        add_employee_button = icon_button("+", "Add employee to this subdepartment")
        add_employee_button.clicked.connect(self._add_employee)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Department"))
        top_row.addWidget(self.department_combo)
        top_row.addWidget(QLabel("Subdepartment"))
        top_row.addWidget(self.subdepartment_combo)
        top_row.addWidget(QLabel("From"))
        top_row.addWidget(self.from_date)
        top_row.addWidget(QLabel("To"))
        top_row.addWidget(self.to_date)
        top_row.addWidget(load_button)
        # Left, next to Load, not floated right: Team and Templates both put
        # their add/edit/delete icons at the left edge, and an action parked
        # alone against the window edge is the one nobody finds.
        top_row.addSpacing(8)
        top_row.addWidget(add_employee_button)
        top_row.addStretch(1)

        self.table = QTableWidget()
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # The real column labels live in row 1 (see _render), so the native
        # header carries no text. It stays visible at hairline height purely
        # as the drag surface for column widths — hiding it outright would
        # take Excel-style resizing with it.
        self.table.horizontalHeader().setFixedHeight(6)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(three_line_row_height(self.table))
        self.table.verticalHeader().setVisible(False)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self.table, stretch=1)

        self._reload_departments()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._reload_departments()

    def reload(self) -> None:
        self._reload()

    # --- department / subdepartment cascade -------------------------------

    def _add_employee(self) -> None:
        """Add an employee straight into the subdepartment on screen.

        Same dialog, same validation and same persistence path as the Team
        panel — the roster has one owner, this is only a second door to it.
        """
        dialog = EmployeeDialog(
            self._repository,
            parent=self,
            preset_department=self.department_combo.currentText(),
            preset_subdepartment=self.subdepartment_combo.currentText(),
        )
        if dialog.exec() != QDialog.Accepted:
            return
        employee = dialog.employee()
        if not employee.id or not employee.first_name or not employee.last_name:
            return

        self._schedule.add_employee(employee)
        if self._on_change:
            self._on_change()
        self._show_subdepartment(employee.department, employee.subdepartment)

    def _show_subdepartment(self, department: str, subdepartment: str) -> None:
        """Point the filters at `department`/`subdepartment` and rebuild.

        Called after an add: the dialog lets the user pick a different
        subdepartment than the one on screen, and silently rebuilding a grid
        the new employee is not in would read as "nothing happened". The
        final `_reload` is unconditional because neither combo emits a
        change signal when the wanted value is already selected.
        """
        department_index = self.department_combo.findText(department)
        if department_index >= 0:
            self.department_combo.setCurrentIndex(department_index)
        subdepartment_index = self.subdepartment_combo.findText(subdepartment)
        if subdepartment_index >= 0:
            self.subdepartment_combo.setCurrentIndex(subdepartment_index)
        self._reload()

    def _reload_departments(self) -> None:
        current = self.department_combo.currentText()
        departments = self._repository.load_departments()
        self.department_combo.blockSignals(True)
        self.department_combo.clear()
        self.department_combo.addItems(departments)
        index = self.department_combo.findText(current)
        self.department_combo.setCurrentIndex(index if index >= 0 else 0)
        self.department_combo.blockSignals(False)
        self._reload_subdepartments(self.department_combo.currentText())

    def _reload_subdepartments(self, department: str) -> None:
        current = self.subdepartment_combo.currentText()
        options = self._repository.load_subdepartments(department) if department else []
        self.subdepartment_combo.blockSignals(True)
        self.subdepartment_combo.clear()
        self.subdepartment_combo.addItems([o.name for o in options])
        index = self.subdepartment_combo.findText(current)
        self.subdepartment_combo.setCurrentIndex(index if index >= 0 else 0)
        self.subdepartment_combo.blockSignals(False)
        self._reload()

    def _current_subdepartment(self) -> str:
        return self.subdepartment_combo.currentText().strip()

    # --- loading -------------------------------------------------

    def _reload(self) -> None:
        subdepartment = self._current_subdepartment()
        start = _qdate_to_date(self.from_date.date())
        end = _qdate_to_date(self.to_date.date())
        if end < start:
            start, end = end, start
        span_days = min((end - start).days, _MAX_DAYS - 1)
        self._dates = [start + timedelta(days=i) for i in range(span_days + 1)]

        if not subdepartment:
            self._templates, self._shift_ids, self._employees = [], [], []
            self._day_template = {}
            self._render()
            return

        self._templates = self._repository.load_templates(subdepartment)
        self._shift_ids = self._repository.load_shift_ids(subdepartment)
        self._employees = sorted(
            (e for e in self._schedule.employees() if e.subdepartment == subdepartment),
            key=lambda e: e.full_name,
        )
        self._timings_by_template = {}
        for template in self._templates:
            self._timings_by_template[template.id] = {
                t.shift_id: t for t in self._repository.load_shift_timings(template.id) if t.segments
            }

        by_id = {t.id: t for t in self._templates}
        self._day_template = {}
        for ta in self._repository.load_template_assignments_range(subdepartment, start, end):
            self._day_template[ta.date] = by_id.get(ta.template_id)

        self._render()

    # --- rendering -------------------------------------------------

    def _day_column(self, day_index: int) -> int:
        """First of the 3 columns (Schedule, Shift, Hrs) for the day at
        `day_index` in `self._dates` — sticky #/Last/First/ID take columns 0-3."""
        return len(_STICKY_HEADERS) + day_index * 3

    def _sub_header_item(self, label: str) -> QTableWidgetItem:
        """A bold, muted label for row 1 — used for both "Schedule/Shift/Hrs"
        under a day and "#/Last Name/First Name/Employee ID" over the sticky
        columns, so both sides of the table read as one header band."""
        item = QTableWidgetItem(label.upper())
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setForeground(QColor(COLORS["text_tertiary"]))
        font = item.font()
        font.setBold(True)
        font.setPointSize(max(font.pointSize() - 1, 7))
        item.setFont(font)
        return item

    def _render(self) -> None:
        table = self.table
        table.clear()
        # Row 0 = day banner (date + template), row 1 = column labels
        # (#/Last Name/First Name/Employee ID over the sticky columns,
        # Schedule/Shift/Hrs under each day) — employee rows start at row 2.
        # The native QHeaderView is left blank on purpose: real labels live
        # here instead, so the sticky columns' header band is exactly as
        # tall as the day banner's, instead of a short text header sitting
        # above a much taller banner. The header itself stays visible (just
        # empty) so column widths are still Excel-style draggable.
        table.setRowCount(len(self._employees) + 2)
        # sticky columns + 3 per day + 1 Total Hrs column.
        column_count = len(_STICKY_HEADERS) + len(self._dates) * 3 + 1
        table.setColumnCount(column_count)
        table.setHorizontalHeaderLabels([""] * column_count)
        sticky_span = len(_STICKY_HEADERS)
        table.setSpan(0, 0, 1, sticky_span)  # blank corner above #/Last/First/ID
        for sub_index, label in enumerate(_STICKY_HEADERS):
            table.setItem(1, sub_index, self._sub_header_item(label))
        table.setSpan(0, column_count - 1, 2, 1)  # Total Hrs: blank corner, label lives in the header text instead
        total_header = self._sub_header_item("Total Hrs")
        table.setItem(0, column_count - 1, total_header)

        for day_index, day in enumerate(self._dates):
            col = self._day_column(day_index)
            table.setCellWidget(0, col, self._build_day_banner(day))
            table.setSpan(0, col, 1, 3)
            for sub_index, label in enumerate(_DAY_SUB_HEADERS):
                table.setItem(1, col + sub_index, self._sub_header_item(label))

        for row_offset, employee in enumerate(self._employees):
            row = row_offset + 2
            sequence_item = QTableWidgetItem(str(row_offset + 1))
            sequence_item.setTextAlignment(Qt.AlignCenter)
            sequence_item.setFlags(sequence_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 0, sequence_item)
            for col, value in enumerate((employee.last_name, employee.first_name, employee.id), start=1):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col, item)

            total_hours = 0.0
            for day_index, day in enumerate(self._dates):
                col = self._day_column(day_index)
                timing = self._current_timing(employee, day)
                schedule_item = QTableWidgetItem(_schedule_text(timing))
                schedule_item.setTextAlignment(Qt.AlignCenter)
                schedule_item.setFlags(schedule_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col, schedule_item)

                table.setCellWidget(row, col + 1, self._build_shift_badge(employee, day))

                hours = _timing_hours(timing)
                total_hours += hours
                hrs_item = QTableWidgetItem(f"{hours:.1f}" if timing else "")
                hrs_item.setTextAlignment(Qt.AlignCenter)
                hrs_item.setFlags(hrs_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col + 2, hrs_item)

            total_item = QTableWidgetItem(f"{total_hours:.1f}")
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            font = total_item.font()
            font.setBold(True)
            total_item.setFont(font)
            table.setItem(row, table.columnCount() - 1, total_item)

        table.horizontalHeader().resizeSection(0, chars_width(table, 4))  # "#"
        name_width = chars_width(table, 20)
        for col in range(1, sticky_span):
            table.horizontalHeader().resizeSection(col, name_width)
        schedule_width = chars_width(table, 20)
        short_width = chars_width(table, 6)
        for day_index in range(len(self._dates)):
            col = self._day_column(day_index)
            table.horizontalHeader().resizeSection(col, schedule_width)
            table.horizontalHeader().resizeSection(col + 1, short_width)
            table.horizontalHeader().resizeSection(col + 2, short_width)
        table.horizontalHeader().resizeSection(table.columnCount() - 1, chars_width(table, 10))
        table.setRowHeight(0, 64)
        table.setRowHeight(1, 22)

    def _build_day_banner(self, day: date) -> QWidget:
        template = self._day_template.get(day)
        frame = _ClickableFrame()
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(f"border-bottom: 1px solid {COLORS['border_default']};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(1)

        date_label = QLabel(f"{day.strftime('%a, %b')} {day.day}")
        date_label.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']}; font-size: 10px;")
        layout.addWidget(date_label)

        if template is not None:
            hex_color = TEMPLATE_COLOR_HEX.get(template.color, TEMPLATE_COLOR_HEX["blue"])
            name_row = QHBoxLayout()
            name_row.setSpacing(4)
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"border: none; border-radius: 4px; background: {hex_color};")
            name_label = QLabel(template.name)
            name_label.setStyleSheet("border: none; font-weight: 700;")
            name_row.addWidget(dot)
            name_row.addWidget(name_label)
            name_row.addStretch(1)
            layout.addLayout(name_row)
            if template.subtitle:
                comment_label = QLabel(template.subtitle)
                comment_label.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']}; font-size: 10px;")
                comment_label.setWordWrap(True)
                layout.addWidget(comment_label)
        else:
            placeholder = QLabel("No template — click to assign")
            placeholder.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']}; font-style: italic;")
            layout.addWidget(placeholder)

        frame.clicked.connect(lambda d=day: self._pick_day_template(d))
        return frame

    def _pick_day_template(self, day: date) -> None:
        current = self._day_template.get(day)
        dialog = _DayTemplateDialog(self._templates, current, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self._on_day_template_changed(day, dialog.chosen_name())

    def _current_timing(self, employee: Employee, day: date) -> ShiftTiming | None:
        template = self._day_template.get(day)
        if template is None:
            return None
        existing = self._existing_shift_assignment(employee, day)
        if existing is None:
            return None
        shift_id = next((s for s in self._shift_ids if s.code == existing.resource), None)
        if shift_id is None:
            return None
        return self._timings_by_template.get(template.id, {}).get(shift_id.id)

    def _available_codes(self, day: date) -> list[str]:
        template = self._day_template.get(day)
        timings = self._timings_by_template.get(template.id, {}) if template else {}
        codes_by_shift_id = {s.id: s.code for s in self._shift_ids}
        return sorted(codes_by_shift_id[sid] for sid in timings if sid in codes_by_shift_id)

    def _build_shift_badge(self, employee: Employee, day: date) -> QWidget:
        """The shared colored badge (widgets.shift_badge_button) — each
        Shift ID carries its *own* color (ShiftId.color), independent of the
        day's template color, matching the reference. Click opens a small
        menu to replace/remove it, same "click to act" pattern as the Month
        view's day chip."""
        existing = self._existing_shift_assignment(employee, day)
        code = existing.resource if existing else ""
        shift_id = next((s for s in self._shift_ids if s.code == code), None) if code else None
        hex_color = TEMPLATE_COLOR_HEX.get(shift_id.color, TEMPLATE_COLOR_HEX["blue"]) if shift_id else None

        button = shift_badge_button(
            code, hex_color, f"Shift {code} — click to replace or remove" if code else "Click to assign a shift"
        )
        button.clicked.connect(lambda: self._show_shift_menu(button, employee, day))
        return button

    def _show_shift_menu(self, anchor: QWidget, employee: Employee, day: date) -> None:
        existing = self._existing_shift_assignment(employee, day)
        available = self._available_codes(day)
        menu = QMenu(anchor)
        if existing is not None:
            remove_action = menu.addAction(f"Remove from shift '{existing.resource}'")
            menu.addSeparator()
        else:
            remove_action = None
        if not available:
            empty_action = menu.addAction("No shifts available — assign a template with timings first")
            empty_action.setEnabled(False)
        for code in available:
            action = menu.addAction(f"Assign '{code}'")
            action.triggered.connect(lambda _checked=False, c=code: self._on_shift_pick_changed(employee, day, c))
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen is remove_action:
            self._on_shift_pick_changed(employee, day, _NO_SHIFT)

    def _existing_shift_assignment(self, employee: Employee, day: date) -> Assignment | None:
        matches = self._schedule.assignments(employee_id=employee.id, on=day, layer=Layer.SHIFT)
        return matches[0] if matches else None

    # --- edits -------------------------------------------------

    def _on_day_template_changed(self, day: date, template_name: str) -> None:
        subdepartment = self._current_subdepartment()
        if template_name == _NO_TEMPLATE:
            self._repository.delete_template_assignment(subdepartment, day)
            self._day_template[day] = None
        else:
            template = next((t for t in self._templates if t.name == template_name), None)
            if template is None:
                return
            self._repository.save_template_assignment(
                TemplateAssignment(subdepartment=subdepartment, date=day, template_id=template.id)
            )
            self._day_template[day] = template
        self._render()

    def _on_shift_pick_changed(self, employee: Employee, day: date, shift_code: str) -> None:
        existing = self._existing_shift_assignment(employee, day)
        if existing is not None:
            self._schedule.remove_assignment(existing.id)
            self._repository.delete_assignment(existing.id)

        if shift_code != _NO_SHIFT:
            template = self._day_template.get(day)
            shift_id = next((s for s in self._shift_ids if s.code == shift_code), None)
            timing = self._timings_by_template.get(template.id, {}).get(shift_id.id) if template and shift_id else None
            if timing and timing.segments:
                start_minutes = min(s.start_minutes for s in timing.segments)
                end_minutes = max(s.end_minutes for s in timing.segments)
                day_start = datetime.combine(day, datetime.min.time())
                assignment = Assignment(
                    employee_id=employee.id,
                    start=day_start + timedelta(minutes=start_minutes),
                    end=day_start + timedelta(minutes=end_minutes),
                    resource=shift_code,
                    layer=Layer.SHIFT,
                    department=employee.department,
                )
                self._schedule.add_assignment(assignment)
                self._repository.save_assignment(assignment)

        self._render()  # Schedule/Hrs/Total Hrs columns depend on this pick
        if self._on_change:
            self._on_change()
