"""Settings -> Lists: the admin-managed lists everything else picks from.

* Departments, Subdepartments and Positions — Staff's Add/Edit-employee
  dialog and the Templates tab's selectors read from these (dropdown-only
  entry there, no free text), so this is where the allowed values live.
  A Subdepartment and a Position each belong to one Department.
* Location codes — the short codes (B1, RW2, BR…) a supervisor puts in the
  Day view's rotation grid. Typed straight into the table: double-click a
  cell to change it, or type a new code into the blank row at the bottom.
  The icon buttons and right-click menu still open the full form.

Templates and Shift IDs keep their own screen (Templates tab).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from rostify.core.templates import LocationCode, PositionOption, SubdepartmentOption
from rostify.services.persistence import Repository

from .widgets import IconTableEditor, SettingsCard, SimpleFormDialog

_LOCATION_FIELDS = [("Abbreviation", None), ("Location Code", None), ("Description", None), ("Group", None)]


class ListControlPanel(QWidget):
    def __init__(
        self,
        repository: Repository,
        on_location_codes_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._on_location_codes_change = on_location_codes_change
        self._departments: list[str] = []
        self._subdepartments: list[SubdepartmentOption] = []
        self._positions: list[PositionOption] = []
        self._location_codes: list[LocationCode] = []

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
            ["Department", "Position"], self._add_position, self._edit_position, self._delete_position
        )
        self.location_editor = IconTableEditor(
            ["Abbreviation", "Location Code", "Location Description", "Location Group"],
            self._add_location,
            self._edit_location,
            self._delete_location,
            on_cell_edited=self._on_location_cell_edited,
            new_row_hint="Type a new code…",
        )
        self.location_editor.table.setMinimumHeight(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for title, hint, editor in (
            ("Departments", "Top-level org units. Right-click a row to edit or delete it.", self.department_editor),
            ("Subdepartments", "Employee groups inside a department. Templates and shifts belong to one.", self.subdepartment_editor),
            (
                "Positions",
                "Job titles, each inside one department. The employee form only offers the positions "
                "of the employee's department.",
                self.position_editor,
            ),
            (
                "Location codes",
                "Short codes (B1, RW2, BR…) a supervisor puts in the Day view's rotation grid. "
                "Double-click a cell to change it, or type a new code into the empty row at the bottom.",
                self.location_editor,
            ),
        ):
            card = SettingsCard(title, hint)
            editor.setProperty("transparentBg", True)
            card.body.addWidget(editor)
            layout.addWidget(card)

        self.reload()

    def reload(self) -> None:
        self._departments = self._repository.load_departments()
        self._subdepartments = self._repository.load_subdepartments()
        self._positions = self._repository.load_positions()
        self._location_codes = self._repository.load_location_codes()
        self.department_editor.set_rows([(d,) for d in self._departments])
        self.subdepartment_editor.set_rows([(s.department, s.name) for s in self._subdepartments])
        self.position_editor.set_rows([(p.department, p.name) for p in self._positions])
        self.location_editor.set_rows(
            [(lc.abbreviation, lc.location_code, lc.description, lc.group) for lc in self._location_codes]
        )

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
        dialog = SimpleFormDialog("Add position", [("Department", self._departments), ("Name", None)], parent=self)
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        department, name = dialog.values()
        if not (department and name):
            return
        if self._position_exists(department, name):
            QMessageBox.warning(self, "Duplicate position", f"'{name}' already exists in {department}.")
            return
        self._repository.save_position(PositionOption(department=department, name=name))
        self.reload()

    def _edit_position(self, row: int) -> None:
        existing = self._positions[row]
        dialog = SimpleFormDialog(
            "Edit position",
            [("Department", self._departments), ("Name", None)],
            initial=[existing.department, existing.name],
            parent=self,
        )
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        department, name = dialog.values()
        if not (department and name):
            return
        if (department, name) != (existing.department, existing.name) and self._position_exists(department, name):
            QMessageBox.warning(self, "Duplicate position", f"'{name}' already exists in {department}.")
            return
        self._repository.save_position(PositionOption(id=existing.id, department=department, name=name))
        self.reload()

    def _delete_position(self, row: int) -> None:
        existing = self._positions[row]
        if self._confirm(f"Delete position '{existing.name}' ({existing.department})?"):
            self._repository.delete_position(existing.id)
            self.reload()

    def _position_exists(self, department: str, name: str) -> bool:
        return any(p.department == department and p.name == name for p in self._positions)

    # --- location codes ----------------------------------------------------

    def _add_location(self) -> None:
        dialog = SimpleFormDialog("Add location code", _LOCATION_FIELDS, parent=self)
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        abbreviation, location_code, description, group = dialog.values()
        self._save_location(None, LocationCode(abbreviation, location_code, description, group))

    def _edit_location(self, row: int) -> None:
        existing = self._location_codes[row]
        dialog = SimpleFormDialog(
            "Edit location code",
            _LOCATION_FIELDS,
            initial=[existing.abbreviation, existing.location_code, existing.description, existing.group],
            parent=self,
        )
        if dialog.exec() != SimpleFormDialog.Accepted:
            return
        abbreviation, location_code, description, group = dialog.values()
        self._save_location(existing, LocationCode(abbreviation, location_code, description, group))

    def _on_location_cell_edited(self, row: int, column: int, text: str) -> None:
        """A value typed straight into the table. `row` past the last code
        is the blank new row at the bottom."""
        if row >= len(self._location_codes):
            if column == 0 and text:
                self._save_location(None, LocationCode(abbreviation=text))
            else:
                self.reload()
            return
        existing = self._location_codes[row]
        values = [existing.abbreviation, existing.location_code, existing.description, existing.group]
        values[column] = text
        self._save_location(existing, LocationCode(*values))

    def _save_location(self, existing: LocationCode | None, updated: LocationCode) -> None:
        """One save path for the form and for in-table typing. The
        abbreviation is the key, so renaming it replaces the old row."""
        if not updated.abbreviation:
            QMessageBox.warning(self, "Abbreviation needed", "A location code needs an abbreviation.")
            self.reload()
            return
        renamed = existing is None or updated.abbreviation != existing.abbreviation
        if renamed and any(lc.abbreviation == updated.abbreviation for lc in self._location_codes):
            QMessageBox.warning(self, "Duplicate abbreviation", f"'{updated.abbreviation}' already exists.")
            self.reload()
            return
        if existing is not None and renamed:
            self._repository.delete_location_code(existing.abbreviation)
        self._repository.save_location_code(updated)
        self._location_codes_changed()

    def _delete_location(self, row: int) -> None:
        existing = self._location_codes[row]
        if self._confirm(f"Delete location code '{existing.abbreviation}'?"):
            self._repository.delete_location_code(existing.abbreviation)
            self._location_codes_changed()

    def _location_codes_changed(self) -> None:
        self.reload()
        if self._on_location_codes_change:
            self._on_location_codes_change()

    # --- shared -------------------------------------------------------------

    def _confirm(self, message: str) -> bool:
        reply = QMessageBox.question(self, "Confirm", message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes
