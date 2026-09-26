"""Static audit of Rostify's UI layer against the rostify-ui design system.

Checks the things a screenshot cannot show: colors that bypass the token
module, stylesheet properties Qt drops silently, licence-banned imports,
layer-boundary leaks, and values off the type/radius/spacing scales.

Standard library only. Run from anywhere:

    python .claude/skills/rostify-ui/scripts/audit.py
    python .claude/skills/rostify-ui/scripts/audit.py --warnings-only
    python .claude/skills/rostify-ui/scripts/audit.py src/rostify/ui/sidebar.py

Exit code is 1 if any ERROR was found, otherwise 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC = PROJECT_ROOT / "src" / "rostify"
UI = SRC / "ui"
THEME = UI / "theme.py"

# Scales from reference/tokens.md.
FONT_SIZES = {10, 11, 12, 13, 14, 16, 20, 24}
RADII = {0, 4, 6, 8, 12}
# Half of a fixed-size control, which is how a pill is written in QSS:
# the 10px template dot, the 22px and 24px day buttons, the 40px round
# toggle, the 42px sidebar item, the 44px day-number badge.
PILL_RADII = {5, 11, 20, 21, 22}
SPACING = {0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 32}

# QSS properties Qt parses and then ignores. Value is the Python fix.
IGNORED_QSS = {
    "font-variant-numeric": "QFont.setFeature(QFont.Tag('tnum'), 1)",
    "box-shadow": "QGraphicsDropShadowEffect, sparingly",
    "gap": "layout.setSpacing(n)",
    "transition": "QPropertyAnimation, or accept an instant change",
    "text-transform": "uppercase the string in Python",
    "letter-spacing": "QFont.setLetterSpacing(...)",
    "cursor": "widget.setCursor(Qt.PointingHandCursor)",
    "transform": "QTransform on a painted widget",
    "box-sizing": "not a Qt concept; remove it",
    "flex": "use a QLayout",
    "z-index": "widget.raise_() / lower()",
}

BANNED_IMPORTS = {
    "PyQt6": "licence: PyQt6 is GPL/commercial. This project uses PySide6 (LGPL).",
    "QtCharts": "licence: Qt Charts is GPL/commercial. Use pyqtgraph or matplotlib.",
    "QtDataVisualization": "licence: GPL/commercial. Use pyqtgraph or matplotlib.",
}

NO_QT_PACKAGES = ("core", "rules", "io", "services")

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
FONT_RE = re.compile(r"font-size:\s*(\d+)px")
RADIUS_RE = re.compile(r"border-radius:\s*(\d+)px")
PADDING_RE = re.compile(r"(?:padding|margin)(?:-(?:top|right|bottom|left))?:\s*([0-9 px]+?);")
PX_RE = re.compile(r"(\d+)px")


@dataclass
class Finding:
    level: str  # "ERROR" or "WARN"
    check: str
    path: Path
    line: int
    text: str
    hint: str


def iter_code_lines(path: Path):
    """Yield (line_number, line) skipping comment-only lines and docstrings.

    Tracks triple-quoted blocks well enough for this codebase, where every
    docstring opens and closes on its own terms and QSS lives in f-strings
    that start on a line with other code.
    """
    in_doc = False
    delim = ""
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if in_doc:
            if delim in stripped:
                in_doc = False
            continue
        if stripped.startswith(('"""', "'''")):
            delim = stripped[:3]
            body = stripped[3:]
            if delim not in body:  # docstring continues past this line
                in_doc = True
            continue
        if stripped.startswith("#"):
            continue
        yield number, raw


def strip_trailing_comment(line: str) -> str:
    """Drop a trailing ` # ...` comment, leaving quoted '#' colors alone."""
    quote = None
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and index and line[index - 1] in " \t":
            return line[:index]
    return line


def check_file(path: Path, findings: list[Finding]) -> None:
    rel = path.relative_to(PROJECT_ROOT)
    is_theme = path.resolve() == THEME.resolve()
    package = rel.parts[2] if len(rel.parts) > 2 else ""
    source = path.read_text(encoding="utf-8")

    has_pixmap = "QPixmap(" in source
    has_ratio = "setDevicePixelRatio" in source

    for number, raw in iter_code_lines(path):
        line = strip_trailing_comment(raw)

        for banned, why in BANNED_IMPORTS.items():
            if banned in line and ("import" in line or "from" in line):
                findings.append(Finding("ERROR", "banned-import", rel, number, line.strip(), why))

        if package in NO_QT_PACKAGES and re.search(r"\b(?:from|import)\s+PySide6", line):
            findings.append(
                Finding(
                    "ERROR",
                    "layer-boundary",
                    rel,
                    number,
                    line.strip(),
                    f"CLAUDE.md: {package}/ imports no Qt. Keep it portable.",
                )
            )

        if not is_theme:
            for match in HEX_RE.finditer(line):
                findings.append(
                    Finding(
                        "ERROR",
                        "hardcoded-color",
                        rel,
                        number,
                        match.group(0),
                        "use theme.COLORS / theme.SURFACE / theme.TEMPLATE_COLOR_HEX",
                    )
                )

        lowered = line.lower()
        for prop, fix in IGNORED_QSS.items():
            if re.search(rf"(?:^|[\"'{{;\s]){re.escape(prop)}\s*:", lowered):
                findings.append(
                    Finding("ERROR", "ignored-by-qt", rel, number, f"{prop}:", fix)
                )

        for match in FONT_RE.finditer(line):
            size = int(match.group(1))
            if size not in FONT_SIZES:
                findings.append(
                    Finding(
                        "WARN",
                        "off-type-scale",
                        rel,
                        number,
                        match.group(0),
                        f"type scale is {sorted(FONT_SIZES)}",
                    )
                )

        for match in RADIUS_RE.finditer(line):
            radius = int(match.group(1))
            if radius not in RADII and radius not in PILL_RADII:
                findings.append(
                    Finding(
                        "WARN",
                        "off-radius-scale",
                        rel,
                        number,
                        match.group(0),
                        f"radius scale is {sorted(RADII)}, or half a fixed height for a pill",
                    )
                )

        for match in PADDING_RE.finditer(line):
            for value in PX_RE.findall(match.group(1)):
                if int(value) not in SPACING:
                    findings.append(
                        Finding(
                            "WARN",
                            "off-spacing-scale",
                            rel,
                            number,
                            match.group(0).strip(),
                            f"spacing scale is {sorted(SPACING)}",
                        )
                    )

        if re.search(r"color:\s*(?:#fff(?:fff)?\b|white\b)", lowered):
            findings.append(
                Finding(
                    "WARN",
                    "pure-white-text",
                    rel,
                    number,
                    line.strip(),
                    "text_primary is #e8eaed; pure white reads as glare",
                )
            )

    if has_pixmap and not has_ratio:
        findings.append(
            Finding(
                "WARN",
                "hidpi-pixmap",
                rel,
                0,
                "QPixmap(...) with no setDevicePixelRatio",
                "blurs at 125%/150% scaling; see reference/qss.md, HiDPI icons",
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="files to check (default: all of src/rostify)")
    parser.add_argument("--warnings-only", action="store_true", help="hide errors, show warnings")
    args = parser.parse_args()

    if args.paths:
        targets = [Path(p).resolve() for p in args.paths]
    else:
        targets = sorted(SRC.rglob("*.py"))

    if not targets:
        print("No Python files found. Is this the Rostify project?", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    for path in targets:
        check_file(path, findings)

    errors = [f for f in findings if f.level == "ERROR"]
    warnings = [f for f in findings if f.level == "WARN"]
    shown = warnings if args.warnings_only else errors + warnings

    if not shown:
        print(f"rostify-ui audit: clean across {len(targets)} file(s).")
        return 0

    by_check: dict[str, list[Finding]] = {}
    for finding in shown:
        by_check.setdefault(finding.check, []).append(finding)

    for check in sorted(by_check, key=lambda c: (by_check[c][0].level != "ERROR", c)):
        group = by_check[check]
        print(f"\n{group[0].level}  {check}  ({len(group)})")
        print(f"  {group[0].hint}")
        for finding in group[:20]:
            where = f"{finding.path}:{finding.line}" if finding.line else str(finding.path)
            print(f"    {where}  {finding.text}")
        if len(group) > 20:
            print(f"    ... and {len(group) - 20} more")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s) across {len(targets)} file(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
