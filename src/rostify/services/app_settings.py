"""App-wide preferences that are not scheduling rules: appearance, the
workspace name and the Day/Custom grid zoom. Stored in `data/app.yaml`, next to `rules.yaml`.

Plain data only — the UI decides what the values look like. No Qt here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

THEME_MODES = ["dark", "light"]
ACCENTS = ["blue", "green", "purple", "rose", "amber"]
ZOOM_MIN, ZOOM_MAX = 0.5, 2.0


@dataclass(slots=True)
class AppSettings:
    theme_mode: str = "dark"
    accent: str = "blue"
    workspace_name: str = "Casino"
    # Grid zoom (1.0 = 100%), remembered per view.
    day_zoom: float = 1.0
    custom_zoom: float = 1.0
    team_zoom: float = 1.0
    templates_zoom: float = 1.0
    # The department this workspace plans (Settings -> General). Empty
    # means "the first one in Settings -> Lists".
    department: str = ""
    # Month view: is the Templates panel on the right open?
    month_templates_panel: bool = True


def load_app_settings(path: str | Path) -> AppSettings:
    path = Path(path)
    if not path.exists():
        return AppSettings()
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    settings = AppSettings()
    if data.get("theme_mode") in THEME_MODES:
        settings.theme_mode = data["theme_mode"]
    if data.get("accent") in ACCENTS:
        settings.accent = data["accent"]
    if isinstance(data.get("workspace_name"), str) and data["workspace_name"].strip():
        settings.workspace_name = data["workspace_name"].strip()
    if isinstance(data.get("department"), str):
        settings.department = data["department"].strip()
    if isinstance(data.get("month_templates_panel"), bool):
        settings.month_templates_panel = data["month_templates_panel"]
    for key in ("day_zoom", "custom_zoom", "team_zoom", "templates_zoom"):
        value = data.get(key)
        if isinstance(value, (int, float)) and ZOOM_MIN <= value <= ZOOM_MAX:
            setattr(settings, key, float(value))
    return settings


def save_app_settings(path: str | Path, settings: AppSettings) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(settings), f, sort_keys=False, allow_unicode=True)
