"""Minimal line icons for the sidebar nav and for QSS sub-controls.

Same visual language as the reference (reference/RostaStudioSchedule.jsx
uses lucide-react's thin-stroke icons — see CLAUDE.md, "Reference material":
porting that *look* is now in scope) — hand-drawn shapes here, not copied
path data, rendered at runtime via QtSvg so no binary icon assets are
needed yet.

Two consumers, two shapes of output:

* `icon()` returns a `QIcon` for a widget that takes one (the sidebar).
* `glyph_png()` writes a PNG to a per-process cache directory and returns
  a path for QSS `image: url(...)`. Qt Style Sheets cannot take inline SVG
  or a data: URI, and a combo box's arrow and a check box's tick are only
  reachable through QSS sub-controls — so the handful of glyphs the
  stylesheet needs are rendered to disk once at startup instead of being
  checked into the repo.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE_WIDTH = 1.8

# Body markup only (no outer <svg>) — a 24x24 viewBox, stroked, no fill.
_PATHS = {
    "staff": (
        '<circle cx="8" cy="8" r="3.2"/>'
        '<path d="M2.5 20c0-3.8 2.5-6.2 5.5-6.2s5.5 2.4 5.5 6.2"/>'
        '<circle cx="16.5" cy="8.5" r="2.6"/>'
        '<path d="M13.7 14.2c1-.4 2-.6 2.8-.6 2.6 0 4.8 2.2 4.8 5.8"/>'
    ),
    "templates": (
        '<rect x="3" y="3" width="18" height="7" rx="1.5"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1.5"/>'
    ),
    "custom_view": (
        '<rect x="3" y="4" width="18" height="17" rx="2"/>'
        '<line x1="3" y1="9" x2="21" y2="9"/>'
        '<line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/>'
        '<rect x="7" y="12.5" width="10" height="4.5" rx="1"/>'
    ),
    "day_view": (
        '<circle cx="12" cy="12" r="9"/>'
        '<line x1="12" y1="12" x2="12" y2="7"/>'
        '<line x1="12" y1="12" x2="16" y2="14"/>'
    ),
    "schedule": (
        '<rect x="3" y="4" width="18" height="17" rx="2"/>'
        '<line x1="3" y1="9" x2="21" y2="9"/>'
        '<line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/>'
        '<circle cx="7.5" cy="13.5" r="1"/><circle cx="12" cy="13.5" r="1"/><circle cx="16.5" cy="13.5" r="1"/>'
        '<circle cx="7.5" cy="17.5" r="1"/><circle cx="12" cy="17.5" r="1"/>'
    ),
    "settings": (
        '<circle cx="12" cy="12" r="3.2"/>'
        '<circle cx="12" cy="12" r="8" stroke-dasharray="2.2 3.2"/>'
    ),
    "list": (
        '<rect x="3" y="4" width="18" height="4.5" rx="1"/>'
        '<rect x="3" y="10.5" width="18" height="4.5" rx="1"/>'
        '<rect x="3" y="17" width="18" height="4.5" rx="1"/>'
    ),
}

# Glyphs only the stylesheet uses. Drawn with a heavier stroke than the nav
# icons because they render at 10-12px, where 1.8px disappears.
_QSS_PATHS = {
    "chevron_down": '<path d="M5 9l7 7 7-7"/>',
    "chevron_up": '<path d="M19 15l-7-7-7 7"/>',
    "chevron_left": '<path d="M15 19l-7-7 7-7"/>',
    "chevron_right": '<path d="M9 5l7 7-7 7"/>',
    "check": '<path d="M4 12.5l5.5 5.5L20 6.5"/>',
    "dash": '<path d="M5 12h14"/>',
}
_QSS_STROKE_WIDTH = 2.4

_asset_dir: Path | None = None
_asset_cache: dict[tuple[str, str, int], str] = {}


def _svg(body: str, color: str, stroke_width: float = _STROKE_WIDTH) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def _render(body: str, color: str, size: int, stroke_width: float) -> QPixmap:
    """SVG body -> pixmap at the screen's device pixel ratio.

    Painting into a plain `QPixmap(size, size)` and letting Qt scale it up
    is what makes icons blurry at 125%/150% display scaling; sizing the
    bitmap by the ratio and tagging it keeps the edges crisp while the
    widget still lays out at `size` logical pixels.
    """
    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen is not None else 1.0
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(_svg(body, color, stroke_width).encode("utf-8"))).render(painter)
    painter.end()
    return pixmap


def icon(name: str, color: str, size: int = 20) -> QIcon:
    """Renders one of `_PATHS` at `size`x`size` in `color` (a CSS color
    string, e.g. "#c5c5c5"). Re-rendered on every call — these are only used
    for the handful of sidebar nav items, so there's no caching to bother
    with yet.
    """
    return QIcon(_render(_PATHS[name], color, size, _STROKE_WIDTH))


def glyph_png(name: str, color: str, size: int = 12) -> str:
    """Renders one of `_QSS_PATHS` to a PNG and returns its path, in the
    forward-slash form QSS `url()` wants on every platform.

    Returns "" when no `QGuiApplication` exists yet — `QPixmap` needs one.
    Callers must treat an empty path as "skip this rule" rather than
    emitting `url()` with nothing in it, which would make Qt drop the whole
    declaration and fall back to the native control.
    """
    if QGuiApplication.instance() is None:
        return ""

    key = (name, color, size)
    cached = _asset_cache.get(key)
    if cached is not None:
        return cached

    global _asset_dir
    if _asset_dir is None:
        _asset_dir = Path(tempfile.mkdtemp(prefix="rostify-glyphs-"))

    path = _asset_dir / f"{name}-{color.lstrip('#')}-{size}.png"
    _render(_QSS_PATHS[name], color, size, _QSS_STROKE_WIDTH).save(str(path))
    resolved = path.as_posix()
    _asset_cache[key] = resolved
    return resolved
