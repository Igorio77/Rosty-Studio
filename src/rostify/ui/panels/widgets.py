"""Shared UI building blocks — used by List Control, the Templates tab's
matrix toolbar, and its Location IDs table, so the "icon buttons + resizable
+ centered + ~3 lines" look is written once, not four times.

Qt lives here (this is `ui/`), but nothing here knows about a specific
domain concept (Employee, Template, ...) — that stays in each panel that
uses these.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
    QStyledItemDelegate,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..theme import COLORS


def icon_button(glyph: str, tooltip: str) -> QPushButton:
    """A small square button standing in for an icon. No icon-asset
    pipeline exists yet in this phase (no resource file, no PyInstaller
    data-file wiring) — a text glyph is this phase's icon, same "keep it
    small, revisit later" spirit as the rest of Phase 0.
    """
    button = QPushButton(glyph)
    button.setToolTip(tooltip)
    button.setFixedSize(28, 28)
    # The app-wide QPushButton style (ui/theme.py) pads 6px/14px, which on a
    # fixed 28x28 button leaves no room at all for the glyph — override it
    # down to something that actually fits a square icon button.
    button.setStyleSheet("padding: 2px;")
    return button


def color_dot_icon(hex_color: str, size: int = 10) -> QIcon:
    """A small filled circle, used to mark a Template's color (its
    TEMPLATE_COLORS name -> hex comes from ui.theme.TEMPLATE_COLOR_HEX) next
    to its name — on the Templates matrix and the Month/Year calendar.

    Sized by the screen's device pixel ratio, same as `ui.icons`: painting
    into a plain `QPixmap(size, size)` and letting Qt scale it up is what
    makes a dot look furry at 125%/150% display scaling.
    """
    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen is not None else 1.0
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor(hex_color)))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return QIcon(pixmap)


#: `.roster-shift-badge` in reference/RostaStudioSchedule.jsx: a 26px square
#: with radius 8. Rostify runs one step larger (28px, the icon-button size in
#: the token table) because its shift codes are longer than the reference's
#: single digits, and a 4-character code has to stay legible.
SHIFT_BADGE_SIZE = 28


def shift_badge_button(code: str, hex_color: str | None, tooltip: str, scale: float = 1.0) -> QPushButton:
    """The colored shift badge, shared by the Custom view roster and the Day
    view's Shift ID column so both read the same.

    `hex_color` is a TEMPLATE_COLOR_HEX value — a *saturated* fill with dark
    ink on top, exactly like the reference, not a translucent tint. Pass
    None for "no shift assigned yet": that renders the reference's dashed
    `+` affordance instead.

    Width grows past the 28px square for longer codes; `padding` is set
    explicitly because the global QPushButton rule pads 6px/12px, which
    leaves a fixed-height badge no room to draw its text at all.

    `scale` is the grid's zoom factor, so the badge grows and shrinks with
    the rows it sits in.
    """
    size = max(round(SHIFT_BADGE_SIZE * scale), 16)
    font_px = max(round(12 * scale), 8)
    radius = max(round(8 * scale), 4)
    button = QPushButton(code or "+")
    button.setFlat(True)
    button.setFixedHeight(size)
    button.setMinimumWidth(size)
    button.setCursor(Qt.PointingHandCursor)
    button.setToolTip(tooltip)
    if code and hex_color:
        button.setStyleSheet(
            f"border: none; padding: 2px 6px; border-radius: {radius}px; font-size: {font_px}px; font-weight: 700; "
            f"background: {hex_color}; color: {COLORS['chip_on']};"
        )
    else:
        button.setStyleSheet(
            f"border: 1px dashed {COLORS['border_strong']}; padding: 2px 6px; border-radius: {radius}px; "
            f"font-size: {font_px}px; font-weight: 700; color: {COLORS['text_secondary']}; background: transparent;"
        )
    return button


def centered_in_cell(widget: QWidget) -> QWidget:
    """Wrap a widget so it sits in the middle of a table cell. A widget set
    straight into a cell with setCellWidget hugs the cell's left edge."""
    holder = QWidget()
    holder.setProperty("transparentBg", True)
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget, 0, Qt.AlignCenter)
    return holder


#: Zoom levels for the Day and Custom grids, the same stops Excel's zoom
#: menu steps through.
ZOOM_STEPS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
BASE_FONT_PX = 13


def clamp_zoom(value: float) -> float:
    return min(max(float(value), ZOOM_STEPS[0]), ZOOM_STEPS[-1])


class ZoomControl(QWidget):
    """"−  100%  +" beside a grid, plus Ctrl+mouse-wheel and Ctrl+= / Ctrl+-
    / Ctrl+0 on the grid itself. Emits `zoom_changed` with the new factor;
    the panel re-renders the grid at that size and the owner saves it, so
    the zoom is remembered next time.
    """

    zoom_changed = Signal(float)

    def __init__(self, table: QTableWidget, zoom: float = 1.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._zoom = clamp_zoom(zoom)

        minus = icon_button("−", "Zoom out (Ctrl+-, or Ctrl+mouse wheel)")
        plus = icon_button("+", "Zoom in (Ctrl+=, or Ctrl+mouse wheel)")
        self._label = QPushButton()
        self._label.setFlat(True)
        self._label.setToolTip("Reset zoom to 100% (Ctrl+0)")
        self._label.setFixedWidth(chars_width(self, 5))
        self._label.setStyleSheet("padding: 2px; border: none;")
        minus.clicked.connect(lambda: self.step(-1))
        plus.clicked.connect(lambda: self.step(1))
        self._label.clicked.connect(lambda: self.set_zoom(1.0))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(minus)
        layout.addWidget(self._label)
        layout.addWidget(plus)
        self._update_label()

        self._filter = _ZoomKeys(self)
        table.installEventFilter(self._filter)
        table.viewport().installEventFilter(self._filter)

    def zoom(self) -> float:
        return self._zoom

    def step(self, direction: int) -> None:
        if direction > 0:
            bigger = [z for z in ZOOM_STEPS if z > self._zoom + 1e-6]
            self.set_zoom(bigger[0] if bigger else ZOOM_STEPS[-1])
        else:
            smaller = [z for z in ZOOM_STEPS if z < self._zoom - 1e-6]
            self.set_zoom(smaller[-1] if smaller else ZOOM_STEPS[0])

    def set_zoom(self, value: float) -> None:
        value = clamp_zoom(value)
        if abs(value - self._zoom) < 1e-6:
            return
        self._zoom = value
        self._update_label()
        self.zoom_changed.emit(value)

    def _update_label(self) -> None:
        self._label.setText(f"{round(self._zoom * 100)}%")


class _ZoomKeys(QObject):
    """Ctrl+wheel and the Ctrl+= / Ctrl+- / Ctrl+0 keys on a grid."""

    def __init__(self, control: ZoomControl) -> None:
        super().__init__(control)
        self._control = control

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            self._control.step(1 if event.angleDelta().y() > 0 else -1)
            return True
        if event.type() == QEvent.KeyPress and event.modifiers() & Qt.ControlModifier:
            if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
                self._control.step(1)
                return True
            if event.key() == Qt.Key_Minus:
                self._control.step(-1)
                return True
            if event.key() == Qt.Key_0:
                self._control.set_zoom(1.0)
                return True
        return False


def apply_table_zoom(table: QTableWidget, zoom: float, previous: float) -> None:
    """Set a grid's text size for `zoom`, and scale every column width by
    the change, so widths the user dragged keep their proportions."""
    font_px = max(round(BASE_FONT_PX * zoom), 7)
    table.setStyleSheet(
        f"QTableView {{ font-size: {font_px}px; }} QHeaderView::section {{ font-size: {font_px}px; }}"
    )
    table.ensurePolished()
    if previous and abs(zoom - previous) > 1e-6:
        header = table.horizontalHeader()
        ratio = zoom / previous
        for col in range(header.count()):
            header.resizeSection(col, max(round(header.sectionSize(col) * ratio), 12))


class SettingsCard(QFrame):
    """A titled card: heading row (title plus optional controls on the
    right), an optional hint line, then `body` for the content. The
    reference's `.settings-section` — surface 2, hairline border, radius 12.
    """

    def __init__(self, title: str, hint: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsCard")

        title_label = QLabel(title)
        title_label.setProperty("role", "heading")

        self._header = QHBoxLayout()
        self._header.setSpacing(12)
        self._header.addWidget(title_label)
        self._header.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addLayout(self._header)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setWordWrap(True)
            hint_label.setProperty("role", "hint")
            layout.addWidget(hint_label)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        layout.addLayout(self.body)

    def add_header_widget(self, widget: QWidget) -> None:
        self._header.addWidget(widget)


def three_line_row_height(table: QTableWidget) -> int:
    """Default row height sized for ~3 wrapped lines of the table's font —
    shared by `IconTableEditor` and the Templates tab's bespoke matrix
    table, which needs the same look but can't use `IconTableEditor` itself
    (its cells open a dialog, not a plain editable list)."""
    return QFontMetrics(table.font()).lineSpacing() * 3 + 10


def chars_width(widget: QWidget, characters: int = 20) -> int:
    """Pixel width that fits `characters` of the widget's own font — the
    shared "default column width" used across Templates, Location IDs and
    Custom view, so a name/time-range column isn't left at Qt's cramped
    default width. Still just a *default*: every table here keeps
    `QHeaderView.Interactive`, so the user can drag it narrower or wider.
    """
    return QFontMetrics(widget.font()).horizontalAdvance("0" * characters) + 16


class _NewRowHintDelegate(QStyledItemDelegate):
    """Paints a grey hint ("Type a new code…") in the empty cell of the
    table's last, blank "new row" — a QTableWidgetItem has no placeholder
    text of its own, and real text there would end up inside the editor."""

    def __init__(self, hint: str, is_new_row: Callable[[int], bool], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hint = hint
        self._is_new_row = is_new_row

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        if index.column() == 0 and self._is_new_row(index.row()) and not index.data():
            painter.save()
            painter.setPen(QColor(COLORS["text_tertiary"]))
            painter.drawText(option.rect, Qt.AlignCenter, self._hint)
            painter.restore()


class IconTableEditor(QWidget):
    """A QTableWidget plus an add/edit/delete icon-button row.

    Renders and dispatches only — it doesn't know what "add"/"edit" mean
    for any particular list (which dialog to open, which repository call to
    make); the caller supplies that as three callbacks. That's what lets
    one widget serve Departments (1 column), Subdepartments (2 columns),
    Positions (2 columns) and Location codes (4 columns) without forcing a
    shared row shape.

    Pass `on_cell_edited` to allow typing straight into the cells (double-
    click, Enter or just start typing). The table then also shows one blank
    row at the bottom: typing into it adds a new entry. The callback gets
    (row, column, text); `row == row_count` means that new row.
    """

    def __init__(
        self,
        headers: list[str],
        on_add: Callable[[], None],
        on_edit: Callable[[int], None],
        on_delete: Callable[[int], None],
        parent: QWidget | None = None,
        on_cell_edited: Callable[[int, int, str], None] | None = None,
        new_row_hint: str = "Type to add…",
    ) -> None:
        super().__init__(parent)

        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_cell_edited = on_cell_edited
        self._row_count = 0  # real rows, not counting the blank new row
        self._filling = False  # set_rows is writing cells, not the user

        self.table = QTableWidget()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setWordWrap(True)
        # Same interaction pattern everywhere: click selects/highlights the
        # row (SelectRows), double-click edits — matches the Team tab.
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(three_line_row_height(self.table))
        default_width = chars_width(self.table, 20)
        for column in range(len(headers)):
            self.table.horizontalHeader().resizeSection(column, default_width)
        if on_cell_edited is None:
            self.table.doubleClicked.connect(lambda _: self._with_selected(on_edit))
        else:
            self.table.setEditTriggers(
                QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
            )
            self.table.setItemDelegate(
                _NewRowHintDelegate(new_row_hint, lambda row: row == self._row_count, self.table)
            )
            self.table.itemChanged.connect(self._on_item_changed)
        # Right-click is a second way to add/edit/delete, alongside the icon
        # row above — same three actions, so the icons stay the discoverable
        # default but a mouse-only flow doesn't need them once it's learned.
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        add_button = icon_button("+", "Add")
        edit_button = icon_button("✎", "Edit selected")  # pencil
        delete_button = icon_button("\U0001f5d1", "Delete selected")  # wastebasket
        add_button.clicked.connect(on_add)
        edit_button.clicked.connect(lambda: self._with_selected(on_edit))
        delete_button.clicked.connect(lambda: self._with_selected(on_delete))

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(edit_button)
        button_row.addWidget(delete_button)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self.table)

    def set_rows(self, rows: list[tuple[str, ...]]) -> None:
        editable = self._on_cell_edited is not None
        self._row_count = len(rows)
        self._filling = True
        try:
            self.table.setRowCount(len(rows) + (1 if editable else 0))
            for row_index, values in enumerate(rows):
                for col_index, value in enumerate(values):
                    self.table.setItem(row_index, col_index, self._make_item(str(value), editable))
            if editable:
                # The blank new row: only its first cell is editable, the
                # rest fill in once that first value exists.
                for col_index in range(self.table.columnCount()):
                    self.table.setItem(len(rows), col_index, self._make_item("", col_index == 0))
        finally:
            self._filling = False

    @staticmethod
    def _make_item(text: str, editable: bool) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._filling or self._on_cell_edited is None:
            return
        # Deferred: the callback usually reloads the table, and replacing
        # items from inside their own itemChanged signal can crash Qt.
        row, column, text = item.row(), item.column(), item.text().strip()
        QTimer.singleShot(0, lambda: self._on_cell_edited(row, column, text))

    def _with_selected(self, callback: Callable[[int], None]) -> None:
        row = self.table.currentRow()
        if 0 <= row < self._row_count:
            callback(row)

    def _show_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row >= self._row_count:
            row = -1  # the blank new row has nothing to edit or delete
        if row >= 0:
            self.table.selectRow(row)
        menu = QMenu(self.table)
        add_action = menu.addAction("Add")
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        edit_action.setEnabled(row >= 0)
        delete_action.setEnabled(row >= 0)
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is add_action:
            self._on_add()
        elif chosen is edit_action:
            self._with_selected(self._on_edit)
        elif chosen is delete_action:
            self._with_selected(self._on_delete)


class SimpleFormDialog(QDialog):
    """One `QLineEdit` per field, or a `QComboBox` when a field is given a
    `choices` list. Covers every add/edit dialog in this app except
    Employee, which needs real Department->Subdepartment cascading and a
    password field a generic form doesn't provide.
    """

    def __init__(
        self,
        title: str,
        fields: list[tuple[str, list[str] | None]],
        initial: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._widgets: list[QLineEdit | QComboBox] = []

        form = QFormLayout()
        for index, (label, choices) in enumerate(fields):
            prefill = initial[index] if initial and index < len(initial) else ""
            widget: QLineEdit | QComboBox
            if choices is not None:
                widget = QComboBox()
                widget.addItems(choices)
                if prefill in choices:
                    widget.setCurrentText(prefill)
            else:
                widget = QLineEdit(prefill)
            form.addRow(label, widget)
            self._widgets.append(widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> list[str]:
        return [
            widget.currentText().strip() if isinstance(widget, QComboBox) else widget.text().strip()
            for widget in self._widgets
        ]


class DepartmentSubdepartmentSelector(QWidget):
    """The Department -> Subdepartment cascading combo pair, as its own
    widget. `TemplatesMatrixTab` and `CustomViewPanel` each grew this cascade
    inline before this existed; new panels (the Month/Year calendar) use
    this instead of writing it a third and fourth time.
    """

    subdepartment_changed = Signal(str)

    def __init__(self, repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repository = repository

        self.department_combo = QComboBox()
        self.subdepartment_combo = QComboBox()
        self.department_combo.currentTextChanged.connect(self._reload_subdepartments)
        self.subdepartment_combo.currentTextChanged.connect(self.subdepartment_changed.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Department"))
        layout.addWidget(self.department_combo)
        layout.addWidget(QLabel("Subdepartment"))
        layout.addWidget(self.subdepartment_combo)

        self.reload()

    def reload(self) -> None:
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
        self.subdepartment_changed.emit(self.subdepartment_combo.currentText())

    def current_subdepartment(self) -> str:
        return self.subdepartment_combo.currentText().strip()


class FrozenColumns(QObject):
    """Excel's "freeze panes" for the first `count` columns of a table.

    A second view is laid over the table's left edge, sharing its model and
    its selection, showing only the frozen columns. It scrolls up and down
    with the table but never sideways, so names and ids stay visible while
    a wide timeline scrolls underneath. Widgets that belong in a frozen
    column (e.g. shift badges) go on this view — `set_cell_widget` — not on
    the table. Call `sync()` after every re-render.
    """

    def __init__(self, table: QTableWidget, count: int) -> None:
        super().__init__(table)
        self._table = table
        self._count = count
        view = QTableView(table)
        view.setObjectName("frozenColumns")
        view.setModel(table.model())
        view.setSelectionModel(table.selectionModel())
        view.setFocusPolicy(Qt.NoFocus)
        view.verticalHeader().hide()
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollMode(table.verticalScrollMode())
        view.setSelectionBehavior(table.selectionBehavior())
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setWordWrap(table.wordWrap())
        view.setFrameShape(QFrame.NoFrame)
        view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        view.horizontalHeader().setHighlightSections(False)
        self.view = view
        self._syncing = False

        table.verticalScrollBar().valueChanged.connect(view.verticalScrollBar().setValue)
        view.verticalScrollBar().valueChanged.connect(table.verticalScrollBar().setValue)
        table.horizontalHeader().sectionResized.connect(self._table_column_resized)
        view.horizontalHeader().sectionResized.connect(self._frozen_column_resized)
        table.verticalHeader().sectionResized.connect(lambda row, _old, new: view.setRowHeight(row, new))
        table.installEventFilter(self)
        view.show()
        self.sync()

    def set_cell_widget(self, row: int, column: int, widget: QWidget) -> None:
        self.view.setIndexWidget(self._table.model().index(row, column), widget)

    def sync(self) -> None:
        """Columns, spans, row heights and position after the table changed."""
        table, view = self._table, self.view
        self._syncing = True
        try:
            for column in range(table.columnCount()):
                view.setColumnHidden(column, column >= self._count)
                if column < self._count:
                    view.setColumnWidth(column, table.columnWidth(column))
            view.clearSpans()
            for row in range(table.rowCount()):
                view.setRowHeight(row, table.rowHeight(row))
                span = table.columnSpan(row, 0)
                if span > 1:
                    view.setSpan(row, 0, 1, min(span, self._count))
        finally:
            self._syncing = False
        self._place()

    def _table_column_resized(self, column: int, _old: int, new: int) -> None:
        if column < self._count and not self._syncing:
            self.view.setColumnWidth(column, new)
            self._place()

    def _frozen_column_resized(self, column: int, _old: int, new: int) -> None:
        if column < self._count and not self._syncing:
            self._table.setColumnWidth(column, new)
            self._place()

    def _place(self) -> None:
        table = self._table
        header_height = table.horizontalHeader().height()
        self.view.horizontalHeader().setFixedHeight(header_height)
        width = sum(table.columnWidth(c) for c in range(min(self._count, table.columnCount())))
        frame = table.frameWidth()
        x = frame + (table.verticalHeader().width() if table.verticalHeader().isVisible() else 0)
        self.view.setGeometry(x, frame, width, table.viewport().height() + header_height)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self._table and event.type() in (QEvent.Resize, QEvent.Show, QEvent.LayoutRequest):
            self._place()
        return False


def show_shift_error(parent: QWidget, error, open_timing: Callable | None = None) -> None:
    """Tell the user why a shift was not assigned. When the fix is a
    missing timing, offer "Open in Templates", which jumps straight to that
    Shift ID in the day's template (`open_timing(group, code, day)`)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Shift not assigned")
    box.setText(str(error))
    jump = None
    if getattr(error, "missing_timing", False) and open_timing is not None:
        jump = box.addButton("Open in Templates", QMessageBox.AcceptRole)
        jump.setToolTip("Go to this Shift ID in the day's template and set its timing")
    box.addButton(QMessageBox.Close)
    box.exec()
    if jump is not None and box.clickedButton() is jump:
        open_timing(error.group, error.code, error.day)
