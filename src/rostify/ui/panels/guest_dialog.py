""""+ Add employee" on the Custom view: bring someone from another
subdepartment of the department into this one — for a period (a Transfer:
they are here on those days and gone from their own list), or for good
(their subdepartment changes). E.g. a "Supervisor 1" who mostly works the
dealers' schedule.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from rostify.core.models import Employee
from rostify.core.schedule import Schedule
from rostify.services.roster import future_shifts, shifts_in_period


def _qdate(day: date) -> QDate:
    return QDate(day.year, day.month, day.day)


def _date(qd: QDate) -> date:
    return date(qd.year(), qd.month(), qd.day())


class TransferDialog(QDialog):
    def __init__(
        self,
        schedule: Schedule,
        target: str,
        candidates: list[Employee],
        start: date,
        end: date,
        parent: QWidget | None = None,
    ) -> None:
        """`target`: the subdepartment on screen. `candidates`: employees of
        the department's other subdepartments."""
        super().__init__(parent)
        self.setWindowTitle(f"Add employee to {target}")
        self._schedule = schedule
        self._all = sorted(candidates, key=lambda e: (e.subdepartment, e.last_name, e.first_name))
        self._candidates: list[Employee] = []

        self.source_combo = QComboBox()
        self.source_combo.setToolTip("Which subdepartment to take the employee from")
        self.source_combo.addItem("All")
        self.source_combo.addItems(sorted({e.subdepartment for e in self._all}))
        self.employee_combo = QComboBox()
        self.employee_combo.setToolTip("The employee to bring over — their position does not change")
        self.source_combo.currentTextChanged.connect(lambda _: self._fill_employees())

        self.period_radio = QRadioButton("For a period")
        self.period_radio.setToolTip(f"Works in {target} on these days only, then goes back automatically")
        self.move_radio = QRadioButton(f"Move to {target} permanently")
        self.move_radio.setToolTip("Changes the employee's subdepartment")
        group = QButtonGroup(self)
        group.addButton(self.period_radio)
        group.addButton(self.move_radio)
        self.period_radio.setChecked(True)

        self.from_edit = QDateEdit(_qdate(start))
        self.from_edit.setCalendarPopup(True)
        self.to_edit = QDateEdit(_qdate(end))
        self.to_edit.setCalendarPopup(True)
        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("From"))
        period_row.addWidget(self.from_edit)
        period_row.addWidget(QLabel("To"))
        period_row.addWidget(self.to_edit)
        period_row.addStretch(1)

        self._warning = QLabel("")
        self._warning.setProperty("role", "hint")
        self._warning.setWordWrap(True)

        for signal in (
            self.employee_combo.currentIndexChanged,
            self.from_edit.dateChanged,
            self.to_edit.dateChanged,
            self.period_radio.toggled,
        ):
            signal.connect(lambda *_: self._refresh())

        form = QFormLayout()
        form.addRow("Move from", self.source_combo)
        form.addRow("Employee", self.employee_combo)
        form.addRow("", self.period_radio)
        form.addRow("", period_row)
        form.addRow("", self.move_radio)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._warning)
        layout.addWidget(self._buttons)
        self._fill_employees()

    def _fill_employees(self) -> None:
        source = self.source_combo.currentText()
        self._candidates = [e for e in self._all if source == "All" or e.subdepartment == source]
        self.employee_combo.blockSignals(True)
        self.employee_combo.clear()
        for employee in self._candidates:
            position = f" · {employee.position}" if employee.position else ""
            label = f"{employee.last_name}, {employee.first_name}{position} ({employee.id})"
            if source == "All":
                label += f" — {employee.subdepartment}"
            self.employee_combo.addItem(label)
        self.employee_combo.blockSignals(False)
        self._refresh()

    def _refresh(self) -> None:
        for edit in (self.from_edit, self.to_edit):
            edit.setEnabled(self.period_radio.isChecked())
        employee = self.employee()
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(employee is not None)
        text = ""
        if employee is not None and self.period_radio.isChecked():
            start, end = self.period()
            count = len(shifts_in_period(self._schedule, employee.id, start, end))
            if count:
                text = (
                    f"{employee.full_name} has {count} shift(s) on the {employee.subdepartment} schedule in this "
                    f"period. They will be removed — assign new ones here after the move."
                )
        elif employee is not None:
            count = len(future_shifts(self._schedule, employee, date.today()))
            if count:
                text = (
                    f"{employee.full_name} has {count} shift(s) on the {employee.subdepartment} schedule from today "
                    f"on. They will be removed; earlier shifts stay as history."
                )
        self._warning.setText(text)

    def employee(self) -> Employee | None:
        index = self.employee_combo.currentIndex()
        return self._candidates[index] if 0 <= index < len(self._candidates) else None

    def permanent(self) -> bool:
        return self.move_radio.isChecked()

    def period(self) -> tuple[date, date]:
        start, end = _date(self.from_edit.date()), _date(self.to_edit.date())
        return (start, end) if start <= end else (end, start)
