# CLAUDE.md — Rostify

This file is the single source of truth for this project. If anything else in
the repo contradicts this file, this file wins.

## Project name

The project is **Rostify**. The folder on disk is still named `Rosty` (kept
as-is to avoid disrupting the working directory); treat the two names as the
same project and use "Rostify" consistently in docs, code, and conversation.

## Stack — locked, do not re-open

- Python 3.11+, PySide6 (LGPL licence).
- **NOT PyQt6** — its licence would force open-sourcing the product or paying
  Riverbank. This is a commercial closed-source product.
- **NOT web / React / Vite / TypeScript / Electron.**
- Do **not** use Qt Charts or Qt Data Visualization — GPL/commercial only.
  Use `pyqtgraph` or `matplotlib` for the dashboard.
- Packaging later with PyInstaller `--onedir` (LGPL requires Qt to ship as
  separate DLLs, not bundled into a single .exe).
- Storage: local SQLite plus YAML configuration files.
- Cloud sync is a **later phase**. Design the data layer so it stays
  possible, but build nothing for it now.
- Windows only for v1. Offline operation must always work.
- Access model: one editor, all other users are viewers.

## Two core architectural rules

1. **One unified model serves both planning levels.**

   ```
   Assignment(employee, start, end, resource, layer)
     layer A = day shift
     layer B = position rotation (B1 / BJ2 / BRK / FLOAT)
   ```

   One rule engine and one conflict detector serve both layers. Do not build
   two separate engines.

2. **Scheduling rules are data, not code.**

   Each rule is a plugin class that exposes a `param_schema`. The settings UI
   builds its form automatically from that schema. Users toggle rules on/off,
   edit parameters, and switch hard/soft without touching code. Adding a new
   rule means adding one file in `rules/builtin/` — core and UI must not
   change.

## Layer boundaries — strict

```
core/      domain models, schedule aggregate, calendar   — NO Qt imports
rules/     base, registry, engine, builtin/               — NO Qt imports
io/        importers/, exporters/                          — NO Qt imports
services/  analytics, persistence, event bus                — NO Qt imports
ui/        main_window, grid/, panels/, dialogs/, theme     — Qt lives here only
tests/
```

Reason: `core` and `rules` must stay testable and portable to a future cloud
server.

## Reference material

- `reference/RostaStudioSchedule.jsx` — React prototype. **Now also the
  visual reference** (decided 2026-09-25, overriding the earlier "logic
  only" restriction): its sidebar navigation, dark/light theme with
  switchable accent color, spacing, and icon-per-nav-item look are the
  target UI for Rostify's PySide6 shell. Port the *look* (layout, color
  tokens, iconography, information density) — not its React code, its
  in-memory sample-data shape, or component internals; PySide6 stays the
  actual implementation, per "Stack — locked" above. Still a reference for
  scheduling rules and data model too.
- `reference/CASINO_SCHEDULE_MASTER_2026_V3.6.xlsb` — real production casino
  schedule. Reference for rules, layout and print format.
- `reference/README_rosta_web_LEGACY.md` — the old React web prototype's
  README. Outdated, does not drive any decision.

## How to work on this project

- Ask questions before writing code.
- Give one best option, not a menu of alternatives.
- Plain, simple English in code, docs and comments.
- Complete runnable files, not fragments, once we do write code.
