"""Settings -> List Control: admin-managed Department/Subdepartment/Position
lists. Staff's Add/Edit-employee dialog and the Templates tab's Department/
Subdepartment selectors read from these — dropdown-only entry there, no
free text — so this is where the actual allowed values live.

Templates, Shift IDs and Location IDs keep managing their own lists where
they already live (Templates tab) — no duplication here.
"""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QMessageBox, QVBoxLayout, QWidget

from rostify.core.templates import SubdepartmentOption
from rostify.services.persistence import Repository

from .widgets import IconTableEditor, SimpleFormDialog


class ListControlPanel(QWidget):
    def __init__(self, repository: Repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repository = repository
        self._departments: list[str] = []
        self._subdepartments: list[SubdepartmentOption] = []
        self._positions: list[str] = []

        self.department_editor = IconTableEditor(
            ["Department"], self._add_department, self._edit_department, self._delete_department
        )
        self.subdepartment_editor = IconTableEditor(
            ["Department", "Subdepartment"],
            self._add_subdepartment,
            self._edit_subdepartment,
            self._delete_subdepartment,
        )
        self.position_editor = IconTableEditor(
            ["Position"], self._add_position, self._edit_position, self._delete_position
        )

        layout = QVBoxLayout(self)
        for title, editor in (
            ("Departments", self.department_editor),
            ("Subdepartments", self.subdepartment_editor),
            ("Positions", self.position_editor),
        ):
            box = QGroupBox(title)
            box_layout = QVBoxLayout()
            box_layout.addWidget(editor)
            box.setLayout(box_layout)
            layout.addWidget(box)

        self.reload()

    def reload(self) -> None:
        self._departments = self._repository.load_departments()
        self._subdepartments = self._repository.load_subdepartments()
        self._positions = self._repository.load_positions()
        self.department_editor.set_rows([(d,) for d in self._departments])
        self.subdepartment_editor.set_rows([(s.department, s.name) for s in self._subdepartments])
        self.position_editor.set_rows([(p,) for p in self._positions])

    # --- departments -----------------------------------------------------

    def _add_department(self) -> None:
        dialog = SimpleFormDialog("Add department", [("Name", None)], parent=self)
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        (name,) = dialog.values()
        if name:
            self._repository.save_department(name)
            self.reload()

    def _edit_department(self, row: int) -> None:
        current = self._departments[row]
        dialog = SimpleFormDialog("Edit department", [("Name", None)], initial=[current], parent=self)
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        (new_name,) = dialog.values()
        if new_name and new_name != current:
            self._repository.rename_department(current, new_name)
            self.reload()

    def _delete_department(self, row: int) -> None:
        name = self._departments[row]
        if self._confirm(f"Delete department '{name}'?"):
            self._repository.delete_department(name)
            self.reload()

    # --- subdepartments ----------------------------------------------------

    def _add_subdepartment(self) -> None:
        dialog = SimpleFormDialog(
            "Add subdepartment", [("Department", self._departments), ("Name", None)], parent=self
        )
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        department, name = dialog.values()
        if department and name:
            self._repository.save_subdepartment(SubdepartmentOption(department=department, name=name))
            self.reload()

    def _edit_subdepartment(self, row: int) -> None:
        existing = self._subdepartments[row]
        dialog = SimpleFormDialog(
            "Edit subdepartment",
            [("Department", self._departments), ("Name", None)],
            initial=[existing.department, existing.name],
            parent=self,
        )
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        department, name = dialog.values()
        if department and name:
            self._repository.save_subdepartment(
                SubdepartmentOption(id=existing.id, department=department, name=name)
            )
            self.reload()

    def _delete_subdepartment(self, row: int) -> None:
        existing = self._subdepartments[row]
        if self._confirm(f"Delete subdepartment '{existing.name}'?"):
            self._repository.delete_subdepartment(existing.id)
            self.reload()

    # --- positions ---------------------------------------------------------

    def _add_position(self) -> None:
        dialog = SimpleFormDialog("Add position", [("Name", None)], parent=self)
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        (name,) = dialog.values()
        if name:
            self._repository.save_position(name)
            self.reload()

    def _edit_position(self, row: int) -> None:
        current = self._positions[row]
        dialog = SimpleFormDialog("Edit position", [("Name", None)], initial=[current], parent=self)
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        (new_name,) = dialog.values()
        if new_name and new_name != current:
            self._repository.rename_position(current, new_name)
            self.reload()

    def _delete_position(self, row: int) -> None:
        name = self._positions[row]
        if self._confirm(f"Delete position '{name}'?"):
            self._repository.delete_position(name)
            self.reload()

    # --- shared -------------------------------------------------------------

    def _confirm(self, message: str) -> bool:
        reply = QMessageBox.question(self, "Confirm", message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes
