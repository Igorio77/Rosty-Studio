"""Custom view tab: for one subdepartment and a date range, pick which
Template governs each day ("one Template per subdepartment per day" — the
Custom view's own rule, separate from the Templates tab's master data), then
assign each employee to one of that day's Shift IDs.

Drag and drop: drag a Shift ID badge to another employee or day to move
it (hold Ctrl to copy), or drag one from the Shift ID strip above the grid
onto a cell to assign it. Drag an employee by the "#" column to reorder the
rows; the order is remembered per subdepartment. Clicking a badge still
opens its menu.

"+ Add employee" brings someone from another subdepartment here — for a
period, or for good (guest_dialog.TransferDialog). Employees from another
subdepartment show their names in the accent color; days they belong
elsewhere are greyed out with "→ <subdepartment>". Right-click a name to
send a transferred employee back. Days an employee is temporarily not
available are greyed out too. A Shift ID is one person's slot per day:
taken codes are refused.

Picking a Shift ID here writes a real layer-SHIFT `Assignment` (core/models)
spanning that Shift ID's full Template timing for the day — this is the
Custom view actually using the "one unified Assignment model" rule
(CLAUDE.md), not a separate entity. `core/templates.TemplateAssignment` only
records which Template is the day's plan, not who's on it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

from PySide6.QtCore import QByteArray, QDate, QEvent, QMimeData, QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QDrag
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import ShiftId, ShiftTiming, Template, TemplateAssignment, natural_key
from rostify.services.persistence import Repository
from rostify.services.roster import describe_employee, effective_subdepartment, end_transfer, move_permanently, transfer_for_period
from rostify.services.shift_sync import (
    ShiftError,
    assign_shift,
    clear_shift,
    code_holder,
    duplicate_codes,
    retime_day,
    schedule_group,
    shift_on_day,
)

from ..theme import COLORS, SURFACE, TEMPLATE_COLOR_HEX
from .guest_dialog import TransferDialog
from .widgets import (
    FrozenColumns,
    ZoomControl,
    apply_table_zoom,
    centered_in_cell,
    chars_width,
    shift_badge_button,
    show_shift_error,
    three_line_row_height,
)

_NO_TEMPLATE = "— none —"
_NO_SHIFT = "— none —"
_MAX_DAYS = 31  # keeps the grid from growing unusably wide by accident
_STICKY_HEADERS = ["#", "Last Name", "First Name", "Employee ID"]
_DAY_SUB_HEADERS = ["Schedule", "Shift", "Hrs"]
_SHIFT_MIME = "application/x-rostify-shift"  # "code|employee id|ISO date" (palette: "code||")
_ROW_MIME = "application/x-rostify-employee-row"


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
        zoom: float = 1.0,
        on_zoom_changed: Callable[[float], None] | None = None,
        on_open_timing: Callable | None = None,
    ) -> None:
        """`on_open_timing(group, code, day)`: jump to a Shift ID's timing
        in the Templates tab (offered when a shift has none)."""
        super().__init__(parent)
        self._on_open_timing = on_open_timing
        self._schedule = schedule
        self._repository = repository
        self._on_change = on_change
        self._on_zoom_changed = on_zoom_changed

        self._dates: list[date] = []
        self._sticky_sized = False  # see _render: default widths are set once
        self._sized_dates: list[date] | None = None
        self._templates: list[Template] = []
        self._day_template: dict[date, Template | None] = {}
        self._timings_by_template: dict[str, dict[str, ShiftTiming]] = {}  # template_id -> {shift_id_id: timing}
        self._shift_ids: list[ShiftId] = []
        self._employees: list[Employee] = []
        self._guest_ids: set[str] = set()  # rows from another subdepartment
        self._transfers = []
        # (employee id, day) -> the subdepartment they are in instead, for
        # days they belong elsewhere.
        self._away: dict[tuple[str, date], str] = {}
        self._press: tuple[QPoint, str, object] | None = None  # drag start: (pos, kind, payload)

        self._subdepartment = ""  # set by the Schedule page's shared selector

        # The period, shown by the Schedule page in its top row. Changing
        # either date reloads straight away.
        today = date.today()
        self.from_date = QDateEdit(_date_to_qdate(today))
        self.from_date.setCalendarPopup(True)
        self.from_date.setToolTip("First day shown")
        self.to_date = QDateEdit(_date_to_qdate(today + timedelta(days=6)))
        self.to_date.setCalendarPopup(True)
        self.to_date.setToolTip(f"Last day shown (up to {_MAX_DAYS} days)")
        self.from_date.dateChanged.connect(lambda _: self._reload())
        self.to_date.dateChanged.connect(lambda _: self._reload())
        self.period_controls = QWidget()
        period_row = QHBoxLayout(self.period_controls)
        period_row.setContentsMargins(0, 0, 0, 0)
        period_row.addWidget(QLabel("From"))
        period_row.addWidget(self.from_date)
        period_row.addWidget(QLabel("To"))
        period_row.addWidget(self.to_date)

        # Second row: add crew from another subdepartment, then the strip of
        # Shift IDs to drag onto the grid.
        guest_button = QPushButton("+ Add employee")
        guest_button.setToolTip(
            "Bring an employee from another subdepartment here — for a period, or permanently"
        )
        guest_button.clicked.connect(self._add_guest)

        # Shift IDs to drag onto the grid.
        self._palette_row = QHBoxLayout()
        self._palette_row.setSpacing(4)
        palette_label = QLabel("Drag a shift:")
        palette_label.setProperty("role", "hint")
        self._palette_row.addStretch(1)
        # In a scroll strip: a subdepartment can have dozens of Shift IDs,
        # and a row of them must not push the window wider than the screen.
        strip = QWidget()
        strip.setProperty("transparentBg", True)
        strip.setLayout(self._palette_row)
        self._palette_row.setContentsMargins(0, 0, 0, 0)
        scroller = QScrollArea()
        scroller.setWidget(strip)
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)
        scroller.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroller.setFixedHeight(46)
        scroller.setProperty("transparentBg", True)
        scroller.viewport().setProperty("transparentBg", True)
        palette_bar = QHBoxLayout()
        palette_bar.addWidget(guest_button)
        palette_bar.addSpacing(12)
        palette_bar.addWidget(palette_label)
        palette_bar.addWidget(scroller, stretch=1)

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
        self.table.verticalHeader().setVisible(False)

        # Ctrl+mouse wheel zooms the grid; the owner remembers the level.
        self._zoom = 0.0  # set by _apply_zoom below
        self.zoom_control = ZoomControl(self.table, zoom)
        self.zoom_control.zoom_changed.connect(self._on_zoom)
        self._apply_zoom(self.zoom_control.zoom())

        self.table.viewport().setAcceptDrops(True)
        self.table.viewport().installEventFilter(self)  # drops, and row drags from "#"
        # "#", names and Employee ID stay put while the days scroll.
        self._frozen = FrozenColumns(self.table, len(_STICKY_HEADERS))
        self._frozen.view.viewport().setAcceptDrops(True)
        self._frozen.view.viewport().installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.addLayout(palette_bar)
        layout.addWidget(self.table, stretch=1)
        # Filled in showEvent, not here: nothing is read until the page is
        # actually opened.

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._reload()

    def set_subdepartment(self, subdepartment: str) -> None:
        self._subdepartment = subdepartment
        self._reload()

    def _apply_zoom(self, zoom: float) -> None:
        apply_table_zoom(self.table, zoom, self._zoom)
        self._zoom = zoom
        self.table.verticalHeader().setDefaultSectionSize(three_line_row_height(self.table))

    def _on_zoom(self, zoom: float) -> None:
        self._apply_zoom(zoom)
        self._render()
        if self._on_zoom_changed:
            self._on_zoom_changed(zoom)

    def _px(self, size: int) -> int:
        """A font pixel size at the current zoom."""
        return max(round(size * self._zoom), 7)

    def reload(self) -> None:
        self._reload()

    def _current_subdepartment(self) -> str:
        return self._subdepartment

    # --- loading -------------------------------------------------

    def _reload(self) -> None:
        if not self.isVisible():
            return  # showEvent reloads when the page is opened
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
        self._shift_ids = sorted(self._repository.load_shift_ids(subdepartment), key=lambda s: natural_key(s.code))
        # Everyone who works here on at least one day of the range: own
        # employees not transferred out, people transferred in, and anyone
        # with a shift on this schedule. In the order the user dragged them;
        # new people last, by name.
        self._transfers = self._repository.load_transfers()
        members: dict[str, Employee] = {}
        self._away = {}
        range_set = set(self._dates)
        shifts = {
            (a.employee_id, a.start.date()): a
            for a in self._schedule.assignments(layer=Layer.SHIFT)
            if a.start.date() in range_set
        }
        for employee in self._schedule.employees():
            here = False
            for day in self._dates:
                shift = shifts.get((employee.id, day))
                on_shift_here = shift is not None and schedule_group(shift, employee) == subdepartment
                where = effective_subdepartment(employee, day, self._transfers)
                if where == subdepartment or on_shift_here:
                    here = True
                else:
                    self._away[(employee.id, day)] = where
            if here:
                members[employee.id] = employee
        saved = {employee_id: i for i, employee_id in enumerate(self._repository.load_employee_order(subdepartment))}
        self._employees = sorted(
            members.values(),
            key=lambda e: (saved.get(e.id, len(saved)), e.subdepartment != subdepartment, e.last_name, e.first_name),
        )
        self._guest_ids = {e.id for e in self._employees if e.subdepartment != subdepartment}
        self._timings_by_template = {}
        for template in self._templates:
            self._timings_by_template[template.id] = {
                t.shift_id: t for t in self._repository.load_shift_timings(template.id) if t.segments
            }

        by_id = {t.id: t for t in self._templates}
        self._day_template = {}
        for ta in self._repository.load_template_assignments_range(subdepartment, start, end):
            self._day_template[ta.date] = by_id.get(ta.template_id)

        self._render_palette()
        self._render()

    def _render_palette(self) -> None:
        while self._palette_row.count() > 1:  # keep the trailing stretch
            widget = self._palette_row.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        for position, shift_id in enumerate(self._shift_ids):
            badge = shift_badge_button(
                shift_id.code,
                TEMPLATE_COLOR_HEX.get(shift_id.color, TEMPLATE_COLOR_HEX["blue"]),
                f"Drag {shift_id.code} onto an employee's day",
            )
            badge.setCursor(Qt.OpenHandCursor)
            badge.setProperty("dragShift", f"{shift_id.code}||")
            badge.installEventFilter(self)
            self._palette_row.insertWidget(position, badge)

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
        font.setPixelSize(self._px(12))
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
            sequence_item.setToolTip("Drag to move this employee up or down")
            guest = employee.id in self._guest_ids
            away_all_range = all(employee.is_unavailable_on(day) for day in self._dates) if self._dates else False
            for col, value in enumerate((employee.last_name, employee.first_name, employee.id), start=1):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if away_all_range:
                    item.setForeground(QColor(COLORS["text_tertiary"]))
                elif guest:
                    item.setForeground(QColor(COLORS["accent"]))
                table.setItem(row, col, item)

            total_hours = 0.0
            for day_index, day in enumerate(self._dates):
                col = self._day_column(day_index)
                timing = self._current_timing(employee, day)
                schedule_item = QTableWidgetItem(_schedule_text(timing))
                schedule_item.setTextAlignment(Qt.AlignCenter)
                schedule_item.setFlags(schedule_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col, schedule_item)

                away = self._away.get((employee.id, day))
                if away is not None:
                    # Working in another subdepartment that day.
                    schedule_item.setText(f"→ {away}")
                    schedule_item.setToolTip(f"In {away} on this day")
                    schedule_item.setBackground(QColor(SURFACE[0]))
                    schedule_item.setForeground(QColor(COLORS["text_tertiary"]))
                    table.removeCellWidget(row, col + 1)
                    blank = QTableWidgetItem("")
                    blank.setFlags(Qt.ItemIsEnabled)
                    blank.setBackground(QColor(SURFACE[0]))
                    table.setItem(row, col + 1, blank)
                else:
                    table.setCellWidget(row, col + 1, centered_in_cell(self._build_shift_badge(employee, day)))

                hours = _timing_hours(timing)
                total_hours += hours
                hrs_item = QTableWidgetItem(f"{hours:.1f}" if timing else "")
                hrs_item.setTextAlignment(Qt.AlignCenter)
                hrs_item.setFlags(hrs_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col + 2, hrs_item)
                if away is not None:
                    hrs_item.setBackground(QColor(SURFACE[0]))
                elif employee.is_unavailable_on(day):
                    # Temporarily not available: still shown, greyed out.
                    for item in (schedule_item, hrs_item):
                        item.setBackground(QColor(SURFACE[0]))
                        item.setForeground(QColor(COLORS["text_tertiary"]))
                    schedule_item.setToolTip("Temporarily not available")
                    if not schedule_item.text():
                        schedule_item.setText("n/a")

            total_item = QTableWidgetItem(f"{total_hours:.1f}")
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            font = total_item.font()
            font.setBold(True)
            total_item.setFont(font)
            table.setItem(row, table.columnCount() - 1, total_item)

        # Default widths only when the set of columns changes (first render,
        # or a different date range) — an ordinary re-render after an edit
        # keeps whatever widths the user dragged.
        header = table.horizontalHeader()
        if not self._sticky_sized:
            header.resizeSection(0, chars_width(table, 4))  # "#"
            for col in range(1, sticky_span):
                header.resizeSection(col, chars_width(table, 20))
            self._sticky_sized = True
        if self._sized_dates != self._dates:
            schedule_width = chars_width(table, 20)
            short_width = chars_width(table, 6)
            for day_index in range(len(self._dates)):
                col = self._day_column(day_index)
                header.resizeSection(col, schedule_width)
                header.resizeSection(col + 1, short_width)
                header.resizeSection(col + 2, short_width)
            header.resizeSection(table.columnCount() - 1, chars_width(table, 10))
            self._sized_dates = list(self._dates)
        table.setRowHeight(0, round(64 * self._zoom))
        table.setRowHeight(1, round(22 * self._zoom))
        self._frozen.sync()
        for row in range(2, table.rowCount()):
            table.setRowHeight(row, three_line_row_height(table))

    def _build_day_banner(self, day: date) -> QWidget:
        template = self._day_template.get(day)
        frame = _ClickableFrame()
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(f"border-bottom: 1px solid {COLORS['border_default']};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(1)

        date_label = QLabel(f"{day.strftime('%a, %b')} {day.day}")
        date_label.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']}; font-size: {self._px(10)}px;")
        layout.addWidget(date_label)

        if template is not None:
            hex_color = TEMPLATE_COLOR_HEX.get(template.color, TEMPLATE_COLOR_HEX["blue"])
            name_row = QHBoxLayout()
            name_row.setSpacing(4)
            dot = QLabel()
            dot_size = max(round(8 * self._zoom), 4)
            dot.setFixedSize(dot_size, dot_size)
            dot.setStyleSheet(f"border: none; border-radius: {dot_size // 2}px; background: {hex_color};")
            name_label = QLabel(template.name)
            name_label.setStyleSheet(f"border: none; font-weight: 700; font-size: {self._px(13)}px;")
            name_row.addWidget(dot)
            name_row.addWidget(name_label)
            name_row.addStretch(1)
            layout.addLayout(name_row)
            if template.subtitle:
                comment_label = QLabel(template.subtitle)
                comment_label.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']}; font-size: {self._px(10)}px;")
                comment_label.setWordWrap(True)
                layout.addWidget(comment_label)
        else:
            placeholder = QLabel("No template — click to assign")
            placeholder.setStyleSheet(
                f"border: none; color: {COLORS['text_tertiary']}; font-style: italic; font-size: {self._px(13)}px;"
            )
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
            code,
            hex_color,
            f"Shift {code} — click to replace or remove, drag to move (Ctrl+drag to copy)"
            if code
            else "Click to assign a shift, or drop one here",
            scale=self._zoom,
        )
        button.clicked.connect(lambda: self._show_shift_menu(button, employee, day))
        if code:
            button.setProperty("dragShift", f"{code}|{employee.id}|{day.isoformat()}")
            button.installEventFilter(self)
            if code in duplicate_codes(self._schedule, self._current_subdepartment(), day):
                # Data from before the one-person-per-Shift-ID check.
                button.setStyleSheet(button.styleSheet() + f" border: 2px solid {COLORS['danger']};")
                button.setToolTip(f"'{code}' is given to more than one person on this day — change one of them")
        return button

    def _show_shift_menu(self, anchor: QWidget, employee: Employee, day: date) -> None:
        existing = self._existing_shift_assignment(employee, day)
        available = self._available_codes(day)
        # Codes the day's template has no timing for are listed too: picking
        # one explains why it can't be used and offers the jump to fix it.
        untimed = [s.code for s in self._shift_ids if s.code not in available] if self._day_template.get(day) else []
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
            holder = code_holder(self._schedule, self._current_subdepartment(), day, code)
            if holder is not None and holder.id != employee.id:
                action = menu.addAction(f"'{code}' — taken by {holder.full_name}")
                action.setEnabled(False)
                continue
            action = menu.addAction(f"Assign '{code}'")
            action.triggered.connect(lambda _checked=False, c=code: self._on_shift_pick_changed(employee, day, c))
        if untimed:
            menu.addSeparator()
            for code in untimed:
                action = menu.addAction(f"'{code}' — no timing in this day's template…")
                action.triggered.connect(lambda _checked=False, c=code: self._on_shift_pick_changed(employee, day, c))
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen is remove_action:
            self._on_shift_pick_changed(employee, day, _NO_SHIFT)

    def _existing_shift_assignment(self, employee: Employee, day: date) -> Assignment | None:
        """Their shift that day, if it is on *this* schedule (a dealer lent
        to the supervisors that day shows nothing here)."""
        assignment = shift_on_day(self._schedule, employee.id, day)
        if assignment is None or schedule_group(assignment, employee) != self._current_subdepartment():
            return None
        return assignment

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
        # Shifts already on this day take the new template's times.
        retime_day(self._schedule, self._repository, subdepartment, day)
        self._render()
        if self._on_change:
            self._on_change()

    def _on_shift_pick_changed(self, employee: Employee, day: date, shift_code: str) -> None:
        try:
            if shift_code == _NO_SHIFT:
                clear_shift(self._schedule, self._repository, employee.id, day)
            else:
                assign_shift(self._schedule, self._repository, employee, self._current_subdepartment(), day, shift_code)
        except ShiftError as error:
            show_shift_error(self, error, self._on_open_timing)
            return
        self._render()  # Schedule/Hrs/Total Hrs columns depend on this pick
        if self._on_change:
            self._on_change()

    def _add_guest(self) -> None:
        """Bring an employee from another subdepartment here, for a period
        or permanently."""
        subdepartment = self._current_subdepartment()
        if not subdepartment:
            return
        department = next((o.department for o in self._repository.load_subdepartments() if o.name == subdepartment), "")
        candidates = [
            e
            for e in self._schedule.employees()
            if e.subdepartment != subdepartment and (not department or e.department == department)
        ]
        start = self._dates[0] if self._dates else date.today()
        end = self._dates[-1] if self._dates else start
        dialog = TransferDialog(self._schedule, subdepartment, candidates, start, end, parent=self)
        if dialog.exec() != QDialog.Accepted or dialog.employee() is None:
            return
        employee = dialog.employee()
        if dialog.permanent():
            move_permanently(self._schedule, self._repository, employee, subdepartment, date.today())
        else:
            transfer_for_period(self._schedule, self._repository, employee, subdepartment, *dialog.period())
        self._reload()
        if self._on_change:
            self._on_change()

    def _send_back(self, employee: Employee) -> None:
        """End a transfer into this subdepartment for the days on screen."""
        if not self._dates:
            return
        group = self._current_subdepartment()
        end_transfer(self._repository, employee.id, group, self._dates[0], self._dates[-1])
        # Shifts they had on this schedule those days go with them.
        for day in self._dates:
            shift = shift_on_day(self._schedule, employee.id, day)
            if shift is not None and schedule_group(shift, employee) == group:
                clear_shift(self._schedule, self._repository, employee.id, day)
        self._reload()
        if self._on_change:
            self._on_change()

    def _name_tooltip(self, row: int) -> str:
        index = row - 2
        if not (0 <= index < len(self._employees)) or not self._dates:
            return ""
        return describe_employee(
            self._schedule, self._repository, self._employees[index], self._dates[0], self._dates[-1], self._transfers
        )

    # --- drag and drop ---------------------------------------------------

    def _cell_target(self, pos: QPoint) -> tuple[Employee, date] | None:
        """The (employee, day) under a point on the grid, or None."""
        row, col = self.table.rowAt(pos.y()), self.table.columnAt(pos.x())
        index = row - 2
        day_index = (col - len(_STICKY_HEADERS)) // 3 if col >= len(_STICKY_HEADERS) else -1
        if not (0 <= index < len(self._employees)) or not (0 <= day_index < len(self._dates)):
            return None
        return self._employees[index], self._dates[day_index]

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        kind = event.type()
        frozen = getattr(self, "_frozen", None)  # events arrive while it is being built
        frozen_viewport = frozen.view.viewport() if frozen is not None else None
        on_grid = watched is self.table.viewport() or watched is frozen_viewport
        if watched is frozen_viewport and kind == QEvent.ToolTip:
            # Built on hover: it adds up hours, too slow to do for every row
            # on every render.
            text = self._name_tooltip(frozen.view.rowAt(event.pos().y()))
            if text:
                QToolTip.showText(event.globalPos(), text, frozen.view)
            else:
                QToolTip.hideText()
            return True
        if watched is frozen_viewport and kind == QEvent.ContextMenu:
            index = frozen.view.rowAt(event.pos().y()) - 2
            if 0 <= index < len(self._employees) and self._employees[index].id in self._guest_ids:
                employee = self._employees[index]
                menu = QMenu(frozen.view)
                back = menu.addAction(f"Send back to {employee.subdepartment} for these days")
                if menu.exec(event.globalPos()) is back:
                    self._send_back(employee)
            return True
        # Press on a shift badge (grid or strip) or on a "#" cell: remember
        # it; moving far enough turns it into a drag.
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if isinstance(watched, QPushButton) and watched.property("dragShift"):
                self._press = (event.globalPosition().toPoint(), "shift", watched)
            elif on_grid:
                view = self.table if watched is self.table.viewport() else frozen.view
                pos = event.position().toPoint()
                row = view.rowAt(pos.y()) - 2
                if view.columnAt(pos.x()) == 0 and 0 <= row < len(self._employees):
                    if self._employees[row].id not in self._guest_ids:
                        self._press = (event.globalPosition().toPoint(), "row", row)
        elif kind == QEvent.MouseMove and self._press is not None and event.buttons() & Qt.LeftButton:
            origin, drag_kind, payload = self._press
            if (event.globalPosition().toPoint() - origin).manhattanLength() >= QApplication.startDragDistance():
                self._press = None
                if drag_kind == "shift":
                    self._start_shift_drag(payload)
                else:
                    self._start_row_drag(payload)
                return True
        elif kind == QEvent.MouseButtonRelease:
            self._press = None
        elif on_grid and kind in (QEvent.DragEnter, QEvent.DragMove):
            mime = event.mimeData()
            if mime.hasFormat(_SHIFT_MIME):
                copy = bool(event.modifiers() & Qt.ControlModifier)
                event.setDropAction(Qt.CopyAction if copy else Qt.MoveAction)
                # DragEnter is always accepted: the strip sits above the
                # grid, so a drag enters over the day banner rows, and a
                # refused DragEnter stops Qt sending any further moves.
                # Whether the spot is droppable is decided on each move.
                over_days = watched is self.table.viewport()  # the frozen columns hold no days
                if kind == QEvent.DragEnter or (over_days and self._cell_target(event.position().toPoint()) is not None):
                    event.accept()
                else:
                    event.ignore()
                return True
            if mime.hasFormat(_ROW_MIME):
                row = self.table.rowAt(event.position().toPoint().y())
                if row >= 2:
                    self.table.selectRow(row)
                event.acceptProposedAction()
                return True
        elif on_grid and kind == QEvent.Drop:
            mime = event.mimeData()
            pos = event.position().toPoint()
            if mime.hasFormat(_SHIFT_MIME):
                payload = bytes(mime.data(_SHIFT_MIME)).decode("utf-8")
                copy = bool(event.modifiers() & Qt.ControlModifier)
                event.acceptProposedAction()
                target = self._cell_target(pos) if watched is self.table.viewport() else None
                if target is not None:
                    QTimer.singleShot(0, lambda: self._drop_shift(payload, *target, copy))
                return True
            if mime.hasFormat(_ROW_MIME):
                source = int(bytes(mime.data(_ROW_MIME)).decode())
                target = self.table.rowAt(pos.y()) - 2
                event.acceptProposedAction()
                QTimer.singleShot(0, lambda: self._move_employee_row(source, target))
                return True
        return super().eventFilter(watched, event)

    def _start_shift_drag(self, button: QPushButton) -> None:
        button.setDown(False)
        drag = QDrag(button)
        data = QMimeData()
        data.setData(_SHIFT_MIME, QByteArray(button.property("dragShift").encode("utf-8")))
        drag.setMimeData(data)
        drag.setPixmap(button.grab())
        drag.exec(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)

    def _start_row_drag(self, index: int) -> None:
        drag = QDrag(self.table)
        data = QMimeData()
        data.setData(_ROW_MIME, QByteArray(str(index).encode()))
        drag.setMimeData(data)
        view = self._frozen.view
        row_rect = view.visualRect(view.model().index(index + 2, 1))
        drag.setPixmap(view.viewport().grab(row_rect))
        drag.exec(Qt.MoveAction)

    def _drop_shift(self, payload: str, employee: Employee, day: date, copy: bool) -> None:
        code, source_employee_id, source_day = payload.split("|")
        if source_employee_id == employee.id and source_day == day.isoformat():
            return  # dropped back where it came from
        if (employee.id, day) in self._away:
            QMessageBox.information(self, "Not here that day", f"{employee.full_name} is in {self._away[(employee.id, day)]} on {day:%a %d %b}.")
            return
        group = self._current_subdepartment()
        source = self._schedule.get_employee(source_employee_id) if source_employee_id else None
        moving_same_day = source is not None and not copy and source_day == day.isoformat()
        try:
            if moving_same_day:
                # The code is the source's until it leaves them: free it first,
                # and give it back if the target cannot take it.
                clear_shift(self._schedule, self._repository, source.id, day)
                try:
                    assign_shift(self._schedule, self._repository, employee, group, day, code)
                except ShiftError:
                    assign_shift(self._schedule, self._repository, source, group, day, code)
                    raise
            else:
                assign_shift(self._schedule, self._repository, employee, group, day, code)
                if source is not None and not copy:
                    clear_shift(self._schedule, self._repository, source.id, date.fromisoformat(source_day))
        except ShiftError as error:
            show_shift_error(self, error, self._on_open_timing)
            return
        self._reload()
        if self._on_change:
            self._on_change()

    def _move_employee_row(self, source: int, target: int) -> None:
        crew = [e for e in self._employees if e.id not in self._guest_ids]
        if not 0 <= source < len(crew):
            return
        moving = crew.pop(source)
        crew.insert(max(0, min(target, len(crew))), moving)
        self._repository.save_employee_order(self._current_subdepartment(), [e.id for e in crew])
        self._reload()
