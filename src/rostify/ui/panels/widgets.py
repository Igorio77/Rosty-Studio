"""Shared UI building blocks — used by List Control, the Templates tab's
matrix toolbar, and its Location IDs table, so the "icon buttons + resizable
+ centered + ~3 lines" look is written once, not four times.

Qt lives here (this is `ui/`), but nothing here knows about a specific
domain concept (Employee, Template, ...) — that stays in each panel that
uses these.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
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
    QPushButton,
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


def shift_badge_button(code: str, hex_color: str | None, tooltip: str) -> QPushButton:
    """The colored shift badge, shared by the Custom view roster and the Day
    view's Shift ID column so both read the same.

    `hex_color` is a TEMPLATE_COLOR_HEX value — a *saturated* fill with dark
    ink on top, exactly like the reference, not a translucent tint. Pass
    None for "no shift assigned yet": that renders the reference's dashed
    `+` affordance instead.

    Width grows past the 28px square for longer codes; `padding` is set
    explicitly because the global QPushButton rule pads 6px/12px, which
    leaves a fixed-height badge no room to draw its text at all.
    """
    button = QPushButton(code or "+")
    button.setFlat(True)
    button.setFixedHeight(SHIFT_BADGE_SIZE)
    button.setMinimumWidth(SHIFT_BADGE_SIZE)
    button.setCursor(Qt.PointingHandCursor)
    button.setToolTip(tooltip)
    if code and hex_color:
        button.setStyleSheet(
            f"border: none; padding: 2px 6px; border-radius: 8px; font-size: 12px; font-weight: 700; "
            f"background: {hex_color}; color: {COLORS['chip_on']};"
        )
    else:
        button.setStyleSheet(
            f"border: 1px dashed {COLORS['border_strong']}; padding: 2px 6px; border-radius: 8px; "
            f"font-size: 12px; font-weight: 700; color: {COLORS['text_secondary']}; background: transparent;"
        )
    return button


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


class IconTableEditor(QWidget):
    """A QTableWidget plus an add/edit/delete icon-button row.

    Renders and dispatches only — it doesn't know what "add"/"edit" mean
    for any particular list (which dialog to open, which repository call to
    make); the caller supplies that as three callbacks. That's what lets
    one widget serve Departments (1 column), Subdepartments (2 columns),
    Positions (1 column) and Location IDs (4 columns) without forcing a
    shared row shape.
    """

    def __init__(
        self,
        headers: list[str],
        on_add: Callable[[], None],
        on_edit: Callable[[int], None],
        on_delete: Callable[[int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete

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
        self.table.doubleClicked.connect(lambda _: self._with_selected(on_edit))
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
        self.table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

    def _with_selected(self, callback: Callable[[int], None]) -> None:
        row = self.table.currentRow()
        if row >= 0:
            callback(row)

    def _show_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
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
