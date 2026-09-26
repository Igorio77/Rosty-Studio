"""Roster CSV export.

Deliberately generic (employee/department/layer/resource/time/comment)
rather than a port of the xlsb's Dealer_Output columns (BRAND, SHIP,
VOYAGE_NO, FL_ID, CTS_ID, ...) — those are voyage/operator-specific metadata
that belongs in a later, purpose-built export once a real customer needs
that exact shape, not baked into the generic core export path.
"""

from __future__ import annotations

import csv
from pathlib import Path

from rostify.core.schedule import Schedule

FIELDNAMES = [
    "employee_id",
    "employee_name",
    "department",
    "layer",
    "resource",
    "start",
    "end",
    "comment",
]


def export_schedule_csv(schedule: Schedule, path: str | Path) -> int:
    """Write every assignment in `schedule` to a CSV file at `path`.
    Returns the number of rows written.
    """
    path = Path(path)
    rows = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for assignment in schedule.assignments():
            employee = schedule.get_employee(assignment.employee_id)
            writer.writerow(
                {
                    "employee_id": assignment.employee_id,
                    "employee_name": employee.full_name if employee else "",
                    "department": assignment.department,
                    "layer": assignment.layer.value,
                    "resource": assignment.resource,
                    "start": assignment.start.isoformat(),
                    "end": assignment.end.isoformat(),
                    "comment": assignment.comment,
                }
            )
            rows += 1
    return rows
