---
name: rostify-ui
description: Use when designing, building, restyling, reviewing or auditing any Rostify PySide6 interface — panels, dialogs, the sidebar, the top bar, tables, the schedule calendar, the Gantt/timeline, chips, badges, empty states, or the theme itself. Covers QSS stylesheets, design tokens, color, typography, tabular figures, spacing, radii, scrollbars, focus rings, hover/selected states, HiDPI icons, contrast, and porting the Rosta Studio look from reference/RostaStudioSchedule.jsx. Also use when the UI looks like native Windows default gray, when a widget hardcodes a hex color, or when a change to ui/ needs a visual check. Not for core/, rules/, io/ or services/ — those carry no Qt.
---

Rostify's UI must look like the Rosta Studio dark product in
`reference/RostaStudioSchedule.jsx` — never like a native Windows dialog.
Native default gray, system-default fonts, square 1990s controls and Qt's
untouched widget chrome are all failures.

You are a senior desktop UI architect working in PySide6. Every widget you
add or touch conforms 1:1 to the design system in
[reference/tokens.md](reference/tokens.md).

## Non-negotiables

1. **No hardcoded hex outside `ui/theme.py`.** Colors come from
   `theme.COLORS` / `theme.SURFACE` / `theme.TEMPLATE_COLOR_HEX`. A literal
   `"#1e1f20"` or `QColor("#232323")` in a panel is a defect, including in a
   default argument.
2. **One global stylesheet.** `theme.stylesheet()` is applied once to the
   `QApplication` in `main.py`. Per-widget `setStyleSheet` is a last resort
   for geometry that QSS cannot select (see
   [reference/qss.md](reference/qss.md), "When a local stylesheet is allowed").
   It must still interpolate tokens, never literals.
3. **Stay on the scales.** Font size, radius and spacing come from the
   scales in tokens.md. `font-size: 15px` or `border-radius: 7px` is a
   defect.
4. **Qt is not CSS.** Several properties in a web design brief fail
   *silently* in QSS — `font-variant-numeric`, `box-shadow`, `outline`,
   `gap`, `transition`, `text-transform`, `:not()`. Read
   [reference/qss.md](reference/qss.md) before writing any stylesheet and
   use the Python equivalent it gives.
5. **Qt lives in `ui/` only.** Per CLAUDE.md, `core/`, `rules/`, `io/` and
   `services/` import no Qt. Never reach for a Qt type to solve a domain
   problem.
6. **Licence bans.** No `QtCharts`, no `QtDataVisualization` (GPL/commercial
   only), no `PyQt6`. Dashboard charts use `pyqtgraph` or `matplotlib`.

## Workflow

1. **Read the incumbent before editing.** `ui/theme.py` is the token source
   of truth; `ui/sidebar.py`, `ui/panels/widgets.py` and
   `ui/panels/calendar_views.py` are the established patterns. Match them —
   do not invent a second way to build a toolbar, a chip or an icon button.
2. **Check the reference** for the surface you are building. Find the
   matching CSS class in `reference/RostaStudioSchedule.jsx` (`.sidebar-item`,
   `.dept-trigger`, `.roster-shift-badge`, …) and port its *numbers* —
   heights, padding, radius, weight, color role. Port the look, never the
   React code or its sample-data shape.
3. **Build it,** following [reference/patterns.md](reference/patterns.md)
   for shell structure (sidebar, top bar, stacked views, Gantt).
4. **Audit:** `python .claude/skills/rostify-ui/scripts/audit.py`
   Fix every finding it reports. It is fast and has no dependencies.
5. **Look at it:** `python .claude/skills/rostify-ui/scripts/shot.py --all`
   Renders each page offscreen to PNG and opens nothing. Inspect the images.
   One batched round: capture every affected page at once, fix everything
   the round shows in one pass, re-capture once to confirm, then stop.
   Do not loop screenshot→micro-edit→screenshot.

Steps 4 and 5 are the finish. Run both before reporting a UI change done.

## Judgement

- **The reference wins on look; this file wins on rules.** Where the JSX
  shows a gradient, a shadow or a transition Qt cannot reproduce, pick the
  nearest honest static equivalent rather than a bad imitation. A flat
  `surface_3` panel beats a fake painted shadow.
- **Density is the product.** This is a rota tool read at a glance across a
  month. Prefer 13px text, 42px rows and tight 8px gutters over airy
  marketing spacing. Whitespace that costs a visible week is wrong.
- **Numbers must line up.** Every column of hours, times, dates, IDs and
  counts uses tabular figures — see qss.md, "Tabular numbers".
- **Every state is designed.** Rest, hover, selected, focused, disabled and
  empty. A table with no rows shows a written empty state, not a blank box.
- **Refinement preserves.** When asked to polish a panel, keep its
  behaviour, copy and structure; change only what the brief names. Do not
  rewrite a working panel to express a preference.

## Known gaps

Current state, so you do not mistake these for decisions already made:

- `theme.py` ships the **dark ramp only**. A light theme and a switchable
  accent are the stated target (CLAUDE.md) and the reference carries full
  token sets for both — see tokens.md, "Staying light-ready". Build dark
  now; do not hardcode in a way that blocks the switch.
- **There is no top bar.** The sidebar and the page stack sit directly in
  the central widget, so the department filter and the period stepper are
  repeated inside individual panels instead of living in one shared bar.
  patterns.md, "Top bar" describes the target.
- `ui/panels/calendar_views.py` carries most of the app's inline
  `setStyleSheet` calls — one per calendar cell, re-parsed on every
  rebuild. The colors are tokens now, but the pattern is still the one
  qss.md warns about. Converting those cells to dynamic properties plus
  global rules is the next cleanup there.
- The **day timeline is not built**. When it is, it must be custom-painted
  or `QGraphicsView`, not one widget per cell — see patterns.md, "The
  schedule grid and Gantt".
