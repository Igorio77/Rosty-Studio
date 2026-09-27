"""Team tab: a table of employees backed by the Schedule aggregate, plus
add/edit/delete. Department/Subdepartment/Position are dropdown-only,
sourced from the admin-managed lists in Settings -> Lists
(list_control_panel.py) — no free text for those three fields anymore.

Two tabs: Crew and Archive. Archiving someone (not on board, left the
company) takes them out of every schedule and rotation but keeps their
record; Restore brings them back. Separately, an employee can be marked
"temporarily not available" for a date range: they stay everywhere, greyed
out on those days.
"""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QAbstractTableModel, QDate, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Employee
from rostify.core.schedule import Schedule
from rostify.services.auth import hash_password
from rostify.services.persistence import Repository

from ..theme import COLORS
from .widgets import ZoomControl, apply_table_zoom, icon_button

SEQUENCE_COLUMN = "_seq"  # not a real Employee field — a computed 1-based row number
COLUMNS = [SEQUENCE_COLUMN, "first_name", "last_name", "id", "department", "subdepartment", "position", "email", "password_hash", "active"]
HEADERS = ["#", "First Name", "Last Name", "Employee ID", "Department", "Subdepartment", "Position", "Email", "Password", "Status"]
COLUMN_WIDTHS = [40, 120, 120, 100, 100, 120, 120, 160, 100, 190]


def _short(day: date) -> str:
    return f"{day.day} {day.strftime('%b')}"


def availability_text(employee: Employee) -> str:
    if employee.archived:
        return "Archived"
    if employee.unavailable_from is None:
        return "Available"
    end = employee.unavailable_to or employee.unavailable_from
    if end < date.today():
        return "Available"
    return f"Not available {_short(employee.unavailable_from)} – {_short(end)}"


def _to_qdate(day: date) -> QDate:
    return QDate(day.year, day.month, day.day)


def _from_qdate(qd: QDate) -> date:
    return date(qd.year(), qd.month(), qd.day())


class EmployeeTableModel(QAbstractTableModel):
    """Holds whatever rows it's given — filtering lives in StaffPanel, not
    here, since "which employees" depends on filter controls this model
    doesn't know about."""

    def __init__(self, rows: list[Employee] | None = None) -> None:
        super().__init__()
        self._rows: list[Employee] = rows or []

    def set_rows(self, rows: list[Employee]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def employee_at(self, row: int) -> Employee | None:
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(COLUMNS)

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        employee = self._rows[index.row()]
        if role == Qt.ForegroundRole:
            # Greyed out while temporarily not available.
            return QColor(COLORS["text_tertiary"]) if employee.is_unavailable_on(date.today()) else None
        if role != Qt.DisplayRole:
            return None
        field = COLUMNS[index.column()]
        if field == SEQUENCE_COLUMN:
            return str(index.row() + 1)
        value = getattr(employee, field)
        if field == "active":
            return availability_text(employee)
        if field == "password_hash":
            return "Set" if value else "—"
        return value


class EmployeeDialog(QDialog):
    """Add or edit an employee. Department/Subdepartment/Position are
    dropdowns sourced from Repository's List Control tables (Subdepartment
    cascades off Department, same as the Templates tab's selector). Password
    is masked; leaving it blank means "no password" on add, or "leave the
    existing one unchanged" on edit — it's never displayed or round-tripped
    as plain text.
    """

    def __init__(
        self,
        repository: Repository,
        existing: Employee | None = None,
        parent: QWidget | None = None,
        *,
        preset_department: str = "",
        preset_subdepartment: str = "",
    ) -> None:
        """`preset_*` prefill Department/Subdepartment when adding, so a
        panel that already knows which subdepartment it is showing (the
        Custom view) does not make the user pick it again. They are ignored
        when `existing` is given — an edit always shows that employee's own
        values.
        """
        super().__init__(parent)
        self.setWindowTitle("Edit employee" if existing else "Add employee")
        self._repository = repository
        self._existing = existing

        self.id_edit = QLineEdit(existing.id if existing else "")
        self.id_edit.setEnabled(existing is None)  # the join key never changes once created

        self.first_name_edit = QLineEdit(existing.first_name if existing else "")
        self.last_name_edit = QLineEdit(existing.last_name if existing else "")

        self.department_combo = QComboBox()
        self.department_combo.addItems(repository.load_departments())
        # Set before the subdepartment combo is built below: that one is
        # populated from whatever department is current at the time.
        wanted_department = existing.department if existing else preset_department
        if wanted_department:
            index = self.department_combo.findText(wanted_department)
            if index >= 0:
                self.department_combo.setCurrentIndex(index)

        self.subdepartment_combo = QComboBox()
        self._reload_subdepartments(self.department_combo.currentText())
        wanted_subdepartment = existing.subdepartment if existing else preset_subdepartment
        if wanted_subdepartment:
            index = self.subdepartment_combo.findText(wanted_subdepartment)
            if index >= 0:
                self.subdepartment_combo.setCurrentIndex(index)
        self.department_combo.currentTextChanged.connect(self._reload_subdepartments)

        # Positions belong to a department, so this list follows the
        # Department combo the same way Subdepartment does.
        self.position_combo = QComboBox()
        self._reload_positions(self.department_combo.currentText())
        if existing:
            index = self.position_combo.findText(existing.position)
            if index >= 0:
                self.position_combo.setCurrentIndex(index)
            elif existing.position:
                # Kept visible even if it's no longer in the list, so saving
                # the form doesn't silently change it.
                self.position_combo.addItem(existing.position)
                self.position_combo.setCurrentText(existing.position)
        self.department_combo.currentTextChanged.connect(self._reload_positions)

        self.email_edit = QLineEdit(existing.email if existing else "")

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(
            "Leave blank to keep unchanged" if existing else "Leave blank for no password"
        )

        # "Temporarily not available", with a date range. Archiving is not
        # here: it has its own button on the Team tab.
        self.unavailable_check = QCheckBox("Temporarily not available")
        start = existing.unavailable_from if existing and existing.unavailable_from else date.today()
        end = existing.unavailable_to if existing and existing.unavailable_to else start + timedelta(days=6)
        self.unavailable_from_edit = QDateEdit(_to_qdate(start))
        self.unavailable_from_edit.setCalendarPopup(True)
        self.unavailable_to_edit = QDateEdit(_to_qdate(end))
        self.unavailable_to_edit.setCalendarPopup(True)
        self.unavailable_check.toggled.connect(self.unavailable_from_edit.setEnabled)
        self.unavailable_check.toggled.connect(self.unavailable_to_edit.setEnabled)
        self.unavailable_check.setChecked(bool(existing and existing.unavailable_from))
        self.unavailable_from_edit.setEnabled(self.unavailable_check.isChecked())
        self.unavailable_to_edit.setEnabled(self.unavailable_check.isChecked())
        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("From"))
        period_row.addWidget(self.unavailable_from_edit)
        period_row.addWidget(QLabel("To"))
        period_row.addWidget(self.unavailable_to_edit)
        period_row.addStretch(1)

        form = QFormLayout()
        form.addRow("Employee ID", self.id_edit)
        form.addRow("First Name", self.first_name_edit)
        form.addRow("Last Name", self.last_name_edit)
        form.addRow("Department", self.department_combo)
        form.addRow("Subdepartment", self.subdepartment_combo)
        form.addRow("Position", self.position_combo)
        form.addRow("Email", self.email_edit)
        form.addRow("Password", self.password_edit)
        form.addRow("", self.unavailable_check)
        form.addRow("", period_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _reload_subdepartments(self, department: str) -> None:
        self.subdepartment_combo.clear()
        if department:
            options = self._repository.load_subdepartments(department)
            self.subdepartment_combo.addItems([o.name for o in options])

    def _reload_positions(self, department: str) -> None:
        self.position_combo.clear()
        if department:
            self.position_combo.addItems([p.name for p in self._repository.load_positions(department)])

    def employee(self) -> Employee:
        password_text = self.password_edit.text()
        if password_text:
            password_hash = hash_password(password_text)
        elif self._existing is not None:
            password_hash = self._existing.password_hash
        else:
            password_hash = ""

        return Employee(
            id=self.id_edit.text().strip(),
            first_name=self.first_name_edit.text().strip(),
            last_name=self.last_name_edit.text().strip(),
            department=self.department_combo.currentText(),
            subdepartment=self.subdepartment_combo.currentText(),
            position=self.position_combo.currentText(),
            email=self.email_edit.text().strip(),
            password_hash=password_hash,
            active=self._existing.active if self._existing is not None else True,
            unavailable_from=self._period()[0],
            unavailable_to=self._period()[1],
        )

    def _period(self) -> tuple[date | None, date | None]:
        if not self.unavailable_check.isChecked():
            return None, None
        start = _from_qdate(self.unavailable_from_edit.date())
        end = _from_qdate(self.unavailable_to_edit.date())
        return (start, end) if start <= end else (end, start)


class StaffPanel(QWidget):
    def __init__(
        self,
        schedule: Schedule,
        repository: Repository,
        on_change=None,
        parent: QWidget | None = None,
        department: str = "",
        zoom: float = 1.0,
        on_zoom_changed=None,
    ) -> None:
        super().__init__(parent)
        self._on_zoom_changed = on_zoom_changed
        self._schedule = schedule
        self._repository = repository
        self._on_change = on_change
        self._department = department  # chosen in Settings -> General

        self.subdepartment_combo = QComboBox()
        self.subdepartment_combo.setToolTip("Show one subdepartment, or All")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search name or id…")
        self.search_edit.setToolTip("Filter by name or employee id")

        self.tabs = QTabBar()
        self.tabs.addTab("Employees")
        self.tabs.addTab("Archive")
        self.tabs.setTabToolTip(0, "All current employees: available, or greyed out while temporarily not available")
        self.tabs.setTabToolTip(1, "Archived: kept on file, but out of every schedule and rotation")
        self.tabs.setExpanding(False)
        self.tabs.currentChanged.connect(lambda _: self._on_tab_changed())

        self.subdepartment_combo.currentTextChanged.connect(self._apply_filters)
        self.search_edit.textChanged.connect(self._apply_filters)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Subdepartment"))
        filter_row.addWidget(self.subdepartment_combo)
        filter_row.addWidget(self.search_edit, 1)

        self.model = EmployeeTableModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        # NOT setStretchLastSection(True): with this app's QSS theme, Qt
        # fails to paint the label of a stretched-to-fill last header
        # section (reproduced with QTableView.grab() in isolation — every
        # other header paints, "Status" doesn't) even though the model
        # returns its text correctly. Plain Interactive resize (Qt's
        # default) avoids the bug and still lets the user drag every
        # column, which is what was actually asked for.
        for column, width in enumerate(COLUMN_WIDTHS):
            self.table.horizontalHeader().resizeSection(column, width)
        self.table.doubleClicked.connect(lambda _: self._edit_employee())
        # Right-click is a second way to add/edit/delete, alongside the icon
        # row below — same three actions as the icons, just reachable
        # without leaving the row under the cursor.
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        add_button = icon_button("+", "Add employee")
        edit_button = icon_button("✎", "Edit selected employee")
        delete_button = icon_button("\U0001f5d1", "Delete selected employee")
        add_button.clicked.connect(self._add_employee)
        edit_button.clicked.connect(self._edit_employee)
        delete_button.clicked.connect(self._delete_employee)

        # Archive on the Crew tab, Restore on the Archive tab.
        self.archive_button = QPushButton("Archive")
        self.archive_button.setToolTip("Move the selected employee to the Archive: out of every schedule and rotation")
        self.archive_button.clicked.connect(self._toggle_archive)

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(edit_button)
        button_row.addWidget(delete_button)
        button_row.addSpacing(12)
        button_row.addWidget(self.archive_button)
        button_row.addStretch(1)
        self._zoom = 0.0
        self.zoom_control = ZoomControl(self.table, zoom)
        self.zoom_control.zoom_changed.connect(self._on_zoom)
        button_row.addWidget(self.zoom_control)
        self._apply_zoom(self.zoom_control.zoom())

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addLayout(filter_row)
        layout.addLayout(button_row)
        layout.addWidget(self.table)
        # Filled in showEvent, not here: nothing is read until the page is
        # actually opened.

    def showEvent(self, event) -> None:  # noqa: N802
        """Re-read the Schedule aggregate every time this page is shown.

        Employees can now be added from the Custom view too, and both
        panels hold the same live `Schedule`; without this the Team table
        would keep showing the roster as it stood when the window opened.
        """
        super().showEvent(event)
        self._reload_filter_options()
        self._apply_filters()

    def _reload_filter_options(self) -> None:
        employees = self._department_employees()
        self._set_combo_items(self.subdepartment_combo, sorted({e.subdepartment for e in employees}))

    @staticmethod
    def _set_combo_items(combo: QComboBox, items: list[str]) -> None:
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("All")
        combo.addItems(items)
        index = combo.findText(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _apply_filters(self) -> None:
        employees = self._department_employees()
        subdepartment = self.subdepartment_combo.currentText()
        search = self.search_edit.text().strip().lower()

        if subdepartment and subdepartment != "All":
            employees = [e for e in employees if e.subdepartment == subdepartment]
        if search:
            employees = [e for e in employees if search in e.full_name.lower() or search in e.id.lower()]
        archive = self._showing_archive()
        employees = [e for e in employees if e.archived == archive]

        self.model.set_rows(employees)

    def _apply_zoom(self, zoom: float) -> None:
        apply_table_zoom(self.table, zoom, self._zoom)
        self._zoom = zoom
        self.table.verticalHeader().setDefaultSectionSize(round(30 * zoom))

    def _on_zoom(self, zoom: float) -> None:
        self._apply_zoom(zoom)
        if self._on_zoom_changed:
            self._on_zoom_changed(zoom)

    def _department_employees(self) -> list[Employee]:
        employees = self._schedule.employees(active_only=False)
        return [e for e in employees if e.department == self._department] if self._department else employees

    def _showing_archive(self) -> bool:
        return self.tabs.currentIndex() == 1

    def _on_tab_changed(self) -> None:
        archive = self._showing_archive()
        self.archive_button.setText("Restore" if archive else "Archive")
        self.archive_button.setToolTip(
            "Bring the selected employee back to Employees"
            if archive
            else "Move the selected employee to the Archive: out of every schedule and rotation"
        )
        self._apply_filters()

    def _toggle_archive(self) -> None:
        employee = self._selected_employee()
        if employee is None:
            QMessageBox.information(self, "No selection", "Select an employee first.")
            return
        employee.active = self._showing_archive()  # Restore on Archive tab, Archive on Crew tab
        self._schedule.add_employee(employee)
        self._repository.save_employee(employee)
        self._apply_filters()
        if self._on_change:
            self._on_change()

    def _selected_employee(self) -> Employee | None:
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        return self.model.employee_at(index.row())

    def _show_context_menu(self, position) -> None:
        row = self.table.indexAt(position).row()
        if row >= 0:
            self.table.selectRow(row)
        menu = QMenu(self.table)
        add_action = menu.addAction("Add employee")
        edit_action = menu.addAction("Edit employee")
        delete_action = menu.addAction("Delete employee")
        menu.addSeparator()
        archive_action = menu.addAction("Restore to Employees" if self._showing_archive() else "Move to archive")
        edit_action.setEnabled(row >= 0)
        delete_action.setEnabled(row >= 0)
        archive_action.setEnabled(row >= 0)
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is archive_action:
            self._toggle_archive()
        elif chosen is add_action:
            self._add_employee()
        elif chosen is edit_action:
            self._edit_employee()
        elif chosen is delete_action:
            self._delete_employee()

    def _add_employee(self) -> None:
        dialog = EmployeeDialog(self._repository, parent=self, preset_department=self._department)
        if dialog.exec() != QDialog.Accepted:
            return
        employee = dialog.employee()
        if not employee.id or not employee.first_name or not employee.last_name:
            return
        self._schedule.add_employee(employee)
        self._reload_filter_options()
        self._apply_filters()
        if self._on_change:
            self._on_change()

    def _edit_employee(self) -> None:
        employee = self._selected_employee()
        if employee is None:
            QMessageBox.information(self, "No selection", "Select an employee first.")
            return
        dialog = EmployeeDialog(self._repository, existing=employee, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        updated = dialog.employee()
        if not updated.first_name or not updated.last_name:
            return
        self._schedule.add_employee(updated)  # same id -> overwrites
        self._reload_filter_options()
        self._apply_filters()
        if self._on_change:
            self._on_change()

    def _delete_employee(self) -> None:
        employee = self._selected_employee()
        if employee is None:
            QMessageBox.information(self, "No selection", "Select an employee first.")
            return
        reply = QMessageBox.question(
            self,
            "Delete employee",
            f"Delete {employee.full_name} ({employee.id})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._schedule.remove_employee(employee.id)
        self._repository.delete_employee(employee.id)
        self._reload_filter_options()
        self._apply_filters()
        if self._on_change:
            self._on_change()
