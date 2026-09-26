"""Staff tab: a table of employees backed by the Schedule aggregate, plus
add/edit/delete. Department/Subdepartment/Position are dropdown-only,
sourced from the admin-managed lists in Settings -> List Control
(list_control_panel.py) — no free text for those three fields anymore.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Employee
from rostify.core.schedule import Schedule
from rostify.services.auth import hash_password
from rostify.services.persistence import Repository

from .widgets import icon_button

SEQUENCE_COLUMN = "_seq"  # not a real Employee field — a computed 1-based row number
COLUMNS = [SEQUENCE_COLUMN, "first_name", "last_name", "id", "department", "subdepartment", "position", "email", "password_hash", "active"]
HEADERS = ["#", "First name", "Last Name", "DI #", "Department", "Subdepartment", "Position", "Email", "Password", "Status"]
COLUMN_WIDTHS = [40, 120, 120, 100, 100, 120, 120, 160, 100, 80]


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
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        field = COLUMNS[index.column()]
        if field == SEQUENCE_COLUMN:
            return str(index.row() + 1)
        employee = self._rows[index.row()]
        value = getattr(employee, field)
        if field == "active":
            return "Yes" if value else "No"
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

        self.position_combo = QComboBox()
        self.position_combo.addItems(repository.load_positions())
        if existing:
            index = self.position_combo.findText(existing.position)
            if index >= 0:
                self.position_combo.setCurrentIndex(index)

        self.email_edit = QLineEdit(existing.email if existing else "")

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(
            "Leave blank to keep unchanged" if existing else "Leave blank for no password"
        )

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])
        if existing is not None:
            self.status_combo.setCurrentText("Active" if existing.active else "Inactive")

        form = QFormLayout()
        form.addRow("Employee id", self.id_edit)
        form.addRow("First name", self.first_name_edit)
        form.addRow("Last name", self.last_name_edit)
        form.addRow("Department", self.department_combo)
        form.addRow("Subdepartment", self.subdepartment_combo)
        form.addRow("Position", self.position_combo)
        form.addRow("Email", self.email_edit)
        form.addRow("Password", self.password_edit)
        form.addRow("Status", self.status_combo)

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
            active=self.status_combo.currentText() == "Active",
        )


class StaffPanel(QWidget):
    def __init__(
        self, schedule: Schedule, repository: Repository, on_change=None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._schedule = schedule
        self._repository = repository
        self._on_change = on_change

        self.department_combo = QComboBox()
        self.subdepartment_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search name or id…")
        self.active_only_check = QCheckBox("Active only")

        self.department_combo.currentTextChanged.connect(self._apply_filters)
        self.subdepartment_combo.currentTextChanged.connect(self._apply_filters)
        self.search_edit.textChanged.connect(self._apply_filters)
        self.active_only_check.toggled.connect(self._apply_filters)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Department"))
        filter_row.addWidget(self.department_combo)
        filter_row.addWidget(QLabel("Subdepartment"))
        filter_row.addWidget(self.subdepartment_combo)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.active_only_check)

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

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(edit_button)
        button_row.addWidget(delete_button)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addLayout(button_row)
        layout.addWidget(self.table)

        self._reload_filter_options()
        self._apply_filters()

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
        employees = self._schedule.employees(active_only=False)
        self._set_combo_items(self.department_combo, sorted({e.department for e in employees}))
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
        employees = self._schedule.employees(active_only=False)
        department = self.department_combo.currentText()
        subdepartment = self.subdepartment_combo.currentText()
        search = self.search_edit.text().strip().lower()

        if department and department != "All":
            employees = [e for e in employees if e.department == department]
        if subdepartment and subdepartment != "All":
            employees = [e for e in employees if e.subdepartment == subdepartment]
        if search:
            employees = [e for e in employees if search in e.full_name.lower() or search in e.id.lower()]
        if self.active_only_check.isChecked():
            employees = [e for e in employees if e.active]

        self.model.set_rows(employees)

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
        edit_action.setEnabled(row >= 0)
        delete_action.setEnabled(row >= 0)
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is add_action:
            self._add_employee()
        elif chosen is edit_action:
            self._edit_employee()
        elif chosen is delete_action:
            self._delete_employee()

    def _add_employee(self) -> None:
        dialog = EmployeeDialog(self._repository, parent=self)
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
