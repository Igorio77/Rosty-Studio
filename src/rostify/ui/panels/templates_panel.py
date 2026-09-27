"""Templates tab: manage the Templates / Shift ID matrix (one subdepartment
at a time, cascading off a Department selector). The Location code catalog
lives in Settings -> Lists (`list_control_panel.py`).

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

from PySide6.QtCore import QTime, QTimer, Qt
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

from rostify.core.schedule import Schedule
from rostify.core.templates import TEMPLATE_COLORS, ShiftId, ShiftSegment, ShiftTiming, Template, natural_key
from rostify.services.persistence import Repository
from rostify.services.shift_sync import rename_shift_code, retime_template

from ..theme import TEMPLATE_COLOR_HEX
from .widgets import (
    FrozenColumns,
    SimpleFormDialog,
    ZoomControl,
    apply_table_zoom,
    chars_width,
    color_dot_icon,
    icon_button,
    three_line_row_height,
)


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

    _TEMPLATE_SORTS = ["A–Z", "Z–A"]
    _SHIFT_SORTS = ["A–Z", "Z–A", "Start time"]

    def __init__(
        self,
        repository: Repository,
        schedule: Schedule | None = None,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
        department: str = "",
        zoom: float = 1.0,
        on_zoom_changed: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._department = department  # chosen in Settings -> General
        self._on_zoom_changed = on_zoom_changed
        # Shifts already assigned copy their times from a template, so a
        # timing edit here re-times them (services/shift_sync.py).
        self._schedule = schedule
        self._on_change = on_change
        self._shift_ids: list[ShiftId] = []
        self._templates: list[Template] = []
        self._timings: dict[tuple[str, str], ShiftTiming] = {}
        self._selected_template_row: int | None = None
        self._selected_shift_id_col: int | None = None
        # Column widths the user dragged, keyed by shift ID (and
        # "__template__" for the name column), so a re-render after an edit
        # doesn't snap them back to the default.
        self._column_widths: dict[str, int] = {}
        self._column_keys: list[str] = []

        self.subdepartment_combo = QComboBox()
        self.subdepartment_combo.setToolTip("Templates and Shift IDs belong to one subdepartment")
        self.subdepartment_combo.currentTextChanged.connect(self._on_subdepartment_changed)

        top_row = QHBoxLayout()
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

        # Sort order for the matrix. A–Z is "natural": 2 before 10.
        self.template_sort_combo = QComboBox()
        self.template_sort_combo.addItems(self._TEMPLATE_SORTS)
        self.template_sort_combo.setObjectName("compactCombo")
        self.template_sort_combo.setToolTip("Order of the template rows")
        self.shift_sort_combo = QComboBox()
        self.shift_sort_combo.addItems(self._SHIFT_SORTS)
        self.shift_sort_combo.setObjectName("compactCombo")
        self.shift_sort_combo.setToolTip("Order of the Shift ID columns")
        self.template_sort_combo.currentTextChanged.connect(lambda _: self._sort_and_render())
        self.shift_sort_combo.currentTextChanged.connect(lambda _: self._sort_and_render())
        button_row.addWidget(QLabel("Sort templates"))
        button_row.addWidget(self.template_sort_combo)
        button_row.addSpacing(12)
        button_row.addWidget(QLabel("Sort shift IDs"))
        button_row.addWidget(self.shift_sort_combo)
        self._zoom_initial = zoom
        self._button_row = button_row

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
        self.matrix_table.horizontalHeader().sectionDoubleClicked.connect(self._on_column_header_double_clicked)
        # Right-click is a second way to add/edit/delete, alongside the icon
        # rows above.
        self.matrix_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.matrix_table.customContextMenuRequested.connect(self._show_matrix_context_menu)
        self.matrix_table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.matrix_table.horizontalHeader().customContextMenuRequested.connect(
            self._show_shift_id_header_context_menu
        )
        # The Template column stays put while the Shift ID columns scroll.
        self._frozen = FrozenColumns(self.matrix_table, 1)
        self._frozen.view.doubleClicked.connect(lambda index: self._edit_cell(index.row(), index.column()))
        self._frozen.view.clicked.connect(lambda index: self._on_cell_clicked(index.row(), index.column()))
        self._frozen.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._frozen.view.customContextMenuRequested.connect(self._show_frozen_context_menu)

        self._zoom = 0.0
        self.zoom_control = ZoomControl(self.matrix_table, self._zoom_initial)
        self.zoom_control.zoom_changed.connect(self._on_zoom)
        button_row.addSpacing(12)
        button_row.addWidget(self.zoom_control)
        self._apply_zoom(self.zoom_control.zoom())

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addLayout(button_row)
        layout.addWidget(self.matrix_table, stretch=1)
        # Filled in showEvent, not here: nothing is read until the page is
        # actually opened.

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._reload_subdepartments()

    def _apply_zoom(self, zoom: float) -> None:
        apply_table_zoom(self.matrix_table, zoom, self._zoom)
        self._zoom = zoom
        self.matrix_table.verticalHeader().setDefaultSectionSize(three_line_row_height(self.matrix_table))

    def _on_zoom(self, zoom: float) -> None:
        self._apply_zoom(zoom)
        for row in range(self.matrix_table.rowCount()):
            self.matrix_table.setRowHeight(row, three_line_row_height(self.matrix_table))
        if self._on_zoom_changed:
            self._on_zoom_changed(zoom)

    def select_subdepartment(self, name: str) -> None:
        """Show this subdepartment (Month view's "Open in Templates")."""
        self._reload_subdepartments()
        index = self.subdepartment_combo.findText(name)
        if index >= 0:
            self.subdepartment_combo.setCurrentIndex(index)

    # --- subdepartments ----------------------------------------------------

    def _reload_subdepartments(self) -> None:
        current = self.subdepartment_combo.currentText()
        options = self._repository.load_subdepartments(self._department or None)
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
        self._sort_and_render()

    def _sort_and_render(self) -> None:
        """Order templates and shift IDs as the two Sort combos say. Row and
        column selections refer to positions, so they are cleared."""
        self._selected_template_row = None
        self._selected_shift_id_col = None
        reverse = self.template_sort_combo.currentText() == "Z–A"
        self._templates.sort(key=lambda t: natural_key(t.name), reverse=reverse)
        shift_sort = self.shift_sort_combo.currentText()
        if shift_sort == "Start time":
            def earliest(shift_id: ShiftId):
                starts = [
                    min(seg.start_minutes for seg in timing.segments)
                    for (_, sid), timing in self._timings.items()
                    if sid == shift_id.id and timing.segments
                ]
                return (min(starts) if starts else 10**6, natural_key(shift_id.code))
            self._shift_ids.sort(key=earliest)
        else:
            self._shift_ids.sort(key=lambda sid: natural_key(sid.code), reverse=shift_sort == "Z–A")
        self._render_matrix()

    def _render_matrix(self) -> None:
        # Column 0 is the Template name itself, a plain resizable column —
        # NOT a vertical-header label. Qt's vertical header only lets the
        # user drag row *height*, not header *width*, so a real column is
        # what actually makes "Split_AM_PM" draggable wider.
        table = self.matrix_table
        self._remember_column_widths()
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

        # Every column gets the width the user last gave it; only a column
        # never seen before starts at the default.
        default_width = chars_width(table, 20)
        keys = ["__template__"] + [s.id for s in self._shift_ids]
        for col, key in enumerate(keys):
            table.horizontalHeader().resizeSection(col, self._column_widths.get(key, default_width))
        self._column_keys = keys
        self._frozen.sync()

    def _remember_column_widths(self) -> None:
        header = self.matrix_table.horizontalHeader()
        for col, key in enumerate(self._column_keys):
            if col < header.count():
                self._column_widths[key] = header.sectionSize(col)

    def _on_row_header_clicked(self, row: int) -> None:
        self._selected_template_row = row

    def _on_column_header_clicked(self, col: int) -> None:
        if col == 0:
            return  # the "Template" header, not a shift ID
        self._selected_shift_id_col = col - 1

    def _on_column_header_double_clicked(self, col: int) -> None:
        """Double-click a shift ID's header to edit it — same gesture as
        double-clicking a template's name."""
        if col == 0:
            return  # the "Template" header, not a shift ID
        self._selected_shift_id_col = col - 1
        self._edit_shift_id()

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

        self._retime(template.id)
        self._render_matrix()

    def _retime(self, template_id: str) -> None:
        """Shifts already assigned on days that use this template pick up
        the new timing."""
        if self._schedule is None:
            return
        if retime_template(self._schedule, self._repository, template_id) and self._on_change:
            self._on_change()

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

    def _show_frozen_context_menu(self, position) -> None:
        index = self._frozen.view.indexAt(position)
        if not index.isValid():
            return
        self._selected_template_row = index.row()
        menu = QMenu(self._frozen.view)
        edit_action = menu.addAction("Edit template")
        delete_action = menu.addAction("Delete template")
        chosen = menu.exec(self._frozen.view.viewport().mapToGlobal(position))
        if chosen is edit_action:
            self._edit_template()
        elif chosen is delete_action:
            self._delete_template()

    def open_timing(self, template_id: str, code: str) -> None:
        """Select the (template, Shift ID) cell and open its timing editor."""
        row = next((i for i, t in enumerate(self._templates) if t.id == template_id), None)
        col = next((i + 1 for i, s in enumerate(self._shift_ids) if s.code == code), None)
        if row is None or col is None:
            return
        self.matrix_table.setCurrentCell(row, col)
        self.matrix_table.scrollTo(self.matrix_table.model().index(row, col))
        QTimer.singleShot(0, lambda: self._edit_cell(row, col))

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
        if code != shift_id.code and self._schedule is not None:
            # Shifts already assigned under the old code move to the new one.
            if rename_shift_code(self._schedule, self._repository, shift_id.subdepartment, shift_id.code, code):
                if self._on_change:
                    self._on_change()
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


class TemplatesPanel(QTabWidget):
    """Templates & Shift IDs. The Location code catalog that used to be a
    second tab here now lives in Settings -> Lists."""

    def __init__(
        self,
        repository: Repository,
        schedule: Schedule | None = None,
        on_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
        department: str = "",
        zoom: float = 1.0,
        on_zoom_changed: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.matrix = TemplatesMatrixTab(
            repository, schedule, on_change, department=department, zoom=zoom, on_zoom_changed=on_zoom_changed
        )
        self.addTab(self.matrix, "Templates && Shift IDs")
        self.setTabToolTip(0, "Day plans (templates) and the shift timings inside each")

    def select_subdepartment(self, name: str) -> None:
        self.matrix.select_subdepartment(name)

    def open_timing(self, group: str, code: str, day) -> None:
        """Show `group`'s matrix and open the timing of `code` in the
        template used on `day`."""
        self.matrix.select_subdepartment(group)
        assignment = self.matrix._repository.load_template_assignment(group, day)
        if assignment is not None:
            self.matrix.open_timing(assignment.template_id, code)
