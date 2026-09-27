"""Day view tab: the position-rotation grid for one day.

One row per Shift ID on the day's schedule (the employee on it comes from
the Custom view's picks), one column per time-step slot. Each filled cell
is a real `Assignment(layer=POSITION, resource=<abbreviation>)` spanning
exactly that slot — the layer-B side of CLAUDE.md's unified model. A cell
inside the employee's shift is tinted; positions may still run outside it
(overtime), per the domain expert's call.

Layout:

* Timeline: starts at the earliest shift start in the view and runs 24
  hours. Header shows the hour on the hour (shaded) and just the minutes in
  between — "8 15 30 45 9 15 …", like the paper sheet.
* Rows: grouped by whose schedule they are on — Dealers, then a
  SUPERVISORS band, then supervisors. Someone brought in from another
  subdepartment (Custom view's "+ Add employee") shows with the group they
  work in that day, name in the accent color. Within a group, rows are ordered by shift start time;
  drag a Shift ID badge up or down to reorder — the order is remembered for
  that day.
* Template: picked per subdepartment in the banner — the same record the
  Month and Custom views set. Changing it re-times the day's shifts.
* Greyed rows: employees marked temporarily not available on this day.

Editing works like a spreadsheet: type or pick a code (picking saves at
once, into every selected cell); Ctrl+C / Ctrl+X / Ctrl+V (tab-separated,
so blocks copy to and from Excel); Ctrl+D fills down, Ctrl+R fills right;
Delete clears; Shift+F2 or right-click adds a note to a cell (a red corner
marks it, hover to read). Ctrl+mouse wheel zooms; the zoom is remembered.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from PySide6.QtCore import QByteArray, QDate, QEvent, QMimeData, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QDrag, QFont, QKeySequence, QPainter, QPen, QPolygon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import CellNote, LocationCode, Template, TemplateAssignment, natural_key
from rostify.rules.engine import RuleEngine
from rostify.services.persistence import Repository
from rostify.services.roster import describe_employee, effective_subdepartment
from rostify.services.shift_sync import (
    ShiftError,
    assign_shift,
    clear_shift,
    code_holder,
    day_timings,
    duplicate_codes,
    retime_day,
    schedule_group,
    segment_times,
    shift_on_day,
)

from ..theme import COLORS, SURFACE, TEMPLATE_COLOR_HEX, mix, qcolor
from .widgets import (
    FrozenColumns,
    ZoomControl,
    apply_table_zoom,
    centered_in_cell,
    chars_width,
    color_dot_icon,
    shift_badge_button,
    show_shift_error,
)

_DEFAULT_SLOT_MINUTES = 15
_MIN_SLOT_MINUTES, _MAX_SLOT_MINUTES = 5, 120
_DEFAULT_START_MINUTES = 6 * 60  # used when no shift in the view has a time
_WINDOW_MINUTES = 24 * 60
# Shown by default when the department has them: the rotation grid is
# mostly used for these two.
_DEFAULT_SUBDEPARTMENTS = ("Dealers", "Supervisors")
_NO_SHIFT = "— none —"
_NO_TEMPLATE = "— none —"
# Compact at 100%: a laptop screen shows a full crew without scrolling.
_ROW_HEIGHT = 26
_BADGE_SCALE = 0.75  # shift badge size relative to the Custom view's
_EDITOR_FONT_PX = 13  # the in-cell dropdown stays readable at any zoom
_ROW_MIME = "application/x-rostify-day-row"
# Sticky columns, then one column per time slot.
_COL_SHIFT_ID, _COL_LAST_NAME, _COL_FIRST_NAME, _COL_EMPLOYEE_ID = range(4)
_SLOT_COL_OFFSET = 4
_STICKY_HEADERS = ["Shift ID", "Last Name", "First Name", "Employee ID"]


# Opaque, not translucent: these are handed to QTableWidgetItem.setBackground,
# where an alpha channel would blend against the window rather than the row.
# Read at call time, not import time, so a theme switch picks them up.
def _shift_tint() -> QColor:
    return QColor(SURFACE[1])  # working hours: the plain, clean grid


def _out_of_shift_bg() -> QColor:
    return QColor(SURFACE[2])  # outside the shift: a light fill, still editable


def _qdate_to_date(qd: QDate) -> date:
    return date(qd.year(), qd.month(), qd.day())


def _date_to_qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def _format_range(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def _default_time_step(rule_engine: RuleEngine | None) -> int:
    """Seeds the Day view's own Time Step control from Settings ->
    Position rotation time step, so it starts in sync — it's a display
    convenience for this view, not a live two-way binding to that rule."""
    if rule_engine is not None:
        for rule in rule_engine.rules:
            if rule.id == "position_time_step":
                return int(rule.params.get("time_step_minutes", _DEFAULT_SLOT_MINUTES))
    return _DEFAULT_SLOT_MINUTES


@dataclass
class _Row:
    """One grid row: a group band ("SUPERVISORS"), or an employee."""

    group: str
    employee: Employee | None = None  # None = the group's band row
    shift: Assignment | None = None
    # The shift's worked periods, from the day's template timing (split
    # shifts have two). Falls back to the assignment's own span.
    periods: list[tuple[datetime, datetime]] = field(default_factory=list)
    guest: bool = False  # on this group's schedule, from another subdepartment

    @property
    def code(self) -> str:
        return self.shift.resource if self.shift is not None else ""


class _TimelineHeader(QHeaderView):
    """Column header that labels slots the way the paper sheet does: the
    hour number on a shaded cell at :00, only the minutes in between."""

    def __init__(self, panel: "DayViewPanel") -> None:
        super().__init__(Qt.Horizontal, panel.table)
        self._panel = panel
        self.setSectionsClickable(True)
        self.setHighlightSections(False)
        self.setSectionResizeMode(QHeaderView.Interactive)

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:  # noqa: N802
        if logical_index < _SLOT_COL_OFFSET:
            super().paintSection(painter, rect, logical_index)
            return
        minute = self._panel.slot_minute_of_day(logical_index - _SLOT_COL_OFFSET)
        if minute is None:
            return
        on_the_hour = minute % 60 == 0
        painter.save()
        painter.fillRect(rect, qcolor(COLORS["bg_active"] if on_the_hour else COLORS["bg_surface_alt"]))
        painter.setPen(qcolor(COLORS["border_strong"] if on_the_hour else COLORS["border"]))
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        painter.setPen(qcolor(COLORS["border"]))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        font = QFont(self._panel.table.font())  # follows the grid's zoom
        font.setBold(on_the_hour)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text_primary"] if on_the_hour else COLORS["text_secondary"]))
        label = str((minute // 60) % 24) if on_the_hour else f"{minute % 60:02d}"
        painter.drawText(rect, Qt.AlignCenter, label)
        painter.restore()


class _SlotDelegate(QStyledItemDelegate):
    """In-cell editor and painting for the grid.

    The editor is an editable combo of Location code abbreviations with
    type-to-filter; picking from the list saves at once. It keeps a
    readable size (and pops out wider than a narrow cell) whatever the zoom.
    Painting adds: an hour line, the selection (item backgrounds would hide
    the stylesheet's), a red corner for a note, and the drop line while a
    row is being dragged."""

    def __init__(self, panel: "DayViewPanel") -> None:
        super().__init__(panel)
        self._panel = panel

    def createEditor(self, parent, option, index):  # noqa: N802
        if index.column() < _SLOT_COL_OFFSET or self._panel.row_at(index.row()).employee is None:
            return None
        combo = QComboBox(parent)
        combo.setObjectName("compactCombo")
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.setStyleSheet(f"QComboBox {{ font-size: {_EDITOR_FONT_PX}px; }}")
        codes = self._panel.abbreviations()
        combo.addItem("")
        combo.addItems(codes)
        combo.view().setMinimumWidth(chars_width(combo, 10))
        combo.view().setStyleSheet(f"font-size: {_EDITOR_FONT_PX}px;")
        # Type a few letters to narrow the list, like Excel's autocomplete.
        completer = QCompleter(codes, combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.popup().setStyleSheet(f"font-size: {_EDITOR_FONT_PX}px;")
        combo.setCompleter(completer)
        combo.activated.connect(lambda _index, c=combo: self._commit_and_close(c))
        return combo

    def updateEditorGeometry(self, editor, option, index) -> None:  # noqa: N802
        rect = QRect(option.rect)
        rect.setWidth(max(rect.width(), chars_width(editor, 7)))
        rect.setHeight(max(rect.height(), 26))
        editor.setGeometry(rect)

    def _commit_and_close(self, combo: QComboBox) -> None:
        self.commitData.emit(combo)
        self.closeEditor.emit(combo, QStyledItemDelegate.NoHint)

    def setEditorData(self, editor: QComboBox, index) -> None:  # noqa: N802
        editor.setCurrentText(index.data(Qt.EditRole) or "")
        editor.lineEdit().selectAll()

    def setModelData(self, editor: QComboBox, model, index) -> None:  # noqa: N802
        model.setData(index, editor.currentText().strip(), Qt.EditRole)

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        panel = self._panel
        rect = option.rect
        painter.save()
        slot = index.column() - _SLOT_COL_OFFSET
        if slot >= 0:
            # Grid lines drawn over the cell: the shift tint is an item
            # background, and the view's own faint grid got lost under it.
            painter.setPen(QPen(qcolor(COLORS["border"]), 1))
            painter.drawLine(rect.topRight(), rect.bottomRight())
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())
            minute = panel.slot_minute_of_day(slot)
            if minute is not None and minute % 60 == 0:
                painter.setPen(QPen(qcolor(COLORS["text_tertiary"]), 1))
                painter.drawLine(rect.topLeft(), rect.bottomLeft())
            if panel.note_at(index.row(), slot) is not None:
                size = max(6, min(rect.height() // 3, 10))
                corner = QPolygon(
                    [rect.topRight() + QPoint(-size, 0), rect.topRight() + QPoint(1, 0), rect.topRight() + QPoint(1, size)]
                )
                painter.setPen(Qt.NoPen)
                painter.setBrush(qcolor(COLORS["danger"]))
                painter.drawPolygon(corner)
        if option.state & QStyle.State_Selected:
            accent = QColor(COLORS["accent"])
            wash = QColor(accent)
            wash.setAlphaF(0.28)
            painter.fillRect(rect, wash)
            painter.setPen(QPen(accent, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        if panel.drop_row == index.row():
            painter.setPen(QPen(QColor(COLORS["accent"]), 3))
            painter.drawLine(rect.topLeft(), rect.topRight())
        painter.restore()


class DayViewPanel(QWidget):
    def __init__(
        self,
        schedule: Schedule,
        repository: Repository,
        rule_engine: RuleEngine | None = None,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
        zoom: float = 1.0,
        on_zoom_changed: Callable[[float], None] | None = None,
        department: str = "",
        on_open_timing: Callable | None = None,
    ) -> None:
        """The Schedule page shows `subdepartment_button` on the left of its
        top row, and `period_controls` and `zoom_control` on the right."""
        super().__init__(parent)
        self._schedule = schedule
        self._repository = repository
        self._on_change = on_change
        self._on_zoom_changed = on_zoom_changed
        self._on_open_timing = on_open_timing  # (group, code, day) -> jump to Templates
        self._rows: list[_Row] = []
        self._shift_colors: dict[tuple[str, str], str] = {}  # (group, code) -> TEMPLATE_COLORS name
        self._location_codes: list[LocationCode] = []
        self._location_by_abbr: dict[str, LocationCode] = {}
        self._notes: dict[tuple[int, int], CellNote] = {}  # (row, slot) -> note
        self._rendering = False  # guards itemChanged while _render fills the grid
        self._slot_minutes = _default_time_step(rule_engine)
        self._window_start_minutes = _DEFAULT_START_MINUTES
        # Column widths are set to defaults once, and again for the slot
        # columns only when the time step changes — never on an ordinary
        # re-render, so a width the user dragged stays put after an edit.
        self._sticky_sized = False
        self._sized_slot_minutes: int | None = None
        self.drop_row: int | None = None  # row under a Shift ID drag
        self._badge_press: tuple[QPoint, int] | None = None

        self.date_edit = QDateEdit(_date_to_qdate(date.today()))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setToolTip("Day shown")
        self.date_edit.dateChanged.connect(lambda _: self._reload())

        # Multi-select checkbox menu, not a single-pick combo — lets a
        # supervisor see Dealers and Supervisors together or just one.
        # A QPushButton, not a QToolButton: the global sheet styles
        # QPushButton, and an unstyled QToolButton renders as a native
        # Windows control next to styled neighbours.
        self.subdepartment_button = QPushButton()
        self.subdepartment_button.setToolTip("Which subdepartments' schedules to show — tick one or more")
        self._subdepartment_menu = QMenu(self.subdepartment_button)
        self._subdepartment_actions = {}
        names = [o.name for o in repository.load_subdepartments(department or None)]
        defaults = [n for n in names if n in _DEFAULT_SUBDEPARTMENTS] or names[:1]
        self._subdepartments = names
        for sub in names:
            action = self._subdepartment_menu.addAction(sub)
            action.setCheckable(True)
            action.setChecked(sub in defaults)
            action.toggled.connect(self._on_subdepartment_toggled)
            self._subdepartment_actions[sub] = action
        self.subdepartment_button.setMenu(self._subdepartment_menu)
        self.subdepartment_button.setMinimumWidth(chars_width(self, 18))
        self._update_subdepartment_button_text()

        # A spin box: takes a freely typed number, already styled.
        self.time_step_spin = QSpinBox()
        self.time_step_spin.setRange(_MIN_SLOT_MINUTES, _MAX_SLOT_MINUTES)
        self.time_step_spin.setSingleStep(5)
        self.time_step_spin.setSuffix(" min")
        self.time_step_spin.setValue(self._slot_minutes)
        self.time_step_spin.setKeyboardTracking(False)  # fires once the number is finished, not per digit
        self.time_step_spin.setFixedWidth(chars_width(self, 10))
        self.time_step_spin.setToolTip("Minutes per column")
        self.time_step_spin.valueChanged.connect(self._on_time_step_changed)

        self.period_controls = QWidget()
        period_row = QHBoxLayout(self.period_controls)
        period_row.setContentsMargins(0, 0, 0, 0)
        period_row.setSpacing(8)
        period_row.addWidget(QLabel("Date"))
        period_row.addWidget(self.date_edit)
        period_row.addSpacing(4)
        period_row.addWidget(QLabel("Step"))
        period_row.addWidget(self.time_step_spin)


        # Banner: [big day number] Weekday, Month Year | template pickers
        # (matches reference/RostaStudioSchedule.jsx's Day view header)
        self.banner = QFrame()
        self.banner.setObjectName("dayViewBanner")
        self.banner.setStyleSheet(
            f"QFrame#dayViewBanner {{ border: 1px solid {COLORS['border_default']}; border-radius: 12px; }}"
        )
        self.day_number_label = QLabel("")
        self.day_number_label.setStyleSheet(
            f"border: none; border-radius: 22px; background: {COLORS['accent']}; color: {COLORS['accent_on']}; "
            f"font-size: 20px; font-weight: 700;"
        )
        self.day_number_label.setFixedSize(44, 44)
        self.day_number_label.setAlignment(Qt.AlignCenter)
        self.weekday_label = QLabel("")
        self.weekday_label.setStyleSheet("border: none; font-weight: 700; font-size: 14px;")
        self.month_label = QLabel("")
        self.month_label.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']}; font-size: 11px;")
        date_col = QVBoxLayout()
        date_col.setSpacing(0)
        date_col.addWidget(self.weekday_label)
        date_col.addWidget(self.month_label)

        # One Template picker per shown subdepartment, rebuilt with the day.
        self._template_row = QHBoxLayout()
        self._template_row.setSpacing(8)

        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)
        banner_layout.addWidget(self.day_number_label)
        banner_layout.addLayout(date_col)
        banner_layout.addSpacing(16)
        banner_layout.addLayout(self._template_row)
        banner_layout.addStretch(1)

        self.table = QTableWidget()
        self.table.setHorizontalHeader(_TimelineHeader(self))
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self.table.setItemDelegate(_SlotDelegate(self))
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.installEventFilter(self)  # Excel keys
        self.table.viewport().setAcceptDrops(True)
        self.table.viewport().installEventFilter(self)  # Shift ID row drops
        # Shift ID, names and Employee ID stay put while the timeline scrolls.
        self._frozen = FrozenColumns(self.table, _SLOT_COL_OFFSET)
        self._frozen.view.setItemDelegate(self.table.itemDelegate())
        self._frozen.view.viewport().setAcceptDrops(True)
        self._frozen.view.viewport().installEventFilter(self)
        self._frozen.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._frozen.view.customContextMenuRequested.connect(
            lambda pos: self._context_menu(self._frozen.view.indexAt(pos), self._frozen.view.viewport().mapToGlobal(pos))
        )

        self._zoom = 0.0  # set by _apply_zoom below
        self.zoom_control = ZoomControl(self.table, zoom)
        self.zoom_control.zoom_changed.connect(self._on_zoom)
        self._apply_zoom(self.zoom_control.zoom())

        layout = QVBoxLayout(self)
        layout.addWidget(self.banner)
        layout.addWidget(self.table, stretch=1)
        # Filled in showEvent, not here: nothing is read until the page is
        # actually opened.

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._reload()

    def reload(self) -> None:
        self._reload()

    # --- small queries used by the header and delegate -----------------------

    def row_at(self, row: int) -> _Row:
        return self._rows[row] if 0 <= row < len(self._rows) else _Row(group="")

    def abbreviations(self) -> list[str]:
        return [lc.abbreviation for lc in self._location_codes]

    def slot_minute_of_day(self, slot: int) -> int | None:
        """Minutes since the day's midnight for this slot (may pass 1440)."""
        if not 0 <= slot < self._slot_count():
            return None
        return self._window_start_minutes + slot * self._slot_minutes

    def note_at(self, row: int, slot: int) -> CellNote | None:
        return self._notes.get((row, slot))

    def _slot_count(self) -> int:
        return _WINDOW_MINUTES // self._slot_minutes

    def _current_date(self) -> date:
        return _qdate_to_date(self.date_edit.date())

    def _selected_subdepartments(self) -> list[str]:
        return [s for s in self._subdepartments if self._subdepartment_actions[s].isChecked()]

    def _update_subdepartment_button_text(self) -> None:
        selected = self._selected_subdepartments()
        if len(selected) == len(self._subdepartments) and len(selected) > 1:
            text = "All"
        else:
            text = ", ".join(selected) if selected else "None"
        self.subdepartment_button.setText(text)

    def _on_subdepartment_toggled(self, _checked: bool) -> None:
        if not any(a.isChecked() for a in self._subdepartment_actions.values()):
            self.sender().setChecked(True)  # always keep at least one selected
            return
        self._update_subdepartment_button_text()
        self._reload()

    # --- loading -------------------------------------------------

    def _reload(self) -> None:
        if not self.isVisible():
            return  # showEvent reloads when the page is opened
        day = self._current_date()
        groups = self._selected_subdepartments()
        self._location_codes = self._repository.load_location_codes()
        self._location_by_abbr = {lc.abbreviation: lc for lc in self._location_codes}
        # Each Shift ID owns its badge color, so the Day view badge matches
        # the same code's badge in the Custom view.
        self._shift_colors = {
            (group, shift_id.code): shift_id.color
            for group in groups
            for shift_id in self._repository.load_shift_ids(group)
        }
        self._rows = self._build_rows(day, groups)
        self._window_start_minutes = self._timeline_start(day, groups)
        self._render()
        self._update_banner(day, groups)

    def _build_rows(self, day: date, groups: list[str]) -> list[_Row]:
        timings = {group: day_timings(self._repository, group, day) for group in groups}
        transfers = self._repository.load_transfers()
        self._duplicates = {group: duplicate_codes(self._schedule, group, day) for group in groups}
        shifts = {a.employee_id: a for a in self._schedule.assignments(on=day, layer=Layer.SHIFT)}
        rows: list[_Row] = []
        for group in groups:
            members: list[_Row] = []
            for employee in self._schedule.employees():
                shift = shifts.get(employee.id)
                on_group = (
                    schedule_group(shift, employee)
                    if shift is not None
                    else effective_subdepartment(employee, day, transfers)
                )
                if on_group != group:
                    continue
                periods: list[tuple[datetime, datetime]] = []
                if shift is not None:
                    timing = timings[group].get(shift.resource)
                    periods = (
                        [segment_times(segment, day) for segment in timing.segments]
                        if timing is not None
                        else [(shift.start, shift.end)]
                    )
                members.append(
                    _Row(group, employee, shift, periods, guest=employee.subdepartment != group)
                )
            saved_order = {
                employee_id: i for i, employee_id in enumerate(self._repository.load_day_row_order(group, day))
            }

            def sort_key(row: _Row):
                if row.shift is None:  # no shift today: at the bottom, by name
                    return (2, 0, [], row.employee.last_name, row.employee.first_name)
                start = row.periods[0][0] if row.periods else row.shift.start
                if row.employee.id in saved_order:
                    return (0, saved_order[row.employee.id], [], "", "")
                return (1, start, natural_key(row.code), "", "")

            # Rows that were dragged into place come first in that order;
            # the rest by start time.
            members.sort(key=sort_key)
            if len(groups) > 1 and members:
                rows.append(_Row(group))  # the group band
            rows.extend(members)
        return rows

    def _timeline_start(self, day: date, groups: list[str]) -> int:
        """Earliest shift start among the rows; else the earliest timing in
        the day's templates; else 06:00. Snapped down to the time step."""
        midnight = datetime.combine(day, datetime.min.time())
        starts = [int((row.periods[0][0] - midnight).total_seconds() // 60) for row in self._rows if row.periods]
        if not starts:
            starts = [
                segment.start_minutes
                for group in groups
                for timing in day_timings(self._repository, group, day).values()
                for segment in timing.segments
            ]
        start = min(starts) if starts else _DEFAULT_START_MINUTES
        return max(start - start % self._slot_minutes, 0)

    def _on_time_step_changed(self, minutes: int) -> None:
        if minutes == self._slot_minutes:
            return
        self._slot_minutes = minutes
        self._reload()

    # --- time helpers -------------------------------------------------

    def _window(self) -> tuple[datetime, datetime]:
        midnight = datetime.combine(self._current_date(), datetime.min.time())
        start = midnight + timedelta(minutes=self._window_start_minutes)
        return start, start + timedelta(minutes=_WINDOW_MINUTES)

    def _slot_range(self, slot: int) -> tuple[datetime, datetime]:
        midnight = datetime.combine(self._current_date(), datetime.min.time())
        start = midnight + timedelta(minutes=self._window_start_minutes + slot * self._slot_minutes)
        return start, start + timedelta(minutes=self._slot_minutes)

    def _positions_in_window(self, employee_id: str) -> list[Assignment]:
        window_start, window_end = self._window()
        return [
            a
            for a in self._schedule.assignments(employee_id=employee_id, layer=Layer.POSITION)
            if a.start < window_end and window_start < a.end
        ]

    @staticmethod
    def _covering(assignments: list[Assignment], slot_start: datetime, slot_end: datetime) -> Assignment | None:
        return next((a for a in assignments if a.start < slot_end and slot_start < a.end), None)

    def _template_for_subdepartment(self, day: date, subdepartment: str) -> Template | None:
        assignment = self._repository.load_template_assignment(subdepartment, day)
        if assignment is None:
            return None
        return next((t for t in self._repository.load_templates(subdepartment) if t.id == assignment.template_id), None)

    # --- banner -------------------------------------------------

    def _update_banner(self, day: date, subdepartments: list[str]) -> None:
        self.day_number_label.setText(str(day.day))
        self.weekday_label.setText(day.strftime("%A"))
        self.month_label.setText(day.strftime("%B %Y"))

        while self._template_row.count():
            widget = self._template_row.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()

        for subdepartment in subdepartments:
            templates = sorted(self._repository.load_templates(subdepartment), key=lambda t: natural_key(t.name))
            current = self._template_for_subdepartment(day, subdepartment)
            label = QLabel(f"{subdepartment}:")
            label.setStyleSheet("border: none; font-weight: 700;")
            combo = QComboBox()
            combo.addItem(_NO_TEMPLATE)
            for template in templates:
                combo.addItem(
                    color_dot_icon(TEMPLATE_COLOR_HEX.get(template.color, TEMPLATE_COLOR_HEX["blue"])),
                    template.name,
                )
            if current is not None:
                combo.setCurrentText(current.name)
            combo.setToolTip(f"Template for {subdepartment} on this day")
            combo.activated.connect(
                lambda _index, c=combo, sub=subdepartment: self._on_template_picked(sub, c.currentText())
            )
            # The template's comment sits under its picker, small; nothing
            # when there is none.
            picker = QWidget()
            picker.setProperty("transparentBg", True)
            column = QVBoxLayout(picker)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(0)
            column.addWidget(combo)
            if current is not None and current.subtitle:
                comment = QLabel(current.subtitle)
                comment.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']}; font-size: 11px;")
                comment.setToolTip(current.subtitle)
                comment.setMaximumWidth(combo.sizeHint().width() + 60)
                column.addWidget(comment)
            self._template_row.addWidget(label)
            self._template_row.addWidget(picker)

    def _on_template_picked(self, subdepartment: str, template_name: str) -> None:
        day = self._current_date()
        if template_name == _NO_TEMPLATE:
            self._repository.delete_template_assignment(subdepartment, day)
        else:
            template = next((t for t in self._repository.load_templates(subdepartment) if t.name == template_name), None)
            if template is None:
                return
            self._repository.save_template_assignment(
                TemplateAssignment(subdepartment=subdepartment, date=day, template_id=template.id)
            )
        # Shifts already on this day take the new template's times.
        retime_day(self._schedule, self._repository, subdepartment, day)
        # Deferred: this runs inside the combo that the reload replaces.
        QTimer.singleShot(0, self._reload)
        if self._on_change:
            self._on_change()

    # --- zoom -------------------------------------------------

    def _apply_zoom(self, zoom: float) -> None:
        apply_table_zoom(self.table, zoom, self._zoom)
        self._zoom = zoom
        self.table.verticalHeader().setDefaultSectionSize(round(_ROW_HEIGHT * zoom))

    def _on_zoom(self, zoom: float) -> None:
        self._apply_zoom(zoom)
        self._render()
        if self._on_zoom_changed:
            self._on_zoom_changed(zoom)

    # --- rendering -------------------------------------------------

    def _render(self) -> None:
        table = self.table
        self._rendering = True  # setItem below would otherwise fire _on_item_changed
        try:
            slot_count = self._slot_count()
            table.clearSpans()
            table.setRowCount(len(self._rows))
            table.setColumnCount(_SLOT_COL_OFFSET + slot_count)
            table.setHorizontalHeaderLabels(_STICKY_HEADERS + [""] * slot_count)
            row_height = round(_ROW_HEIGHT * self._zoom)
            window_start, window_end = self._window()
            day = self._current_date()

            self._notes = {}
            row_of_employee = {row.employee.id: i for i, row in enumerate(self._rows) if row.employee is not None}
            for note in self._repository.load_cell_notes(window_start, window_end):
                if note.employee_id in row_of_employee:
                    slot = int((note.at - window_start).total_seconds() // 60) // self._slot_minutes
                    self._notes[(row_of_employee[note.employee_id], slot)] = note

            for row, entry in enumerate(self._rows):
                table.setRowHeight(row, row_height)
                if entry.employee is None:
                    self._render_band(row, entry.group, slot_count)
                    continue
                employee = entry.employee
                unavailable = employee.is_unavailable_on(day)
                color_name = self._shift_colors.get((entry.group, entry.code))
                # A fresh empty item under the badge: a row that was a group
                # band in the last render still held its "DEALERS" text here.
                blank = QTableWidgetItem("")
                blank.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(row, _COL_SHIFT_ID, blank)
                self._frozen.set_cell_widget(
                    row, _COL_SHIFT_ID, centered_in_cell(self._build_shift_badge(row, entry, color_name))
                )

                for col, value in (
                    (_COL_LAST_NAME, employee.last_name),
                    (_COL_FIRST_NAME, employee.first_name),
                    (_COL_EMPLOYEE_ID, employee.id),
                ):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if unavailable:
                        item.setForeground(QColor(COLORS["text_tertiary"]))
                    elif entry.guest:
                        item.setForeground(QColor(COLORS["accent"]))
                    table.setItem(row, col, item)

                positions = self._positions_in_window(employee.id)
                for slot in range(slot_count):
                    slot_start, slot_end = self._slot_range(slot)
                    in_shift = any(start < slot_end and slot_start < end for start, end in entry.periods)
                    position = self._covering(positions, slot_start, slot_end)

                    item = QTableWidgetItem(position.resource if position else "")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setBackground(_shift_tint() if in_shift and not unavailable else _out_of_shift_bg())
                    if not in_shift or unavailable:
                        item.setForeground(QColor(COLORS["text_tertiary"]))

                    tips = []
                    if in_shift and entry.shift is not None:
                        periods = ", ".join(_format_range(start, end) for start, end in entry.periods)
                        tips.append(f"Shift {entry.code}: {periods}")
                    if position is not None:
                        location = self._location_by_abbr.get(position.resource)
                        if location is not None:
                            tips.append(f"{location.abbreviation} — {location.description} ({location.group})")
                        if position.comment:
                            tips.append(f"Comment: {position.comment}")
                    note = self._notes.get((row, slot))
                    if note is not None:
                        tips.append(f"Note: {note.text}")
                    item.setToolTip("\n".join(tips) if tips else "Pick or type a location for this slot.")
                    table.setItem(row, _SLOT_COL_OFFSET + slot, item)

            header = table.horizontalHeader()
            if not self._sticky_sized:
                header.resizeSection(_COL_SHIFT_ID, chars_width(table, 7))
                for col in (_COL_LAST_NAME, _COL_FIRST_NAME, _COL_EMPLOYEE_ID):
                    header.resizeSection(col, chars_width(table, 14))
                self._sticky_sized = True
            if self._sized_slot_minutes != self._slot_minutes:
                # Narrow: a slot shows 2-3 characters ("15", "B1").
                short_width = chars_width(table, 3)
                for col in range(_SLOT_COL_OFFSET, table.columnCount()):
                    header.resizeSection(col, short_width)
                self._sized_slot_minutes = self._slot_minutes
            header.viewport().update()
            self._frozen.sync()
        finally:
            self._rendering = False

    def _render_band(self, row: int, group: str, slot_count: int) -> None:
        """The "SUPERVISORS" style band that opens a group."""
        table = self.table
        table.removeCellWidget(row, _COL_SHIFT_ID)
        item = QTableWidgetItem(group.upper())
        item.setFlags(Qt.ItemIsEnabled)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setBackground(QColor(mix(COLORS["accent"], SURFACE[1], 0.35)))
        item.setForeground(QColor(COLORS["text_primary"]))
        table.setItem(row, 0, item)
        table.setSpan(row, 0, 1, _SLOT_COL_OFFSET + slot_count)
        self._frozen.view.setIndexWidget(table.model().index(row, _COL_SHIFT_ID), None)

    def _build_shift_badge(self, row: int, entry: _Row, color_name: str | None) -> QWidget:
        """The same colored badge the Custom view uses; the dashed `+` when
        the employee has no shift today. Drag a badge up or down to reorder
        the shifts; click it to change the shift."""
        hex_color = TEMPLATE_COLOR_HEX.get(color_name or "", TEMPLATE_COLOR_HEX["blue"]) if color_name else None
        code = entry.code
        button = shift_badge_button(
            code,
            hex_color,
            f"Shift {code} — click to change, drag up or down to reorder" if code else "Add a shift ID for this employee",
            scale=self._zoom * _BADGE_SCALE,
        )
        button.setProperty("dayRow", row)
        button.clicked.connect(lambda _=False, r=row: self._edit_shift_id(r))
        if code and code in getattr(self, "_duplicates", {}).get(entry.group, set()):
            # Data from before the one-person-per-Shift-ID check.
            button.setStyleSheet(button.styleSheet() + f" border: 2px solid {COLORS['danger']};")
            button.setToolTip(f"'{code}' is given to more than one person today — change one of them")
        if code:
            button.installEventFilter(self)
        return button

    # --- Shift ID row drag -------------------------------------------------

    def _handle_badge_event(self, button: QPushButton, event) -> bool:
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._badge_press = (event.position().toPoint(), button.property("dayRow"))
        elif event.type() == QEvent.MouseMove and self._badge_press is not None and event.buttons() & Qt.LeftButton:
            origin, row = self._badge_press
            if (event.position().toPoint() - origin).manhattanLength() >= QApplication.startDragDistance():
                self._badge_press = None
                button.setDown(False)
                drag = QDrag(button)
                data = QMimeData()
                data.setData(_ROW_MIME, QByteArray(str(row).encode()))
                drag.setMimeData(data)
                drag.setPixmap(button.grab())
                drag.exec(Qt.MoveAction)
                self.drop_row = None
                self.table.viewport().update()
                return True
        elif event.type() == QEvent.MouseButtonRelease:
            self._badge_press = None
        return False

    def _drop_target(self, pos: QPoint, source: int) -> int | None:
        """Row a dragged Shift ID row would land before, within its group.
        Past the group's last shift row means "after the last one"."""
        target = self.table.rowAt(pos.y())
        group = self.row_at(source).group
        shift_rows = [i for i, r in enumerate(self._rows) if r.employee is not None and r.group == group and r.shift]
        if not shift_rows:
            return None
        if target < 0 or target > shift_rows[-1]:
            return shift_rows[-1] + 1
        if target < shift_rows[0]:
            return shift_rows[0]
        return target if target in shift_rows else shift_rows[-1] + 1

    def _handle_viewport_drag(self, event) -> bool:
        if event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if not event.mimeData().hasFormat(_ROW_MIME):
                return False
            source = int(bytes(event.mimeData().data(_ROW_MIME)).decode())
            target = self._drop_target(event.position().toPoint(), source)
            self.drop_row = target
            self.table.viewport().update()
            # DragEnter is always accepted — a refused DragEnter stops Qt
            # sending any further moves to the grid.
            if target is None and event.type() == QEvent.DragMove:
                event.ignore()
            else:
                event.acceptProposedAction()
            return True
        if event.type() == QEvent.DragLeave:
            self.drop_row = None
            self.table.viewport().update()
            return False
        if event.type() == QEvent.Drop and event.mimeData().hasFormat(_ROW_MIME):
            source = int(bytes(event.mimeData().data(_ROW_MIME)).decode())
            target = self._drop_target(event.position().toPoint(), source)
            self.drop_row = None
            event.acceptProposedAction()
            if target is not None:
                QTimer.singleShot(0, lambda: self._move_shift_row(source, target))
            return True
        return False

    def _move_shift_row(self, source: int, target: int) -> None:
        """Save the new order of the group's Shift IDs for this day."""
        group = self.row_at(source).group
        shift_rows = [i for i, r in enumerate(self._rows) if r.employee is not None and r.group == group and r.shift]
        order = [self._rows[i].employee.id for i in shift_rows]
        moving = self._rows[source].employee.id
        before = self._rows[target].employee.id if target < len(self._rows) and target in shift_rows else None
        order.remove(moving)
        order.insert(order.index(before) if before in order else len(order), moving)
        self._repository.save_day_row_order(group, self._current_date(), order)
        self._reload()

    # --- editing -------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """An in-cell edit landed. If several slot cells are selected and the
        edited one is among them, the value goes into all of them."""
        if self._rendering or item.column() < _SLOT_COL_OFFSET or self.row_at(item.row()).employee is None:
            return
        text = item.text().strip()
        targets = self._selected_slot_cells()
        if (item.row(), item.column()) not in targets:
            targets = [(item.row(), item.column())]
        # Deferred: writing re-renders the grid, which replaces this item
        # while Qt is still inside its itemChanged signal.
        QTimer.singleShot(0, lambda: self._write_cells([(row, col, text) for row, col in targets]))

    def _selected_slot_cells(self) -> list[tuple[int, int]]:
        return sorted(
            (index.row(), index.column())
            for index in self.table.selectedIndexes()
            if index.column() >= _SLOT_COL_OFFSET and self.row_at(index.row()).employee is not None
        )

    def _write_cells(self, cells: list[tuple[int, int, str]]) -> None:
        """Write many slot cells at once — one re-render and one save at the
        end, however many cells. Used by typing, paste, fill and clear."""
        changed = False
        for row, col, abbreviation in cells:
            employee = self.row_at(row).employee
            if employee is not None and col >= _SLOT_COL_OFFSET:
                changed |= self._set_position(employee, col - _SLOT_COL_OFFSET, abbreviation)
        self._render()
        if changed and self._on_change:
            self._on_change()

    def _set_position(self, employee: Employee, slot: int, abbreviation: str) -> bool:
        """Replace whatever POSITION assignment covers this slot with
        `abbreviation` (empty clears it). Does not re-render. Returns
        whether anything changed."""
        if not 0 <= slot < self._slot_count():
            return False
        slot_start, slot_end = self._slot_range(slot)
        existing = self._covering(self._positions_in_window(employee.id), slot_start, slot_end)
        if existing is None and not abbreviation:
            return False
        if existing is not None and existing.resource == abbreviation:
            return False
        if existing is not None:
            self._schedule.remove_assignment(existing.id)
            self._repository.delete_assignment(existing.id)
        if abbreviation:
            assignment = Assignment(
                employee_id=employee.id,
                start=slot_start,
                end=slot_end,
                resource=abbreviation,
                layer=Layer.POSITION,
                department=employee.department,
                comment=existing.comment if existing else "",
            )
            self._schedule.add_assignment(assignment)
            self._repository.save_assignment(assignment)
        return True

    # --- Excel keys -------------------------------------------------

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if isinstance(watched, QPushButton) and watched.property("dayRow") is not None:
            return self._handle_badge_event(watched, event)
        frozen_view = getattr(self, "_frozen", None)
        if frozen_view is not None and watched is frozen_view.view.viewport() and event.type() == QEvent.ToolTip:
            index = frozen_view.view.indexAt(event.pos())
            employee = self.row_at(index.row()).employee if index.isValid() else None
            if employee is not None and index.column() != _COL_SHIFT_ID:
                day = self._current_date()
                QToolTip.showText(
                    event.globalPos(),
                    describe_employee(
                        self._schedule, self._repository, employee, day, day, self._repository.load_transfers()
                    ),
                    frozen_view.view,
                )
                return True
        frozen = getattr(self, "_frozen", None)  # events arrive while it is being built
        if watched is self.table.viewport() or (frozen is not None and watched is frozen.view.viewport()):
            return self._handle_viewport_drag(event)
        if watched is self.table and event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Copy):
                self._copy_selection()
                return True
            if event.matches(QKeySequence.Cut):
                self._copy_selection()
                self._clear_selection()
                return True
            if event.matches(QKeySequence.Paste):
                self._paste()
                return True
            if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
                self._fill(down=True)
                return True
            if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_R:
                self._fill(down=False)
                return True
            if event.modifiers() == Qt.ShiftModifier and event.key() == Qt.Key_F2:
                index = self.table.currentIndex()
                if index.isValid():
                    self._edit_note(index.row(), index.column())
                return True
            if event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and not event.modifiers():
                self._clear_selection()
                return True
        return super().eventFilter(watched, event)

    def _cell_text(self, row: int, col: int) -> str:
        if col == _COL_SHIFT_ID:
            return self.row_at(row).code
        item = self.table.item(row, col)
        return item.text() if item is not None else ""

    def _selection_box(self) -> tuple[int, int, int, int] | None:
        """(top, left, bottom, right) around everything selected."""
        ranges = self.table.selectedRanges()
        if not ranges:
            return None
        return (
            min(r.topRow() for r in ranges),
            min(r.leftColumn() for r in ranges),
            max(r.bottomRow() for r in ranges),
            max(r.rightColumn() for r in ranges),
        )

    def _copy_selection(self) -> None:
        box = self._selection_box()
        if box is None:
            return
        top, left, bottom, right = box
        lines = [
            "\t".join(self._cell_text(row, col) for col in range(left, right + 1))
            for row in range(top, bottom + 1)
            if self.row_at(row).employee is not None
        ]
        QApplication.clipboard().setText("\n".join(lines))

    def _paste(self) -> None:
        text = QApplication.clipboard().text()
        if not text:
            return
        block = [line.split("\t") for line in text.rstrip("\r\n").replace("\r\n", "\n").split("\n")]
        box = self._selection_box()
        if box is None:
            return
        if len(block) == 1 and len(block[0]) == 1:
            # One value: into every selected cell, like Excel.
            value = block[0][0].strip()
            self._write_cells([(row, col, value) for row, col in self._selected_slot_cells()])
            return
        top, left, _, _ = box
        # Band rows are skipped, the way Excel skips nothing — but a band
        # holds no data, so the block continues on the next employee row.
        employee_rows = [i for i in range(top, len(self._rows)) if self._rows[i].employee is not None]
        cells = []
        for r, values in enumerate(block):
            if r >= len(employee_rows):
                break
            for c, value in enumerate(values):
                cells.append((employee_rows[r], left + c, value.strip()))
        self._write_cells([cell for cell in cells if cell[1] < self.table.columnCount()])

    def _fill(self, down: bool) -> None:
        """Ctrl+D: each column's top cell into the cells below it. Ctrl+R:
        each row's left cell into the cells to its right."""
        cells = []
        for selected in self.table.selectedRanges():
            top, left = selected.topRow(), selected.leftColumn()
            for row in range(top, selected.bottomRow() + 1):
                for col in range(max(left, _SLOT_COL_OFFSET), selected.rightColumn() + 1):
                    source = (top, col) if down else (row, left)
                    if (row, col) != source:
                        cells.append((row, col, self._cell_text(*source)))
        if cells:
            self._write_cells(cells)

    def _clear_selection(self) -> None:
        self._write_cells([(row, col, "") for row, col in self._selected_slot_cells()])

    # --- notes -------------------------------------------------

    def _edit_note(self, row: int, col: int) -> None:
        employee = self.row_at(row).employee
        slot = col - _SLOT_COL_OFFSET
        if employee is None or slot < 0:
            return
        existing = self._notes.get((row, slot))
        slot_start, _ = self._slot_range(slot)
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Note",
            f"{employee.full_name}, {slot_start.strftime('%H:%M')}",
            existing.text if existing else "",
        )
        if not ok:
            return
        at = existing.at if existing else slot_start
        if text.strip():
            self._repository.save_cell_note(CellNote(employee_id=employee.id, at=at, text=text.strip()))
        elif existing is not None:
            self._repository.delete_cell_note(employee.id, at)
        self._render()

    def _delete_note(self, row: int, col: int) -> None:
        note = self._notes.get((row, col - _SLOT_COL_OFFSET))
        if note is not None:
            self._repository.delete_cell_note(note.employee_id, note.at)
            self._render()

    # --- shifts -------------------------------------------------

    def _edit_shift_id(self, row: int) -> None:
        entry = self.row_at(row)
        employee = entry.employee
        if employee is None:
            return
        day = self._current_date()
        timed = set(day_timings(self._repository, entry.group, day))
        # Every Shift ID of the schedule; ones without a timing today are
        # marked, and picking one offers the jump to set it.
        codes = sorted({s.code for s in self._repository.load_shift_ids(entry.group)} | timed, key=natural_key)
        current = entry.code

        dialog = QDialog(self)
        dialog.setWindowTitle("Set shift ID")
        combo = QComboBox()
        combo.addItem(_NO_SHIFT)
        for code in codes:
            holder = code_holder(self._schedule, entry.group, day, code)
            if holder is not None and holder.id != employee.id:
                combo.addItem(f"{code} — taken by {holder.full_name}", code)
                # A Shift ID is one person's slot: taken ones cannot be picked.
                combo.model().item(combo.count() - 1).setEnabled(False)
            elif code not in timed:
                combo.addItem(f"{code} — no timing today", code)
            else:
                combo.addItem(code, code)
        if current:
            combo.setCurrentIndex(max(combo.findData(current), 0))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Shift ID on the {entry.group} schedule for this day"))
        layout.addWidget(combo)
        if not codes:
            hint = QLabel("No template with timings on this day yet — pick one in the banner above.")
            hint.setProperty("role", "hint")
            layout.addWidget(hint)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        new_code = combo.currentData() or ""
        if new_code == current:
            return
        try:
            if new_code:
                assign_shift(self._schedule, self._repository, employee, entry.group, day, new_code)
            else:
                clear_shift(self._schedule, self._repository, employee.id, day)
        except ShiftError as error:
            show_shift_error(self, error, self._on_open_timing)
            return
        self._reload()
        if self._on_change:
            self._on_change()

    def _show_context_menu(self, position) -> None:
        self._context_menu(self.table.indexAt(position), self.table.viewport().mapToGlobal(position))

    def _context_menu(self, index, global_pos) -> None:
        if not index.isValid() or self.row_at(index.row()).employee is None:
            return
        entry = self.row_at(index.row())
        menu = QMenu(self.table)
        actions = {}
        if index.column() == _COL_SHIFT_ID:
            actions[menu.addAction("Set shift ID")] = lambda: self._edit_shift_id(index.row())
            if entry.guest and entry.shift is not None:
                actions[menu.addAction(f"Remove from {entry.group} for this day")] = lambda: self._remove_guest(entry)
        elif index.column() >= _SLOT_COL_OFFSET:
            has_note = self._notes.get((index.row(), index.column() - _SLOT_COL_OFFSET)) is not None
            actions[menu.addAction("Edit note…" if has_note else "Add note…")] = lambda: self._edit_note(
                index.row(), index.column()
            )
            if has_note:
                actions[menu.addAction("Delete note")] = lambda: self._delete_note(index.row(), index.column())
        else:
            return
        chosen = menu.exec(global_pos)
        if chosen in actions:
            actions[chosen]()

    def _remove_guest(self, entry: _Row) -> None:
        clear_shift(self._schedule, self._repository, entry.employee.id, self._current_date())
        self._reload()
        if self._on_change:
            self._on_change()

