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

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.core.templates import (
    LocationCode,
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
    name TEXT PRIMARY KEY
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

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        existing = {row[1] for row in self._conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def close(self) -> None:
        self._conn.close()

    # --- employees ---------------------------------------------------

    def save_employee(self, employee: Employee) -> None:
        self._conn.execute(
            """
            INSERT INTO employees
                (id, first_name, last_name, subdepartment, department, position, email, password_hash, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                first_name=excluded.first_name, last_name=excluded.last_name,
                subdepartment=excluded.subdepartment, department=excluded.department,
                position=excluded.position, email=excluded.email,
                password_hash=excluded.password_hash, active=excluded.active
            """,
            (
                employee.id,
                employee.first_name,
                employee.last_name,
                employee.subdepartment,
                employee.department,
                employee.position,
                employee.email,
                employee.password_hash,
                int(employee.active),
            ),
        )
        self._conn.commit()

    def load_employees(self) -> list[Employee]:
        rows = self._conn.execute(
            "SELECT id, first_name, last_name, subdepartment, department, position, email, password_hash, active "
            "FROM employees"
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
            )
            for r in rows
        ]

    def delete_employee(self, employee_id: str) -> None:
        self._conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        self._conn.commit()

    # --- assignments ---------------------------------------------------

    def save_assignment(self, assignment: Assignment) -> None:
        self._conn.execute(
            """
            INSERT INTO assignments (id, employee_id, start, end, resource, layer, department, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                employee_id=excluded.employee_id, start=excluded.start, end=excluded.end,
                resource=excluded.resource, layer=excluded.layer,
                department=excluded.department, comment=excluded.comment
            """,
            (
                assignment.id,
                assignment.employee_id,
                assignment.start.isoformat(),
                assignment.end.isoformat(),
                assignment.resource,
                assignment.layer.value,
                assignment.department,
                assignment.comment,
            ),
        )
        self._conn.commit()

    def load_assignments(self) -> list[Assignment]:
        rows = self._conn.execute(
            "SELECT id, employee_id, start, end, resource, layer, department, comment FROM assignments"
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
        self._conn.execute("UPDATE departments SET name = ? WHERE name = ?", (new_name, old_name))
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

    def save_position(self, name: str) -> None:
        self._conn.execute("INSERT OR IGNORE INTO positions (name) VALUES (?)", (name,))
        self._conn.commit()

    def rename_position(self, old_name: str, new_name: str) -> None:
        self._conn.execute("UPDATE positions SET name = ? WHERE name = ?", (new_name, old_name))
        self._conn.commit()

    def load_positions(self) -> list[str]:
        rows = self._conn.execute("SELECT name FROM positions ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def delete_position(self, name: str) -> None:
        self._conn.execute("DELETE FROM positions WHERE name = ?", (name,))
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
        for employee in schedule.employees(active_only=False):
            self.save_employee(employee)
        for assignment in schedule.assignments():
            self.save_assignment(assignment)
