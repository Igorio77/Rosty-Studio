"""Render Rostify's pages to PNG so a UI change can actually be looked at.

Runs the real MainWindow against a throwaway seeded database in a temp
directory, so your own data/rostify.db is never opened or touched. The
window is laid out and painted but never put on screen, so nothing appears
and nothing steals focus.

    python .claude/skills/rostify-ui/scripts/shot.py --all
    python .claude/skills/rostify-ui/scripts/shot.py schedule team
    python .claude/skills/rostify-ui/scripts/shot.py --all --width 1600 --height 1000
    python .claude/skills/rostify-ui/scripts/shot.py schedule --show
    python .claude/skills/rostify-ui/scripts/shot.py --all --headless   # CI, no display

Images land in <project>/.ui-shots/ (add it to .gitignore).

Inspect the results in one batched round: capture every affected page,
fix everything the round shows in a single pass, capture once more to
confirm, then stop. Do not loop shot -> micro-edit -> shot.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Must be set before QApplication exists, so before the PySide6 imports below
# pull in the platform plugin. Only for --headless: Qt's "offscreen" plugin
# has no access to the Windows font database, so every glyph renders as a
# tofu box and the capture is useless for judging type. The default path
# keeps the native plugin and hides the window with WA_DontShowOnScreen
# instead, which lays out and paints exactly as the real app does.
if "--headless" in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from rostify.rules.registry import RuleRegistry  # noqa: E402
from rostify.services.config import build_rule_engine  # noqa: E402
from rostify.services.persistence import Repository  # noqa: E402
from rostify.services.seed_data import (  # noqa: E402
    demo_assignments,
    demo_employees,
    seed_location_codes,
    seed_lookup_lists,
    seed_templates,
)
from rostify.ui.main_window import MainWindow  # noqa: E402
from rostify.ui.sidebar import BOTTOM_NAV_ITEMS, MAIN_NAV_ITEMS, NAV_ITEMS  # noqa: E402
from rostify.ui.theme import stylesheet  # noqa: E402

# Friendlier names for the nav keys, so `shot.py team` works as well as
# `shot.py staff`. Keys themselves come from sidebar.NAV_ITEMS.
ALIASES = {"team": "staff", "roster": "schedule", "calendar": "schedule"}


def seed(data_dir: Path) -> tuple:
    """Same bootstrap as rostify.main, against a fresh directory."""
    repository = Repository(data_dir / "rostify.db")
    schedule = repository.load_schedule()

    for employee in demo_employees():
        schedule.add_employee(employee)
    for assignment in demo_assignments():
        schedule.add_assignment(assignment)
    repository.save_schedule(schedule)

    departments, subdepartments, positions = seed_lookup_lists()
    for department in departments:
        repository.save_department(department)
    for subdepartment in subdepartments:
        repository.save_subdepartment(subdepartment)
    for position in positions:
        repository.save_position(position)

    shift_ids, templates, timings = seed_templates()
    for shift_id in shift_ids:
        repository.save_shift_id(shift_id)
    for template in templates:
        repository.save_template(template)
    for timing in timings:
        repository.save_shift_timing(timing)

    for location_code in seed_location_codes():
        repository.save_location_code(location_code)

    rules_config_path = data_dir / "rules.yaml"
    rule_engine = build_rule_engine(RuleRegistry(), rules_config_path)
    return schedule, rule_engine, repository.load_location_codes(), repository, rules_config_path


def main() -> int:
    nav_keys = [key for key, _, _ in NAV_ITEMS]

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pages", nargs="*", help=f"pages to capture: {', '.join(nav_keys)}")
    parser.add_argument("--all", action="store_true", help="capture every page")
    parser.add_argument("--width", type=int, default=1420, help="window width (default 1420)")
    parser.add_argument("--height", type=int, default=820, help="window height (default 820)")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / ".ui-shots", help="output directory")
    parser.add_argument("--show", action="store_true", help="put the window on screen while capturing")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="use Qt's offscreen plugin for a machine with no display; text renders as boxes",
    )
    args = parser.parse_args()

    requested = args.pages or (nav_keys if args.all else [])
    if not requested:
        parser.error(f"name at least one page, or pass --all. Pages: {', '.join(nav_keys)}")

    pages = []
    for name in requested:
        key = ALIASES.get(name, name)
        if key not in nav_keys:
            parser.error(f"unknown page {name!r}. Pages: {', '.join(nav_keys)}")
        pages.append(key)

    args.out.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="rostify-shot-"))

    try:
        bundle = seed(temp_dir)
        app = QApplication(sys.argv[:1])
        app.setStyleSheet(stylesheet())

        window = MainWindow(*bundle)
        window.resize(args.width, args.height)
        if not args.show:
            # Full layout and paint pass, never mapped to the screen.
            window.setAttribute(Qt.WA_DontShowOnScreen, True)
        window.show()
        app.processEvents()

        main_keys = [key for key, _, _ in MAIN_NAV_ITEMS]
        bottom_keys = [key for key, _, _ in BOTTOM_NAV_ITEMS]

        written = []
        for key in pages:
            window.stack.setCurrentIndex(nav_keys.index(key))
            # Drive the sidebar the way a click does, so the captured nav
            # highlight matches the captured page. Settings lives in the
            # bottom list, so selecting by a single flat index would leave
            # the highlight on whichever main item was selected before.
            for widget, keys in (
                (window.sidebar.main_list, main_keys),
                (window.sidebar.bottom_list, bottom_keys),
            ):
                widget.blockSignals(True)
                widget.setCurrentRow(keys.index(key) if key in keys else -1)
                widget.blockSignals(False)
            app.processEvents()

            path = args.out / f"{key}.png"
            window.grab().save(str(path))
            written.append(path)

        for path in written:
            print(f"{path.relative_to(PROJECT_ROOT)}  ({path.stat().st_size // 1024} KB)")
        print(f"\n{len(written)} image(s) at {args.width}x{args.height}. Open them and look before reporting done.")
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
