"""SQLite persistence (CLAUDE.md: "Storage: local SQLite plus YAML
configuration files"). Plain stdlib `sqlite3` — no ORM dependency, kept
deliberately small since this is Phase 0 foundation, not the final schema.

Cloud sync is out of scope (CLAUDE.md: "later phase, design so it stays
possible, build nothing for it now") — the one thing done here in that
spirit is giving every row a stable `id`/`employee_id` instead of relying on
row position, since a sync/replication layer would need that regardless.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from rostify.core.models import Assignment, Employee, Layer, Transfer
from rostify.core.schedule import Schedule
from rostify.core.templates import (
    CellNote,
    LocationCode,
    PositionOption,
    ShiftId,
    ShiftSegment,
    ShiftTiming,
    SubdepartmentOption,
    Template,
    TemplateAssignment,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    subdepartment TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'Casino',
    position TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS assignments (
    id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(id),
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    resource TEXT NOT NULL,
    layer TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_assignments_employee ON assignments(employee_id);
CREATE INDEX IF NOT EXISTS idx_assignments_start ON assignments(start);

CREATE TABLE IF NOT EXISTS shift_ids (
    id TEXT PRIMARY KEY,
    subdepartment TEXT NOT NULL,
    code TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT 'blue',
    UNIQUE(subdepartment, code)
);

CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    subdepartment TEXT NOT NULL,
    name TEXT NOT NULL,
    subtitle TEXT NOT NULL DEFAULT '',
    color TEXT NOT NULL DEFAULT 'blue',
    UNIQUE(subdepartment, name)
);

CREATE TABLE IF NOT EXISTS shift_timings (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    shift_id TEXT NOT NULL REFERENCES shift_ids(id) ON DELETE CASCADE,
    segments_json TEXT NOT NULL DEFAULT '[]',
    comment TEXT NOT NULL DEFAULT '',
    UNIQUE(template_id, shift_id)
);

CREATE TABLE IF NOT EXISTS location_codes (
    abbreviation TEXT PRIMARY KEY,
    location_code TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    location_group TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS departments (
    name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS subdepartments (
    id TEXT PRIMARY KEY,
    department TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(department, name)
);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    department TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(department, name)
);

-- An employee working in another subdepartment for a period.
CREATE TABLE IF NOT EXISTS transfers (
    id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    subdepartment TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cell_notes (
    employee_id TEXT NOT NULL,
    at TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (employee_id, at)
);

-- Day view: the order of shift rows the user dragged, per subdepartment
-- and day. Keyed by employee: two people can share a Shift ID code.
CREATE TABLE IF NOT EXISTS day_row_order (
    subdepartment TEXT NOT NULL,
    date TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (subdepartment, date, employee_id)
);

-- Custom view: the order of employee rows the user dragged, per
-- subdepartment.
CREATE TABLE IF NOT EXISTS employee_order (
    subdepartment TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (subdepartment, employee_id)
);

CREATE TABLE IF NOT EXISTS template_assignments (
    subdepartment TEXT NOT NULL,
    date TEXT NOT NULL,
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    PRIMARY KEY (subdepartment, date)
);
"""


class Repository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate_positions_to_departments()
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """`CREATE TABLE IF NOT EXISTS` only helps brand-new databases — an
        existing `data/rostify.db` from before a column was added needs an
        explicit `ALTER TABLE`, or every query touching that column breaks.
        """
        self._ensure_column("templates", "color", "TEXT NOT NULL DEFAULT 'blue'")
        self._ensure_column("shift_ids", "color", "TEXT NOT NULL DEFAULT 'blue'")
        self._ensure_column("employees", "unavailable_from", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("employees", "unavailable_to", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("assignments", "subdepartment", "TEXT NOT NULL DEFAULT ''")
        # Replaced by day_row_order (keyed by employee, not shift code).
        self._conn.execute("DROP TABLE IF EXISTS day_shift_order")

    def _migrate_positions_to_departments(self) -> None:
        """Positions used to be one flat list keyed by name. Now each one
        belongs to a department. An old table is rebuilt in the new shape
        and every old position goes to the first department, so nothing the
        user entered is lost. Runs before SCHEMA, because SCHEMA's
        `CREATE TABLE IF NOT EXISTS` would leave the old table as it is."""
        columns = {row[1] for row in self._conn.execute("PRAGMA table_info(positions)")}
        if not columns or "department" in columns:
            return  # brand-new database, or already migrated
        has_departments = {row[1] for row in self._conn.execute("PRAGMA table_info(departments)")}
        department_row = (
            self._conn.execute("SELECT name FROM departments ORDER BY name LIMIT 1").fetchone()
            if has_departments
            else None
        )
        department = department_row[0] if department_row else ""
        names = [r[0] for r in self._conn.execute("SELECT name FROM positions ORDER BY name")]
        self._conn.execute("DROP TABLE positions")
        self._conn.executescript(SCHEMA)
        for name in names:
            option = PositionOption(department=department, name=name)
            self._conn.execute(
                "INSERT INTO positions (id, department, name) VALUES (?, ?, ?)",
                (option.id, option.department, option.name),
            )
        self._conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        existing = {row[1] for row in self._conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def close(self) -> None:
        self._conn.close()

    # --- employees ---------------------------------------------------

    _EMPLOYEE_UPSERT = """
        INSERT INTO employees
            (id, first_name, last_name, subdepartment, department, position, email, password_hash, active,
             unavailable_from, unavailable_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            first_name=excluded.first_name, last_name=excluded.last_name,
            subdepartment=excluded.subdepartment, department=excluded.department,
            position=excluded.position, email=excluded.email,
            password_hash=excluded.password_hash, active=excluded.active,
            unavailable_from=excluded.unavailable_from, unavailable_to=excluded.unavailable_to
    """

    @staticmethod
    def _employee_row(employee: Employee) -> tuple:
        return (
            employee.id,
            employee.first_name,
            employee.last_name,
            employee.subdepartment,
            employee.department,
            employee.position,
            employee.email,
            employee.password_hash,
            int(employee.active),
            employee.unavailable_from.isoformat() if employee.unavailable_from else "",
            employee.unavailable_to.isoformat() if employee.unavailable_to else "",
        )

    def save_employee(self, employee: Employee) -> None:
        self._conn.execute(self._EMPLOYEE_UPSERT, self._employee_row(employee))
        self._conn.commit()

    def load_employees(self) -> list[Employee]:
        rows = self._conn.execute(
            "SELECT id, first_name, last_name, subdepartment, department, position, email, password_hash, active, "
            "unavailable_from, unavailable_to FROM employees"
        ).fetchall()
        return [
            Employee(
                id=r[0],
                first_name=r[1],
                last_name=r[2],
                subdepartment=r[3],
                department=r[4],
                position=r[5],
                email=r[6],
                password_hash=r[7],
                active=bool(r[8]),
                unavailable_from=date.fromisoformat(r[9]) if r[9] else None,
                unavailable_to=date.fromisoformat(r[10]) if r[10] else None,
            )
            for r in rows
        ]

    def delete_employee(self, employee_id: str) -> None:
        self._conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        self._conn.commit()

    # --- assignments ---------------------------------------------------

    _ASSIGNMENT_UPSERT = """
        INSERT INTO assignments (id, employee_id, start, end, resource, layer, department, comment, subdepartment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            employee_id=excluded.employee_id, start=excluded.start, end=excluded.end,
            resource=excluded.resource, layer=excluded.layer,
            department=excluded.department, comment=excluded.comment,
            subdepartment=excluded.subdepartment
    """

    @staticmethod
    def _assignment_row(assignment: Assignment) -> tuple:
        return (
            assignment.id,
            assignment.employee_id,
            assignment.start.isoformat(),
            assignment.end.isoformat(),
            assignment.resource,
            assignment.layer.value,
            assignment.department,
            assignment.comment,
            assignment.subdepartment,
        )

    def save_assignment(self, assignment: Assignment) -> None:
        self._conn.execute(self._ASSIGNMENT_UPSERT, self._assignment_row(assignment))
        self._conn.commit()

    def load_assignments(self) -> list[Assignment]:
        rows = self._conn.execute(
            "SELECT id, employee_id, start, end, resource, layer, department, comment, subdepartment FROM assignments"
        ).fetchall()
        return [
            Assignment(
                id=r[0],
                employee_id=r[1],
                start=datetime.fromisoformat(r[2]),
                end=datetime.fromisoformat(r[3]),
                resource=r[4],
                layer=Layer(r[5]),
                department=r[6],
                comment=r[7],
                subdepartment=r[8],
            )
            for r in rows
        ]

    def delete_assignment(self, assignment_id: str) -> None:
        self._conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
        self._conn.commit()

    # --- shift ids ---------------------------------------------------

    def save_shift_id(self, shift_id: ShiftId) -> None:
        self._conn.execute(
            """
            INSERT INTO shift_ids (id, subdepartment, code, color) VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                subdepartment=excluded.subdepartment, code=excluded.code, color=excluded.color
            """,
            (shift_id.id, shift_id.subdepartment, shift_id.code, shift_id.color),
        )
        self._conn.commit()

    def load_shift_ids(self, subdepartment: str) -> list[ShiftId]:
        rows = self._conn.execute(
            "SELECT id, subdepartment, code, color FROM shift_ids WHERE subdepartment = ? ORDER BY code",
            (subdepartment,),
        ).fetchall()
        return [ShiftId(id=r[0], subdepartment=r[1], code=r[2], color=r[3]) for r in rows]

    def delete_shift_id(self, shift_id: str) -> None:
        self._conn.execute("DELETE FROM shift_ids WHERE id = ?", (shift_id,))
        self._conn.commit()

    # --- templates ---------------------------------------------------

    def save_template(self, template: Template) -> None:
        self._conn.execute(
            """
            INSERT INTO templates (id, subdepartment, name, subtitle, color) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                subdepartment=excluded.subdepartment, name=excluded.name, subtitle=excluded.subtitle,
                color=excluded.color
            """,
            (template.id, template.subdepartment, template.name, template.subtitle, template.color),
        )
        self._conn.commit()

    def load_templates(self, subdepartment: str) -> list[Template]:
        rows = self._conn.execute(
            "SELECT id, subdepartment, name, subtitle, color FROM templates WHERE subdepartment = ? ORDER BY name",
            (subdepartment,),
        ).fetchall()
        return [Template(id=r[0], subdepartment=r[1], name=r[2], subtitle=r[3], color=r[4]) for r in rows]

    def delete_template(self, template_id: str) -> None:
        self._conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self._conn.commit()

    # --- shift timings ---------------------------------------------------

    def save_shift_timing(self, timing: ShiftTiming) -> None:
        segments_json = json.dumps(
            [{"start_minutes": s.start_minutes, "end_minutes": s.end_minutes} for s in timing.segments]
        )
        self._conn.execute(
            """
            INSERT INTO shift_timings (id, template_id, shift_id, segments_json, comment)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                template_id=excluded.template_id, shift_id=excluded.shift_id,
                segments_json=excluded.segments_json, comment=excluded.comment
            """,
            (timing.id, timing.template_id, timing.shift_id, segments_json, timing.comment),
        )
        self._conn.commit()

    def load_shift_timings(self, template_id: str) -> list[ShiftTiming]:
        rows = self._conn.execute(
            "SELECT id, template_id, shift_id, segments_json, comment FROM shift_timings WHERE template_id = ?",
            (template_id,),
        ).fetchall()
        return [
            ShiftTiming(
                id=r[0],
                template_id=r[1],
                shift_id=r[2],
                segments=[ShiftSegment(**seg) for seg in json.loads(r[3])],
                comment=r[4],
            )
            for r in rows
        ]

    def delete_shift_timing(self, timing_id: str) -> None:
        self._conn.execute("DELETE FROM shift_timings WHERE id = ?", (timing_id,))
        self._conn.commit()

    # --- location codes ---------------------------------------------------

    def save_location_code(self, location_code: LocationCode) -> None:
        self._conn.execute(
            """
            INSERT INTO location_codes (abbreviation, location_code, description, location_group)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(abbreviation) DO UPDATE SET
                location_code=excluded.location_code, description=excluded.description,
                location_group=excluded.location_group
            """,
            (location_code.abbreviation, location_code.location_code, location_code.description, location_code.group),
        )
        self._conn.commit()

    def load_location_codes(self) -> list[LocationCode]:
        rows = self._conn.execute(
            "SELECT abbreviation, location_code, description, location_group FROM location_codes ORDER BY abbreviation"
        ).fetchall()
        return [LocationCode(abbreviation=r[0], location_code=r[1], description=r[2], group=r[3]) for r in rows]

    def delete_location_code(self, abbreviation: str) -> None:
        self._conn.execute("DELETE FROM location_codes WHERE abbreviation = ?", (abbreviation,))
        self._conn.commit()

    # --- departments / subdepartments / positions (List Control) ---------

    def save_department(self, name: str) -> None:
        self._conn.execute("INSERT OR IGNORE INTO departments (name) VALUES (?)", (name,))
        self._conn.commit()

    def rename_department(self, old_name: str, new_name: str) -> None:
        """Renames the department and moves its subdepartments and
        positions along with it, so they are not left orphaned."""
        self._conn.execute("UPDATE departments SET name = ? WHERE name = ?", (new_name, old_name))
        self._conn.execute("UPDATE subdepartments SET department = ? WHERE department = ?", (new_name, old_name))
        self._conn.execute("UPDATE positions SET department = ? WHERE department = ?", (new_name, old_name))
        self._conn.commit()

    def load_departments(self) -> list[str]:
        rows = self._conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def delete_department(self, name: str) -> None:
        self._conn.execute("DELETE FROM departments WHERE name = ?", (name,))
        self._conn.commit()

    def save_subdepartment(self, option: SubdepartmentOption) -> None:
        self._conn.execute(
            """
            INSERT INTO subdepartments (id, department, name) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET department=excluded.department, name=excluded.name
            """,
            (option.id, option.department, option.name),
        )
        self._conn.commit()

    def load_subdepartments(self, department: str | None = None) -> list[SubdepartmentOption]:
        if department is None:
            rows = self._conn.execute("SELECT id, department, name FROM subdepartments ORDER BY name").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, department, name FROM subdepartments WHERE department = ? ORDER BY name",
                (department,),
            ).fetchall()
        return [SubdepartmentOption(id=r[0], department=r[1], name=r[2]) for r in rows]

    def delete_subdepartment(self, subdepartment_id: str) -> None:
        self._conn.execute("DELETE FROM subdepartments WHERE id = ?", (subdepartment_id,))
        self._conn.commit()

    def save_position(self, option: PositionOption) -> None:
        self._conn.execute(
            """
            INSERT INTO positions (id, department, name) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET department=excluded.department, name=excluded.name
            """,
            (option.id, option.department, option.name),
        )
        self._conn.commit()

    def load_positions(self, department: str | None = None) -> list[PositionOption]:
        if department is None:
            rows = self._conn.execute(
                "SELECT id, department, name FROM positions ORDER BY department, name"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, department, name FROM positions WHERE department = ? ORDER BY name",
                (department,),
            ).fetchall()
        return [PositionOption(id=r[0], department=r[1], name=r[2]) for r in rows]

    def delete_position(self, position_id: str) -> None:
        self._conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        self._conn.commit()

    # --- template assignments (Custom view's "one Template per --------
    # subdepartment per day") -------------------------------------------

    def save_template_assignment(self, template_assignment: TemplateAssignment) -> None:
        self._conn.execute(
            """
            INSERT INTO template_assignments (subdepartment, date, template_id) VALUES (?, ?, ?)
            ON CONFLICT(subdepartment, date) DO UPDATE SET template_id=excluded.template_id
            """,
            (template_assignment.subdepartment, template_assignment.date.isoformat(), template_assignment.template_id),
        )
        self._conn.commit()

    def load_template_assignment(self, subdepartment: str, on: date) -> TemplateAssignment | None:
        row = self._conn.execute(
            "SELECT subdepartment, date, template_id FROM template_assignments WHERE subdepartment = ? AND date = ?",
            (subdepartment, on.isoformat()),
        ).fetchone()
        if row is None:
            return None
        return TemplateAssignment(subdepartment=row[0], date=date.fromisoformat(row[1]), template_id=row[2])

    def load_template_assignments_range(
        self, subdepartment: str, start: date, end: date
    ) -> list[TemplateAssignment]:
        rows = self._conn.execute(
            "SELECT subdepartment, date, template_id FROM template_assignments "
            "WHERE subdepartment = ? AND date BETWEEN ? AND ? ORDER BY date",
            (subdepartment, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [TemplateAssignment(subdepartment=r[0], date=date.fromisoformat(r[1]), template_id=r[2]) for r in rows]

    def delete_template_assignment(self, subdepartment: str, on: date) -> None:
        self._conn.execute(
            "DELETE FROM template_assignments WHERE subdepartment = ? AND date = ?",
            (subdepartment, on.isoformat()),
        )
        self._conn.commit()

    # --- convenience ---------------------------------------------------

    def load_schedule(self) -> Schedule:
        schedule = Schedule()
        for employee in self.load_employees():
            schedule.add_employee(employee)
        for assignment in self.load_assignments():
            schedule.add_assignment(assignment)
        return schedule

    def save_schedule(self, schedule: Schedule) -> None:
        """Everything in one transaction. Committing row by row made every
        edit in the app wait on thousands of separate disk writes."""
        self._conn.executemany(
            self._EMPLOYEE_UPSERT, [self._employee_row(e) for e in schedule.employees(active_only=False)]
        )
        self._conn.executemany(self._ASSIGNMENT_UPSERT, [self._assignment_row(a) for a in schedule.assignments()])
        self._conn.commit()

    # --- transfers -----------------------------------------------------------

    def save_transfer(self, transfer: Transfer) -> None:
        self._conn.execute(
            "INSERT INTO transfers (id, employee_id, subdepartment, start, end) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET employee_id=excluded.employee_id, "
            "subdepartment=excluded.subdepartment, start=excluded.start, end=excluded.end",
            (transfer.id, transfer.employee_id, transfer.subdepartment, transfer.start.isoformat(), transfer.end.isoformat()),
        )
        self._conn.commit()

    def load_transfers(self) -> list[Transfer]:
        rows = self._conn.execute("SELECT id, employee_id, subdepartment, start, end FROM transfers").fetchall()
        return [
            Transfer(id=r[0], employee_id=r[1], subdepartment=r[2], start=date.fromisoformat(r[3]), end=date.fromisoformat(r[4]))
            for r in rows
        ]

    def delete_transfer(self, transfer_id: str) -> None:
        self._conn.execute("DELETE FROM transfers WHERE id = ?", (transfer_id,))
        self._conn.commit()

    # --- cell notes (Day view) -------------------------------------------

    def save_cell_note(self, note: CellNote) -> None:
        self._conn.execute(
            "INSERT INTO cell_notes (employee_id, at, text) VALUES (?, ?, ?) "
            "ON CONFLICT(employee_id, at) DO UPDATE SET text=excluded.text",
            (note.employee_id, note.at.isoformat(), note.text),
        )
        self._conn.commit()

    def delete_cell_note(self, employee_id: str, at: datetime) -> None:
        self._conn.execute("DELETE FROM cell_notes WHERE employee_id = ? AND at = ?", (employee_id, at.isoformat()))
        self._conn.commit()

    def load_cell_notes(self, start: datetime, end: datetime) -> list[CellNote]:
        rows = self._conn.execute(
            "SELECT employee_id, at, text FROM cell_notes WHERE at >= ? AND at < ? ORDER BY at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [CellNote(employee_id=r[0], at=datetime.fromisoformat(r[1]), text=r[2]) for r in rows]

    # --- row orders ------------------------------------------------------

    def save_day_row_order(self, subdepartment: str, on: date, employee_ids: list[str]) -> None:
        self._conn.execute(
            "DELETE FROM day_row_order WHERE subdepartment = ? AND date = ?", (subdepartment, on.isoformat())
        )
        self._conn.executemany(
            "INSERT INTO day_row_order (subdepartment, date, employee_id, position) VALUES (?, ?, ?, ?)",
            [(subdepartment, on.isoformat(), employee_id, index) for index, employee_id in enumerate(employee_ids)],
        )
        self._conn.commit()

    def load_day_row_order(self, subdepartment: str, on: date) -> list[str]:
        rows = self._conn.execute(
            "SELECT employee_id FROM day_row_order WHERE subdepartment = ? AND date = ? ORDER BY position",
            (subdepartment, on.isoformat()),
        ).fetchall()
        return [r[0] for r in rows]

    def save_employee_order(self, subdepartment: str, employee_ids: list[str]) -> None:
        self._conn.execute("DELETE FROM employee_order WHERE subdepartment = ?", (subdepartment,))
        self._conn.executemany(
            "INSERT INTO employee_order (subdepartment, employee_id, position) VALUES (?, ?, ?)",
            [(subdepartment, employee_id, index) for index, employee_id in enumerate(employee_ids)],
        )
        self._conn.commit()

    def load_employee_order(self, subdepartment: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT employee_id FROM employee_order WHERE subdepartment = ? ORDER BY position", (subdepartment,)
        ).fetchall()
        return [r[0] for r in rows]

    def load_template_days(self, template_id: str) -> list[TemplateAssignment]:
        """Every (subdepartment, day) that uses this template."""
        rows = self._conn.execute(
            "SELECT subdepartment, date, template_id FROM template_assignments WHERE template_id = ?", (template_id,)
        ).fetchall()
        return [TemplateAssignment(subdepartment=r[0], date=date.fromisoformat(r[1]), template_id=r[2]) for r in rows]
