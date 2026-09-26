"""Day view tab: a position-rotation grid for Dealers and Supervisors —
one row per employee, one column per time-step slot across a fixed daily
window (06:00 to 02:00 the next day), each filled cell showing the Location
ID abbreviation that employee is on for that slot.

This is the layer-B (POSITION) side of the unified Assignment model
(CLAUDE.md "one unified model serves both planning levels") — a filled cell
is a real `Assignment(layer=POSITION, resource=<abbreviation>)` spanning
exactly that slot. Deliberately NOT clipped to the employee's layer-A
(SHIFT) shift window: a position can run before/after the nominal shift
(overtime/under time), per the domain expert's explicit call. Cells within
the employee's shift window are tinted so working hours still read at a
glance; hovering any cell shows that slot's shift + position info.

Interaction: a slot cell is edited in place — the view's own editor is an
editable combo of Location ID abbreviations (`_AbbreviationDelegate`), so a
supervisor can pick from the list or type a code straight into the grid.
The editor is built on demand by the delegate, one at a time; an earlier
pass parked a live QComboBox in all ~80 columns of every row at once and
that was both slow and visually cramped. A per-slot comment still needs
more room than a grid cell, so it stays on the right-click menu's dialog.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import LocationCode, ShiftId, Template
from rostify.rules.engine import RuleEngine
from rostify.services.persistence import Repository

from ..theme import COLORS, SURFACE, TEMPLATE_COLOR_HEX, mix
from .widgets import chars_width, shift_badge_button

_DEFAULT_SLOT_MINUTES = 15
_MIN_SLOT_MINUTES, _MAX_SLOT_MINUTES = 5, 120
_DAY_START_MINUTES = 6 * 60  # 06:00
_DAY_END_MINUTES = 26 * 60  # 02:00 the next day
_SUBDEPARTMENTS = ("Dealers", "Supervisors")
_NO_LOCATION = "— clear —"
_NO_SHIFT = "— none —"
# Sticky columns, then one column per time slot.
_COL_SHIFT_ID, _COL_LAST_NAME, _COL_FIRST_NAME, _COL_EMPLOYEE_ID = range(4)
_SLOT_COL_OFFSET = 4
_STICKY_HEADERS = ["Shift ID", "Last Name", "First Name", "Employee ID"]
# Opaque, not translucent: these are handed to QTableWidgetItem.setBackground,
# where an alpha channel would blend against the window rather than the row.
_SHIFT_TINT = QColor(mix(COLORS["accent"], SURFACE[1], 0.16))  # this slot is within the employee's shift
_OUT_OF_SHIFT_BG = QColor(SURFACE[0])  # recessed: outside the shift window, still editable


def _qdate_to_date(qd: QDate) -> date:
    return date(qd.year(), qd.month(), qd.day())


def _date_to_qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def _format_slot_header(minute_of_day: int) -> str:
    hh, mm = divmod(minute_of_day % 1440, 60)
    return f"{hh:02d}:{mm:02d}"


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


class _AbbreviationDelegate(QStyledItemDelegate):
    """In-cell editor for a position slot: an editable combo of the Location
    ID abbreviations, so a slot takes either a pick from the list or a typed
    code. Qt builds one editor at a time, on demand — which is what keeps a
    20-hour grid responsive."""

    def __init__(self, abbreviations: Callable[[], list[str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._abbreviations = abbreviations

    def createEditor(self, parent, option, index):  # noqa: N802
        combo = QComboBox(parent)
        # Without compactCombo the global 160px min-width makes the editor
        # three times its cell and it covers the neighbouring slots.
        combo.setObjectName("compactCombo")
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.addItem("")
        combo.addItems(self._abbreviations())
        return combo

    def setEditorData(self, editor: QComboBox, index) -> None:  # noqa: N802
        editor.setCurrentText(index.data(Qt.EditRole) or "")
        editor.lineEdit().selectAll()

    def setModelData(self, editor: QComboBox, model, index) -> None:  # noqa: N802
        model.setData(index, editor.currentText().strip(), Qt.EditRole)


class _SlotEditDialog(QDialog):
    """Pick a Location ID (or clear) for one slot, plus an optional
    comment — the same cell carries both."""

    def __init__(
        self,
        location_codes: list[LocationCode],
        existing_abbreviation: str,
        existing_comment: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set position")

        self.location_combo = QComboBox()
        self.location_combo.setEditable(True)  # dropdown OR type a code not yet in the catalog
        self.location_combo.addItem(_NO_LOCATION)
        self.location_combo.addItems([lc.abbreviation for lc in location_codes])
        if existing_abbreviation:
            index = self.location_combo.findText(existing_abbreviation)
            if index >= 0:
                self.location_combo.setCurrentIndex(index)
            else:
                self.location_combo.setCurrentText(existing_abbreviation)

        self.comment_edit = QLineEdit(existing_comment)

        form = QFormLayout()
        form.addRow("Location", self.location_combo)
        form.addRow("Comment", self.comment_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def abbreviation(self) -> str:
        text = self.location_combo.currentText().strip()
        return "" if text == _NO_LOCATION else text

    def comment(self) -> str:
        return self.comment_edit.text().strip()


class _ShiftIdEditDialog(QDialog):
    """Pick which Shift ID (or none) this employee is on for the day —
    answers "how do I set the Shift ID column" from the Day view itself,
    instead of only from the Custom view."""

    def __init__(self, shift_ids: list[ShiftId], current_code: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set shift ID")

        self.combo = QComboBox()
        self.combo.addItem(_NO_SHIFT)
        self.combo.addItems([s.code for s in shift_ids])
        if current_code:
            index = self.combo.findText(current_code)
            if index >= 0:
                self.combo.setCurrentIndex(index)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Shift ID for this day"))
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

    def code(self) -> str:
        text = self.combo.currentText()
        return "" if text == _NO_SHIFT else text


class DayViewPanel(QWidget):
    def __init__(
        self,
        schedule: Schedule,
        repository: Repository,
        rule_engine: RuleEngine | None = None,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._schedule = schedule
        self._repository = repository
        self._on_change = on_change
        self._employees: list[Employee] = []
        self._shift_codes: dict[str, str] = {}
        self._shift_colors: dict[tuple[str, str], str] = {}  # (subdepartment, code) -> TEMPLATE_COLORS name
        self._location_codes: list[LocationCode] = []
        self._location_by_abbr: dict[str, LocationCode] = {}
        self._rendering = False  # guards itemChanged while _render fills the grid
        self._slot_minutes = _default_time_step(rule_engine)
        self._slot_starts = list(range(_DAY_START_MINUTES, _DAY_END_MINUTES, self._slot_minutes))

        self.date_edit = QDateEdit(_date_to_qdate(date.today()))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(lambda _: self._reload())

        # Multi-select checkbox menu, not a single-pick combo — lets a
        # supervisor see e.g. Dealers and Supervisors together (grouped,
        # not interleaved — see _reload's sort key) or just one of them.
        # A QPushButton, not a QToolButton: the global sheet styles
        # QPushButton, and an unstyled QToolButton renders as a native
        # Windows control next to styled neighbours.
        self.subdepartment_button = QPushButton()
        self._subdepartment_menu = QMenu(self.subdepartment_button)
        self._subdepartment_actions: dict[str, "QAction"] = {}
        for sub in _SUBDEPARTMENTS:
            action = self._subdepartment_menu.addAction(sub)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self._on_subdepartment_toggled)
            self._subdepartment_actions[sub] = action
        self.subdepartment_button.setMenu(self._subdepartment_menu)
        self.subdepartment_button.setMinimumWidth(chars_width(self, 18))
        self._update_subdepartment_button_text()

        # A spin box, not an editable combo: it takes a freely typed number
        # (the actual requirement), it is already styled down to its
        # chevrons, and it has none of the editable-combo geometry trouble
        # that clips a value on a narrow field.
        self.time_step_spin = QSpinBox()
        self.time_step_spin.setRange(_MIN_SLOT_MINUTES, _MAX_SLOT_MINUTES)
        self.time_step_spin.setSingleStep(5)
        self.time_step_spin.setSuffix(" min")
        self.time_step_spin.setValue(self._slot_minutes)
        self.time_step_spin.setKeyboardTracking(False)  # fires once the number is finished, not per digit
        self.time_step_spin.setFixedWidth(chars_width(self, 10))
        self.time_step_spin.valueChanged.connect(self._on_time_step_changed)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.addWidget(QLabel("Date"))
        top_row.addWidget(self.date_edit)
        top_row.addSpacing(8)
        top_row.addWidget(QLabel("Subdepartments"))
        top_row.addWidget(self.subdepartment_button)
        top_row.addSpacing(8)
        top_row.addWidget(QLabel("Time step"))
        top_row.addWidget(self.time_step_spin)
        top_row.addStretch(1)

        # Banner: [big day number] Weekday, Month Year | ● Template name — comments
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

        self.template_dot = QLabel("")
        self.template_dot.setFixedSize(10, 10)
        self.template_name_label = QLabel("")
        self.template_name_label.setStyleSheet("border: none; font-weight: 700;")
        self.template_comments_label = QLabel("")
        self.template_comments_label.setStyleSheet(f"border: none; color: {COLORS['text_tertiary']};")
        self.template_comments_label.setWordWrap(True)

        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)
        banner_layout.addWidget(self.day_number_label)
        banner_layout.addLayout(date_col)
        banner_layout.addSpacing(12)
        banner_layout.addWidget(self.template_dot)
        banner_layout.addWidget(self.template_name_label)
        banner_layout.addWidget(self.template_comments_label, stretch=1)

        self.table = QTableWidget()
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # Excel-shaped editing: click a selected cell, double-click, Enter or
        # just start typing opens the in-cell editor (_AbbreviationDelegate).
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self.table.setItemDelegate(_AbbreviationDelegate(lambda: [lc.abbreviation for lc in self._location_codes], self))
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self.banner)
        layout.addWidget(self.table, stretch=1)

        self._reload()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._reload()

    def reload(self) -> None:
        self._reload()

    def _current_date(self) -> date:
        return _qdate_to_date(self.date_edit.date())

    def _selected_subdepartments(self) -> list[str]:
        return [s for s in _SUBDEPARTMENTS if self._subdepartment_actions[s].isChecked()]

    def _update_subdepartment_button_text(self) -> None:
        selected = self._selected_subdepartments()
        if len(selected) == len(_SUBDEPARTMENTS):
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
        day = self._current_date()
        selected_subdepartments = self._selected_subdepartments()
        employees = [e for e in self._schedule.employees() if e.subdepartment in selected_subdepartments]
        self._location_codes = self._repository.load_location_codes()
        self._location_by_abbr = {lc.abbreviation: lc for lc in self._location_codes}

        shift_codes = {e.id: self._employee_shift_code(e.id, day) for e in employees}
        # Grouped by subdepartment first (so "All" doesn't interleave
        # Dealers/Supervisors), then Shift ID (blank sorts last), then name.
        self._employees = sorted(employees, key=lambda e: (e.subdepartment, shift_codes[e.id] or "~", e.full_name))
        self._shift_codes = shift_codes
        # Each Shift ID owns its badge color (ShiftId.color), so the Day view
        # badge matches the same code's badge in the Custom view.
        self._shift_colors = {
            (subdepartment, shift_id.code): shift_id.color
            for subdepartment in selected_subdepartments
            for shift_id in self._repository.load_shift_ids(subdepartment)
        }
        self._render()
        self._update_banner(day, selected_subdepartments)

    def _on_time_step_changed(self, minutes: int) -> None:
        if minutes == self._slot_minutes:
            return
        self._slot_minutes = minutes
        self._slot_starts = list(range(_DAY_START_MINUTES, _DAY_END_MINUTES, self._slot_minutes))
        self._render()

    # --- window / overlap helpers -------------------------------------------------

    def _window(self, day: date) -> tuple[datetime, datetime]:
        midnight = datetime.combine(day, datetime.min.time())
        return midnight + timedelta(minutes=_DAY_START_MINUTES), midnight + timedelta(minutes=_DAY_END_MINUTES)

    def _slot_range(self, day: date, slot_start: int) -> tuple[datetime, datetime]:
        midnight = datetime.combine(day, datetime.min.time())
        start = midnight + timedelta(minutes=slot_start)
        return start, start + timedelta(minutes=self._slot_minutes)

    def _assignments_in_window(self, employee_id: str, layer: Layer, day: date) -> list[Assignment]:
        window_start, window_end = self._window(day)
        return [
            a
            for a in self._schedule.assignments(employee_id=employee_id, layer=layer)
            if a.start < window_end and window_start < a.end
        ]

    @staticmethod
    def _covering(assignments: list[Assignment], slot_start: datetime, slot_end: datetime) -> Assignment | None:
        return next((a for a in assignments if a.start < slot_end and slot_start < a.end), None)

    def _existing_shift_assignment(self, employee: Employee, day: date) -> Assignment | None:
        matches = self._assignments_in_window(employee.id, Layer.SHIFT, day)
        return matches[0] if matches else None

    def _employee_shift_code(self, employee_id: str, day: date) -> str:
        shifts = self._assignments_in_window(employee_id, Layer.SHIFT, day)
        return shifts[0].resource if shifts else ""

    def _template_for_subdepartment(self, day: date, subdepartment: str) -> Template | None:
        templates_by_id = {t.id: t for t in self._repository.load_templates(subdepartment)}
        assignments = self._repository.load_template_assignments_range(subdepartment, day, day)
        return templates_by_id.get(assignments[0].template_id) if assignments else None

    # --- banner -------------------------------------------------

    def _update_banner(self, day: date, subdepartments: list[str]) -> None:
        self.day_number_label.setText(str(day.day))
        self.weekday_label.setText(day.strftime("%A"))
        self.month_label.setText(day.strftime("%B %Y"))

        names = []
        color_hex = None
        comments = []
        for subdepartment in subdepartments:
            template = self._template_for_subdepartment(day, subdepartment)
            if template is not None:
                names.append(template.name if len(subdepartments) == 1 else f"{subdepartment}: {template.name}")
                if template.subtitle:
                    comments.append(template.subtitle)
                color_hex = color_hex or TEMPLATE_COLOR_HEX.get(template.color, TEMPLATE_COLOR_HEX["blue"])

        if names:
            self.template_dot.setStyleSheet(
                f"border: none; border-radius: 5px; background: {color_hex or TEMPLATE_COLOR_HEX['blue']};"
            )
            self.template_name_label.setText(" · ".join(names))
            self.template_comments_label.setText(" · ".join(comments))
        else:
            self.template_dot.setStyleSheet("border: none; background: transparent;")
            self.template_name_label.setText("No template assigned")
            self.template_comments_label.setText("")

    # --- rendering -------------------------------------------------

    def _render(self) -> None:
        table = self.table
        self._rendering = True  # setItem below would otherwise fire _on_item_changed
        try:
            table.setRowCount(len(self._employees))
            table.setColumnCount(_SLOT_COL_OFFSET + len(self._slot_starts))
            table.setHorizontalHeaderLabels(
                _STICKY_HEADERS + [_format_slot_header(m) for m in self._slot_starts]
            )

            day = self._current_date()
            for row, employee in enumerate(self._employees):
                code = self._shift_codes.get(employee.id, "")
                color_name = self._shift_colors.get((employee.subdepartment, code))
                table.setCellWidget(
                    row,
                    _COL_SHIFT_ID,
                    self._build_shift_badge(row, code, color_name),
                )

                for col, value in (
                    (_COL_LAST_NAME, employee.last_name),
                    (_COL_FIRST_NAME, employee.first_name),
                    (_COL_EMPLOYEE_ID, employee.id),
                ):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    table.setItem(row, col, item)

                shift_assignments = self._assignments_in_window(employee.id, Layer.SHIFT, day)
                position_assignments = self._assignments_in_window(employee.id, Layer.POSITION, day)

                for slot_index, slot_start_minutes in enumerate(self._slot_starts):
                    col = _SLOT_COL_OFFSET + slot_index
                    slot_start, slot_end = self._slot_range(day, slot_start_minutes)
                    covering_shift = self._covering(shift_assignments, slot_start, slot_end)
                    covering_position = self._covering(position_assignments, slot_start, slot_end)

                    item = QTableWidgetItem(covering_position.resource if covering_position else "")
                    item.setTextAlignment(Qt.AlignCenter)
                    # Editable: the delegate turns this into a dropdown that
                    # also accepts a typed abbreviation.
                    # Slots outside the employee's shift window are recessed
                    # — still fully editable, just de-emphasized.
                    item.setBackground(_SHIFT_TINT if covering_shift is not None else _OUT_OF_SHIFT_BG)
                    if covering_shift is None:
                        item.setForeground(QColor(COLORS["text_tertiary"]))

                    tooltip_lines = []
                    if covering_shift is not None:
                        tooltip_lines.append(
                            f"Shift {covering_shift.resource}: {_format_range(covering_shift.start, covering_shift.end)}"
                        )
                    if covering_position is not None:
                        location = self._location_by_abbr.get(covering_position.resource)
                        if location is not None:
                            tooltip_lines.append(f"{location.abbreviation} — {location.description} ({location.group})")
                        if covering_position.comment:
                            tooltip_lines.append(f"Note: {covering_position.comment}")
                    item.setToolTip(
                        "\n".join(tooltip_lines) if tooltip_lines else "Pick or type a location for this slot."
                    )
                    table.setItem(row, col, item)

            name_width = chars_width(table, 16)
            short_width = chars_width(table, 5)
            table.horizontalHeader().resizeSection(_COL_SHIFT_ID, chars_width(table, 6))
            for col in (_COL_LAST_NAME, _COL_FIRST_NAME, _COL_EMPLOYEE_ID):
                table.horizontalHeader().resizeSection(col, name_width)
            for col in range(_SLOT_COL_OFFSET, table.columnCount()):
                table.horizontalHeader().resizeSection(col, short_width)
            for row in range(table.rowCount()):
                table.setRowHeight(row, 34)  # room for the 28px shift badge
        finally:
            self._rendering = False

    def _build_shift_badge(self, row: int, code: str, color_name: str | None) -> QWidget:
        """The same colored badge the Custom view roster uses — and, when the
        employee has no shift yet, the dashed `+` that adds one."""
        hex_color = TEMPLATE_COLOR_HEX.get(color_name or "", TEMPLATE_COLOR_HEX["blue"]) if color_name else None
        button = shift_badge_button(
            code,
            hex_color,
            f"Shift {code} — click to change or clear" if code else "Add a shift ID for this employee",
        )
        button.clicked.connect(lambda _=False, r=row: self._edit_shift_id(r))
        return button

    # --- editing -------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """An in-cell edit landed: write it through as a POSITION assignment."""
        if self._rendering or item.column() < _SLOT_COL_OFFSET:
            return
        row = item.row()
        if row >= len(self._employees):
            return
        self._apply_position(self._employees[row], item.column() - _SLOT_COL_OFFSET, item.text().strip())

    def _apply_position(self, employee: Employee, slot_index: int, abbreviation: str, comment: str | None = None) -> None:
        """Replace whatever POSITION assignment covers this slot with
        `abbreviation` (empty clears it). Shared by the in-cell editor and
        the comment dialog."""
        if slot_index >= len(self._slot_starts):
            return
        day = self._current_date()
        slot_start, slot_end = self._slot_range(day, self._slot_starts[slot_index])
        existing = self._covering(self._assignments_in_window(employee.id, Layer.POSITION, day), slot_start, slot_end)
        if existing is not None and existing.resource == abbreviation and comment is None:
            return  # nothing changed

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
                comment=comment if comment is not None else (existing.comment if existing else ""),
            )
            self._schedule.add_assignment(assignment)
            self._repository.save_assignment(assignment)

        self._render()
        if self._on_change:
            self._on_change()

    def _edit_shift_id(self, row: int) -> None:
        employee = self._employees[row]
        day = self._current_date()
        shift_ids = self._repository.load_shift_ids(employee.subdepartment)
        current_code = self._shift_codes.get(employee.id, "")

        dialog = _ShiftIdEditDialog(shift_ids, current_code, self)
        if dialog.exec() != QDialog.Accepted:
            return
        new_code = dialog.code()
        if new_code == current_code:
            return

        existing = self._existing_shift_assignment(employee, day)
        if existing is not None:
            self._schedule.remove_assignment(existing.id)
            self._repository.delete_assignment(existing.id)

        if new_code:
            template = self._template_for_subdepartment(day, employee.subdepartment)
            shift_id_obj = next((s for s in shift_ids if s.code == new_code), None)
            timing = None
            if template is not None and shift_id_obj is not None:
                timing = next(
                    (t for t in self._repository.load_shift_timings(template.id) if t.shift_id == shift_id_obj.id),
                    None,
                )
            if timing is None or not timing.segments:
                QMessageBox.information(
                    self,
                    "No timing set",
                    f"Shift '{new_code}' has no timing for today's template yet — set it on the "
                    f"Templates tab (or assign a template to this day first).",
                )
                return
            start_minutes = min(s.start_minutes for s in timing.segments)
            end_minutes = max(s.end_minutes for s in timing.segments)
            day_start = datetime.combine(day, datetime.min.time())
            assignment = Assignment(
                employee_id=employee.id,
                start=day_start + timedelta(minutes=start_minutes),
                end=day_start + timedelta(minutes=end_minutes),
                resource=new_code,
                layer=Layer.SHIFT,
                department=employee.department,
            )
            self._schedule.add_assignment(assignment)
            self._repository.save_assignment(assignment)

        self._reload()
        if self._on_change:
            self._on_change()

    def _edit_position_with_comment(self, row: int, col: int) -> None:
        """The long form: location *and* a note. A grid cell has no room for
        a comment field, so that one case keeps a dialog."""
        employee = self._employees[row]
        day = self._current_date()
        slot_index = col - _SLOT_COL_OFFSET
        if slot_index >= len(self._slot_starts):
            return
        slot_start, slot_end = self._slot_range(day, self._slot_starts[slot_index])
        existing = self._covering(self._assignments_in_window(employee.id, Layer.POSITION, day), slot_start, slot_end)

        dialog = _SlotEditDialog(
            self._location_codes,
            existing.resource if existing else "",
            existing.comment if existing else "",
            self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        self._apply_position(employee, slot_index, dialog.abbreviation(), comment=dialog.comment())

    def _show_context_menu(self, position) -> None:
        index = self.table.indexAt(position)
        if not index.isValid() or index.row() >= len(self._employees):
            return
        menu = QMenu(self.table)
        if index.column() == _COL_SHIFT_ID:
            action = menu.addAction("Set shift ID")
        elif index.column() >= _SLOT_COL_OFFSET:
            action = menu.addAction("Set position (with comment)")
        else:
            return
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is not action:
            return
        if index.column() == _COL_SHIFT_ID:
            self._edit_shift_id(index.row())
        else:
            self._edit_position_with_comment(index.row(), index.column())
