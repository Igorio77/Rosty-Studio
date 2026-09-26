"""App-wide preferences that are not scheduling rules: appearance and the
workspace name. Stored in `data/app.yaml`, next to `rules.yaml`.

Plain data only — the UI decides what the values look like. No Qt here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

THEME_MODES = ["dark", "light"]
ACCENTS = ["blue", "green", "purple", "rose", "amber"]


@dataclass(slots=True)
class AppSettings:
    theme_mode: str = "dark"
    accent: str = "blue"
    workspace_name: str = "Casino"


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
    return settings


def save_app_settings(path: str | Path, settings: AppSettings) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(settings), f, sort_keys=False, allow_unicode=True)
