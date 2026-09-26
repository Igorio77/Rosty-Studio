# Rostify

Customizable, local-first workforce scheduling desktop app. Windows, Python
3.11+, PySide6 (LGPL). See `CLAUDE.md` for the locked stack, the two core
architectural rules, and the layer boundaries — that file is the source of
truth for this project, not this README.

## Status

Phase 0 foundation, wired end to end and tested:
- `core/` — `Employee`, the unified `Assignment` model (layer A = shift,
  layer B = position rotation), and the `Schedule` aggregate.
- `rules/` — the plugin rule engine (`Rule` base class with a declarative
  `param_schema`, auto-discovery, `RuleEngine`) plus three builtin rules
  ported from the real production workbook's export-time checks (see
  `docs/01-analysis.md` §4.1): max field length, employee-id format,
  overlapping-assignment detection.
- `services/` — SQLite persistence, YAML rule configuration, a minimal
  event bus, and seed data (the real position-code catalog from
  `reference/CASINO_SCHEDULE_MASTER_2026_V3.6.xlsb`'s `Abbreviation` sheet,
  plus fictional demo employees — see `services/seed_data.py` for why real
  crew data is never used here).
- `io/` — a working roster CSV export.
- `ui/` — a PySide6 main window with three tabs (Staff, Schedule, Settings)
  wired to all of the above, including a settings form generated entirely
  from each rule's `param_schema`.
- `tests/` — 13 passing unit tests covering the core model and the rule
  engine.

Not built yet (see `reference/README_rosta_web_LEGACY.md` and
`reference/legacy_web/ROADMAP_RU_STALE.md` for the original phased plan,
now superseded by `CLAUDE.md` + `docs/01-analysis.md`): the paintable day
grid, Excel/CSV team import, week/month/Gantt views, real double-booking /
rest-period / max-hours rules (explicit gap, see `docs/01-analysis.md` §4.3
— needs the domain expert, not more file-reading), multi-user sync,
PyInstaller packaging.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```powershell
python -m rostify.main
```

First run seeds a handful of fictional demo employees and writes
`data/rostify.db` + `data/rules.yaml` (gitignored). Override the data
location with the `ROSTIFY_DATA_DIR` environment variable.

## Test

```powershell
pytest
```
