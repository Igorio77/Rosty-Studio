"""Schedule tab: a flat table of assignments (both layers together — layer
is just a column) plus a form to add one, wired straight through
RuleEngine.evaluate(). This is the panel that actually proves out CLAUDE.md's
first architectural rule: one engine, one form, both layers.

Deliberately not the paintable day grid from README.md's Phase 1 — that's a
much bigger UI investment or a proper design pass, not something to improvise
without seeing what the interaction should feel like first.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Assignment, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import LocationCode
from rostify.rules.base import RuleViolation, Severity
from rostify.rules.engine import RuleEngine

COLUMNS = ["employee", "department", "layer", "resource", "start", "end", "comment"]
HEADERS = ["Employee", "Department", "Layer", "Resource", "Start", "End", "Comment"]


class AssignmentTableModel(QAbstractTableModel):
    def __init__(self, schedule: Schedule) -> None:
        super().__init__()
        self._schedule = schedule
        self._rows: list[Assignment] = schedule.assignments()

    def assignment_at(self, row: int) -> Assignment | None:
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def refresh(self) -> None:
        self.beginResetModel()
        self._rows = self._schedule.assignments()
        self.endResetModel()

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
        a = self._rows[index.row()]
        field = COLUMNS[index.column()]
        if field == "employee":
            employee = self._schedule.get_employee(a.employee_id)
            return employee.full_name if employee else a.employee_id
        if field == "layer":
            return "Shift (A)" if a.layer == Layer.SHIFT else "Position (B)"
        if field in ("start", "end"):
            return getattr(a, field).strftime("%Y-%m-%d %H:%M")
        return getattr(a, field)


class AddAssignmentDialog(QDialog):
    def __init__(
        self,
        schedule: Schedule,
        location_codes: list[LocationCode],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add assignment")
        self._schedule = schedule

        self.employee_combo = QComboBox()
        for employee in schedule.employees():
            self.employee_combo.addItem(f"{employee.full_name} ({employee.id})", employee.id)

        self.layer_combo = QComboBox()
        self.layer_combo.addItem("Shift (layer A)", Layer.SHIFT)
        self.layer_combo.addItem("Position (layer B)", Layer.POSITION)

        self.resource_combo = QComboBox()
        self.resource_combo.setEditable(True)
        codes = sorted({lc.abbreviation for lc in location_codes})
        self.resource_combo.addItems(codes)

        now = datetime.now()
        self.start_edit = QDateTimeEdit(now)
        self.start_edit.setCalendarPopup(True)
        self.end_edit = QDateTimeEdit(now.replace(hour=(now.hour + 1) % 24))
        self.end_edit.setCalendarPopup(True)

        self.comment_edit = QLineEdit()

        form = QFormLayout()
        form.addRow("Employee", self.employee_combo)
        form.addRow("Layer", self.layer_combo)
        form.addRow("Resource / position code", self.resource_combo)
        form.addRow("Start", self.start_edit)
        form.addRow("End", self.end_edit)
        form.addRow("Comment", self.comment_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def assignment(self) -> Assignment | None:
        employee_id = self.employee_combo.currentData()
        if not employee_id:
            return None
        employee = self._schedule.get_employee(employee_id)
        return Assignment(
            employee_id=employee_id,
            start=self.start_edit.dateTime().toPython(),
            end=self.end_edit.dateTime().toPython(),
            resource=self.resource_combo.currentText().strip(),
            layer=self.layer_combo.currentData(),
            department=employee.subdepartment if employee else "",
            comment=self.comment_edit.text().strip(),
        )


class SchedulePanel(QWidget):
    def __init__(
        self,
        schedule: Schedule,
        rule_engine: RuleEngine,
        location_codes: list[LocationCode],
        repository=None,
        on_change=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._schedule = schedule
        self._rule_engine = rule_engine
        self._location_codes = location_codes
        self._repository = repository
        self._on_change = on_change

        self.model = AssignmentTableModel(schedule)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        # NOT setStretchLastSection(True): with this app's QSS theme, Qt
        # fails to paint the label of a stretched-to-fill last header
        # section (see staff_panel.py for how this was diagnosed). Plain
        # Interactive resize (Qt's default) avoids the bug.
        for column, width in enumerate([140, 90, 90, 90, 140, 140, 200]):
            self.table.horizontalHeader().resizeSection(column, width)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        add_button = QPushButton("Add assignment")
        add_button.setObjectName("primary")
        add_button.clicked.connect(self._add_assignment)

        hint = QLabel(
            "Every add is checked by the active rules (Settings tab). A HARD "
            "violation blocks the add; SOFT violations warn but still save."
        )
        hint.setProperty("role", "hint")
        hint.setWordWrap(True)

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self.table)
        layout.addWidget(hint)

    def showEvent(self, event) -> None:  # noqa: N802
        # Other tabs (Custom view, Day view) write assignments straight into
        # the shared Schedule object; this refresh is what makes them show
        # up here without needing an app restart.
        super().showEvent(event)
        self.model.refresh()

    def _show_context_menu(self, position) -> None:
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        self.table.selectRow(index.row())
        menu = QMenu(self.table)
        delete_action = menu.addAction("Delete assignment")
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is delete_action:
            self._delete_assignment(index.row())

    def _delete_assignment(self, row: int) -> None:
        assignment = self.model.assignment_at(row)
        if assignment is None:
            return
        reply = QMessageBox.question(
            self, "Delete assignment", "Delete this assignment?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self._schedule.remove_assignment(assignment.id)
        if self._repository is not None:
            self._repository.delete_assignment(assignment.id)
        self.model.refresh()
        if self._on_change:
            self._on_change()

    def set_location_codes(self, location_codes: list[LocationCode]) -> None:
        """Called when the Templates tab adds/removes a Location ID, so the
        Add-assignment dialog's resource dropdown stays current without
        needing an app restart."""
        self._location_codes = location_codes

    def _add_assignment(self) -> None:
        if not self._schedule.employees():
            QMessageBox.information(self, "No employees", "Add an employee first (Team page).")
            return

        dialog = AddAssignmentDialog(self._schedule, self._location_codes, self)
        if dialog.exec() != QDialog.Accepted:
            return
        assignment = dialog.assignment()
        if assignment is None or not assignment.resource:
            return

        violations = self._rule_engine.evaluate(assignment, self._schedule)
        hard = [v for v in violations if v.severity == Severity.HARD]
        soft = [v for v in violations if v.severity == Severity.SOFT]

        if hard:
            QMessageBox.critical(self, "Blocked", self._format_violations(hard))
            return

        if soft and not self._confirm_soft_warnings(soft):
            return

        self._schedule.add_assignment(assignment)
        self.model.refresh()
        if self._on_change:
            self._on_change()

    @staticmethod
    def _format_violations(violations: list[RuleViolation]) -> str:
        return "\n".join(f"[{v.rule_id}] {v.message}" for v in violations)

    def _confirm_soft_warnings(self, violations: list[RuleViolation]) -> bool:
        reply = QMessageBox.warning(
            self,
            "Warning",
            self._format_violations(violations) + "\n\nAdd anyway?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes
