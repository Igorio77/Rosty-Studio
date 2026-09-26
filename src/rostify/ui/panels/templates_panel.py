"""Templates tab: manage the Templates / Shift ID matrix (one subdepartment
at a time, cascading off a Department selector). The Location ID catalog
widget (`LocationIdsTab`) is also defined here, but it is mounted in
Settings -> Position codes.

This is master data for scheduling, not the Schedule aggregate itself, so
this panel talks straight to the Repository (services/persistence.py) —
there is no in-memory Schedule involvement the way Staff/Schedule panels
have one, because Template/ShiftId/ShiftTiming/LocationCode aren't part of
Schedule's Employee/Assignment shape (see core/templates.py).

Deliberately not the Custom view or Day view from README.md's later phases
— this only builds the Template/Shift-ID/Location-ID foundation those views
will assign real Assignment rows against.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTime, Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from rostify.core.templates import TEMPLATE_COLORS, LocationCode, ShiftId, ShiftSegment, ShiftTiming, Template
from rostify.services.persistence import Repository

from ..theme import TEMPLATE_COLOR_HEX
from .widgets import IconTableEditor, SimpleFormDialog, chars_width, color_dot_icon, icon_button, three_line_row_height


def _color_dot_icon(color_name: str):
    return color_dot_icon(TEMPLATE_COLOR_HEX.get(color_name, TEMPLATE_COLOR_HEX["blue"]))


def _format_minutes(total_minutes: int) -> str:
    """12h clock, with a "(+1d)" suffix when `total_minutes` >= 1440 (a
    segment that runs into the next day)."""
    day_offset, minute_of_day = divmod(total_minutes, 1440)
    hh, mm = divmod(minute_of_day, 60)
    period = "AM" if hh < 12 else "PM"
    hh12 = hh % 12 or 12
    suffix = " (+1d)" if day_offset else ""
    return f"{hh12}:{mm:02d} {period}{suffix}"


def _cell_summary(timing: ShiftTiming | None) -> str:
    """One line per segment plus the comment (if any) — the matrix's default
    3-line row height exists so a split shift's two segments and its comment
    are all visible at once, not folded into a "+1" that needs a hover."""
    if timing is None or not timing.segments:
        return ""
    lines = [f"{_format_minutes(s.start_minutes)}–{_format_minutes(s.end_minutes)}" for s in timing.segments]
    if timing.comment:
        lines.append(timing.comment)
    return "\n".join(lines)


def _cell_tooltip(timing: ShiftTiming | None) -> str:
    if timing is None or not timing.segments:
        return "Click to set this shift's timing."
    lines = [
        f"Segment {i}: {_format_minutes(s.start_minutes)}–{_format_minutes(s.end_minutes)}"
        for i, s in enumerate(timing.segments, start=1)
    ]
    if timing.comment:
        lines.append(f"Comment: {timing.comment}")
    return "\n".join(lines)


def _minutes_to_qtime(minute_of_day: int) -> QTime:
    hh, mm = divmod(minute_of_day, 60)
    return QTime(hh, mm)


class EditShiftTimingDialog(QDialog):
    """Start/Finish segment editor for one (Template, Shift ID) cell.
    Overnight is inferred automatically: if a segment's finish time-of-day is
    earlier than its start, it's treated as running into the next day.
    """

    def __init__(
        self,
        shift_id_code: str,
        template_name: str,
        existing: ShiftTiming | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Shift timing — {shift_id_code} ({template_name})")
        self._segment_rows: list[tuple[QTimeEdit, QTimeEdit, QWidget]] = []

        self._segments_layout = QVBoxLayout()
        if existing is not None:
            for segment in existing.segments:
                self._add_segment_row(segment.start_minutes % 1440, segment.end_minutes % 1440)
        if not self._segment_rows:
            self._add_segment_row(9 * 60, 17 * 60)

        add_segment_button = icon_button("+", "Add segment")
        add_segment_button.clicked.connect(lambda: self._add_segment_row(9 * 60, 17 * 60))

        self.comment_edit = QLineEdit(existing.comment if existing else "")

        form = QFormLayout()
        form.addRow("Comment", self.comment_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(self._segments_layout)
        layout.addWidget(add_segment_button)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _add_segment_row(self, start_minute_of_day: int, end_minute_of_day: int) -> None:
        start_edit = QTimeEdit()
        start_edit.setDisplayFormat("h:mm AP")
        start_edit.setTime(_minutes_to_qtime(start_minute_of_day))

        end_edit = QTimeEdit()
        end_edit.setDisplayFormat("h:mm AP")
        end_edit.setTime(_minutes_to_qtime(end_minute_of_day))

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(start_edit)
        row_layout.addWidget(end_edit)

        remove_button = icon_button("\U0001f5d1", "Remove segment")
        remove_button.clicked.connect(lambda: self._remove_segment_row(row_widget))
        row_layout.addWidget(remove_button)

        self._segments_layout.addWidget(row_widget)
        self._segment_rows.append((start_edit, end_edit, row_widget))

    def _remove_segment_row(self, row_widget: QWidget) -> None:
        self._segment_rows = [r for r in self._segment_rows if r[2] is not row_widget]
        row_widget.setParent(None)
        row_widget.deleteLater()

    def segments(self) -> list[ShiftSegment]:
        segments = []
        for start_edit, end_edit, _ in self._segment_rows:
            start_tod = start_edit.time().hour() * 60 + start_edit.time().minute()
            end_tod = end_edit.time().hour() * 60 + end_edit.time().minute()
            end_minutes = end_tod + 1440 if end_tod < start_tod else end_tod
            segments.append(ShiftSegment(start_minutes=start_tod, end_minutes=end_minutes))
        return segments

    def comment(self) -> str:
        return self.comment_edit.text().strip()


class TemplatesMatrixTab(QWidget):
    """Department -> Subdepartment cascading selector, plus the
    Template x Shift-ID matrix for whichever subdepartment is selected.

    Column 0 is the Template name (a real, resizable column, not a vertical
    header label). Clicking a Template-name cell or a Shift-ID column header
    selects it for "Edit"/"Delete"; clicking any other cell opens that
    (Template, Shift ID)'s segment-timing dialog instead. Right-clicking
    anywhere offers the same actions as a context menu.
    """

    def __init__(self, repository: Repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repository = repository
        self._shift_ids: list[ShiftId] = []
        self._templates: list[Template] = []
        self._timings: dict[tuple[str, str], ShiftTiming] = {}
        self._selected_template_row: int | None = None
        self._selected_shift_id_col: int | None = None

        self.department_combo = QComboBox()
        self.department_combo.currentTextChanged.connect(self._reload_subdepartments)
        self.subdepartment_combo = QComboBox()
        self.subdepartment_combo.currentTextChanged.connect(self._on_subdepartment_changed)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Department"))
        top_row.addWidget(self.department_combo)
        top_row.addWidget(QLabel("Subdepartment"))
        top_row.addWidget(self.subdepartment_combo)
        top_row.addStretch(1)

        template_label = QLabel("Templates:")
        add_template_button = icon_button("+", "Add template")
        add_template_button.clicked.connect(self._add_template)
        edit_template_button = icon_button("✎", "Edit selected template (click its name in the matrix first)")
        edit_template_button.clicked.connect(self._edit_template)
        delete_template_button = icon_button("\U0001f5d1", "Delete selected template")
        delete_template_button.clicked.connect(self._delete_template)

        shift_id_label = QLabel("Shift IDs:")
        add_shift_id_button = icon_button("+", "Add shift ID")
        add_shift_id_button.clicked.connect(self._add_shift_id)
        edit_shift_id_button = icon_button("✎", "Edit selected shift ID (click its column header first)")
        edit_shift_id_button.clicked.connect(self._edit_shift_id)
        delete_shift_id_button = icon_button("\U0001f5d1", "Delete selected shift ID")
        delete_shift_id_button.clicked.connect(self._delete_shift_id)

        button_row = QHBoxLayout()
        button_row.addWidget(template_label)
        button_row.addWidget(add_template_button)
        button_row.addWidget(edit_template_button)
        button_row.addWidget(delete_template_button)
        button_row.addSpacing(16)
        button_row.addWidget(shift_id_label)
        button_row.addWidget(add_shift_id_button)
        button_row.addWidget(edit_shift_id_button)
        button_row.addWidget(delete_shift_id_button)
        button_row.addStretch(1)

        self.matrix_table = QTableWidget()
        self.matrix_table.setWordWrap(True)
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.matrix_table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.matrix_table.verticalHeader().setDefaultSectionSize(three_line_row_height(self.matrix_table))
        # Same interaction pattern as the Team tab: a single click selects
        # (and highlights the row, via SelectRows below) — it never opens a
        # dialog by itself — a double-click opens the editor. Consistent
        # behavior across tabs, so the icon buttons above always mean
        # "act on whatever is currently selected".
        self.matrix_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.matrix_table.cellClicked.connect(self._on_cell_clicked)
        self.matrix_table.cellDoubleClicked.connect(self._edit_cell)
        self.matrix_table.verticalHeader().sectionClicked.connect(self._on_row_header_clicked)
        self.matrix_table.horizontalHeader().sectionClicked.connect(self._on_column_header_clicked)
        # Right-click is a second way to add/edit/delete, alongside the icon
        # rows above.
        self.matrix_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.matrix_table.customContextMenuRequested.connect(self._show_matrix_context_menu)
        self.matrix_table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.matrix_table.horizontalHeader().customContextMenuRequested.connect(
            self._show_shift_id_header_context_menu
        )

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addLayout(button_row)
        layout.addWidget(self.matrix_table, stretch=1)

        self.reload_departments()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self.reload_departments()

    # --- department / subdepartment cascade -------------------------------

    def reload_departments(self) -> None:
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
        self._reload_for_subdepartment(self.subdepartment_combo.currentText())

    def _on_subdepartment_changed(self, text: str) -> None:
        self._reload_for_subdepartment(text)

    def _current_subdepartment(self) -> str:
        return self.subdepartment_combo.currentText().strip()

    # --- matrix -------------------------------------------------

    def _reload_for_subdepartment(self, subdepartment: str) -> None:
        self._selected_template_row = None
        self._selected_shift_id_col = None
        if not subdepartment:
            self._shift_ids, self._templates, self._timings = [], [], {}
            self._render_matrix()
            return
        self._shift_ids = self._repository.load_shift_ids(subdepartment)
        self._templates = self._repository.load_templates(subdepartment)
        self._timings = {}
        for template in self._templates:
            for timing in self._repository.load_shift_timings(template.id):
                self._timings[(timing.template_id, timing.shift_id)] = timing
        self._render_matrix()

    def _render_matrix(self) -> None:
        # Column 0 is the Template name itself, a plain resizable column —
        # NOT a vertical-header label. Qt's vertical header only lets the
        # user drag row *height*, not header *width*, so a real column is
        # what actually makes "Split_AM_PM" draggable wider.
        table = self.matrix_table
        table.setRowCount(len(self._templates))
        table.setColumnCount(len(self._shift_ids) + 1)
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Template"))
        for col, shift_id in enumerate(self._shift_ids, start=1):
            header_item = QTableWidgetItem(shift_id.code)
            header_item.setIcon(_color_dot_icon(shift_id.color))
            table.setHorizontalHeaderItem(col, header_item)

        for row, template in enumerate(self._templates):
            name_item = QTableWidgetItem(template.name)
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setIcon(_color_dot_icon(template.color))
            font = name_item.font()
            font.setBold(True)
            name_item.setFont(font)
            table.setItem(row, 0, name_item)

            for col, shift_id in enumerate(self._shift_ids, start=1):
                timing = self._timings.get((template.id, shift_id.id))
                item = QTableWidgetItem(_cell_summary(timing))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setToolTip(_cell_tooltip(timing))
                table.setItem(row, col, item)

        default_width = chars_width(table, 20)
        for col in range(table.columnCount()):
            if table.columnWidth(col) < default_width:
                table.horizontalHeader().resizeSection(col, default_width)

    def _on_row_header_clicked(self, row: int) -> None:
        self._selected_template_row = row

    def _on_column_header_clicked(self, col: int) -> None:
        if col == 0:
            return  # the "Template" header, not a shift ID
        self._selected_shift_id_col = col - 1

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Single click: select only — same as the Team tab. `SelectRows`
        already highlights the row; this just keeps the Edit/Delete Template
        buttons and the shift-id-column bookkeeping in sync with it."""
        self._selected_template_row = row
        if col > 0:
            self._selected_shift_id_col = col - 1

    def _edit_cell(self, row: int, col: int) -> None:
        """Double click: open the editor for whatever was double-clicked —
        the Template's own edit dialog for its name cell, the segment-timing
        dialog for any other cell."""
        if col == 0:
            self._selected_template_row = row
            self._edit_template()
            return
        template = self._templates[row]
        shift_id = self._shift_ids[col - 1]
        existing = self._timings.get((template.id, shift_id.id))

        dialog = EditShiftTimingDialog(shift_id.code, template.name, existing, self)
        if dialog.exec() != QDialog.Accepted:
            return

        segments = dialog.segments()
        if not segments:
            if existing is not None:
                self._repository.delete_shift_timing(existing.id)
                del self._timings[(template.id, shift_id.id)]
        else:
            timing = existing or ShiftTiming(template_id=template.id, shift_id=shift_id.id)
            timing.segments = segments
            timing.comment = dialog.comment()
            self._repository.save_shift_timing(timing)
            self._timings[(template.id, shift_id.id)] = timing

        self._render_matrix()

    def _show_matrix_context_menu(self, position) -> None:
        index = self.matrix_table.indexAt(position)
        menu = QMenu(self.matrix_table)
        if index.isValid() and index.column() == 0:
            # Right-click on a Template name cell -> Template actions.
            self._selected_template_row = index.row()
            edit_action = menu.addAction("Edit template")
            delete_action = menu.addAction("Delete template")
            chosen = menu.exec(self.matrix_table.viewport().mapToGlobal(position))
            if chosen is edit_action:
                self._edit_template()
            elif chosen is delete_action:
                self._delete_template()
        elif index.isValid():
            # Right-click on a timing cell -> that cell's shift timing.
            edit_action = menu.addAction("Edit shift timing")
            chosen = menu.exec(self.matrix_table.viewport().mapToGlobal(position))
            if chosen is edit_action:
                self._edit_cell(index.row(), index.column())
        else:
            add_action = menu.addAction("Add template")
            chosen = menu.exec(self.matrix_table.viewport().mapToGlobal(position))
            if chosen is add_action:
                self._add_template()

    def _show_shift_id_header_context_menu(self, position) -> None:
        header = self.matrix_table.horizontalHeader()
        col = header.logicalIndexAt(position)
        if col == 0:
            return  # the "Template" header, not a shift ID
        menu = QMenu(header)
        if col > 0:
            self._selected_shift_id_col = col - 1
            edit_action = menu.addAction("Edit shift ID")
            delete_action = menu.addAction("Delete shift ID")
            chosen = menu.exec(header.mapToGlobal(position))
            if chosen is edit_action:
                self._edit_shift_id()
            elif chosen is delete_action:
                self._delete_shift_id()
        else:
            add_action = menu.addAction("Add shift ID")
            chosen = menu.exec(header.mapToGlobal(position))
            if chosen is add_action:
                self._add_shift_id()

    # --- templates -------------------------------------------------

    _TEMPLATE_FIELDS = [("Name", None), ("Subtitle", None), ("Color", TEMPLATE_COLORS)]

    def _add_template(self) -> None:
        subdepartment = self._current_subdepartment()
        if not subdepartment:
            QMessageBox.information(self, "No subdepartment", "Choose a subdepartment first.")
            return
        dialog = SimpleFormDialog("Add template", self._TEMPLATE_FIELDS, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, subtitle, color = dialog.values()
        if not name:
            return
        if any(t.name == name for t in self._templates):
            QMessageBox.warning(self, "Duplicate template", f"'{name}' already exists for {subdepartment}.")
            return
        self._repository.save_template(Template(subdepartment=subdepartment, name=name, subtitle=subtitle, color=color))
        self._reload_for_subdepartment(subdepartment)

    def _edit_template(self) -> None:
        template = self._selected_template()
        if template is None:
            QMessageBox.information(self, "No selection", "Click a template's name in the matrix first.")
            return
        dialog = SimpleFormDialog(
            "Edit template",
            self._TEMPLATE_FIELDS,
            initial=[template.name, template.subtitle, template.color],
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        name, subtitle, color = dialog.values()
        if not name:
            return
        self._repository.save_template(
            Template(id=template.id, subdepartment=template.subdepartment, name=name, subtitle=subtitle, color=color)
        )
        self._reload_for_subdepartment(self._current_subdepartment())

    def _delete_template(self) -> None:
        template = self._selected_template()
        if template is None:
            QMessageBox.information(self, "No selection", "Click a template's name in the matrix first.")
            return
        if self._confirm(f"Delete template '{template.name}'? Its shift timings go with it."):
            self._repository.delete_template(template.id)
            self._reload_for_subdepartment(self._current_subdepartment())

    def _selected_template(self) -> Template | None:
        row = self._selected_template_row
        return self._templates[row] if row is not None and row < len(self._templates) else None

    # --- shift ids -------------------------------------------------

    _SHIFT_ID_FIELDS = [("Code", None), ("Color", TEMPLATE_COLORS)]

    def _add_shift_id(self) -> None:
        subdepartment = self._current_subdepartment()
        if not subdepartment:
            QMessageBox.information(self, "No subdepartment", "Choose a subdepartment first.")
            return
        dialog = SimpleFormDialog("Add shift ID", self._SHIFT_ID_FIELDS, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        code, color = dialog.values()
        if not code:
            return
        if any(s.code == code for s in self._shift_ids):
            QMessageBox.warning(self, "Duplicate shift ID", f"'{code}' already exists for {subdepartment}.")
            return
        self._repository.save_shift_id(ShiftId(subdepartment=subdepartment, code=code, color=color or "blue"))
        self._reload_for_subdepartment(subdepartment)

    def _edit_shift_id(self) -> None:
        shift_id = self._selected_shift_id()
        if shift_id is None:
            QMessageBox.information(self, "No selection", "Click a shift ID's column header first.")
            return
        dialog = SimpleFormDialog(
            "Edit shift ID", self._SHIFT_ID_FIELDS, initial=[shift_id.code, shift_id.color], parent=self
        )
        if dialog.exec() != QDialog.Accepted:
            return
        code, color = dialog.values()
        if not code:
            return
        self._repository.save_shift_id(
            ShiftId(id=shift_id.id, subdepartment=shift_id.subdepartment, code=code, color=color or "blue")
        )
        self._reload_for_subdepartment(self._current_subdepartment())

    def _delete_shift_id(self) -> None:
        shift_id = self._selected_shift_id()
        if shift_id is None:
            QMessageBox.information(self, "No selection", "Click a shift ID's column header first.")
            return
        if self._confirm(f"Delete shift ID '{shift_id.code}'? Its shift timings go with it."):
            self._repository.delete_shift_id(shift_id.id)
            self._reload_for_subdepartment(self._current_subdepartment())

    def _selected_shift_id(self) -> ShiftId | None:
        col = self._selected_shift_id_col
        return self._shift_ids[col] if col is not None and col < len(self._shift_ids) else None

    def _confirm(self, message: str) -> bool:
        reply = QMessageBox.question(self, "Confirm", message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes


class LocationIdsTab(QWidget):
    """The Location ID catalog as its own sub-tab: Abbreviation (the short
    code a future Day-view grid cell will pick), Location Code (the fuller
    code), Location Description and Location Group — four distinct fields,
    not one field under two names.
    """

    _FIELDS = [("Abbreviation", None), ("Location Code", None), ("Description", None), ("Group", None)]

    def __init__(
        self,
        repository: Repository,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._on_change = on_change
        self._location_codes: list[LocationCode] = []

        self.editor = IconTableEditor(
            ["Abbreviation", "Location Code", "Location Description", "Location Group"],
            self._add,
            self._edit,
            self._delete,
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)

        self.reload()

    def reload(self) -> None:
        self._location_codes = self._repository.load_location_codes()
        self.editor.set_rows(
            [(lc.abbreviation, lc.location_code, lc.description, lc.group) for lc in self._location_codes]
        )

    def _add(self) -> None:
        dialog = SimpleFormDialog("Add location ID", self._FIELDS, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        abbreviation, location_code, description, group = dialog.values()
        if not abbreviation:
            return
        if any(lc.abbreviation == abbreviation for lc in self._location_codes):
            QMessageBox.warning(self, "Duplicate abbreviation", f"'{abbreviation}' already exists.")
            return
        self._repository.save_location_code(
            LocationCode(abbreviation=abbreviation, location_code=location_code, description=description, group=group)
        )
        self._reload_and_notify()

    def _edit(self, row: int) -> None:
        existing = self._location_codes[row]
        dialog = SimpleFormDialog(
            "Edit location ID",
            self._FIELDS,
            initial=[existing.abbreviation, existing.location_code, existing.description, existing.group],
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        abbreviation, location_code, description, group = dialog.values()
        if not abbreviation:
            return
        if abbreviation != existing.abbreviation:
            self._repository.delete_location_code(existing.abbreviation)
        self._repository.save_location_code(
            LocationCode(abbreviation=abbreviation, location_code=location_code, description=description, group=group)
        )
        self._reload_and_notify()

    def _delete(self, row: int) -> None:
        existing = self._location_codes[row]
        reply = QMessageBox.question(
            self, "Delete location ID", f"Delete '{existing.abbreviation}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self._repository.delete_location_code(existing.abbreviation)
        self._reload_and_notify()

    def _reload_and_notify(self) -> None:
        self.reload()
        if self._on_change:
            self._on_change()


class TemplatesPanel(QTabWidget):
    """Templates & Shift IDs. The Location ID catalog that used to be a
    second tab here now lives in Settings -> Position codes."""

    def __init__(self, repository: Repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.addTab(TemplatesMatrixTab(repository), "Templates && Shift IDs")
