# Rostify design tokens

Source of truth in code: `src/rostify/ui/theme.py`. This file is the
contract that module must satisfy. Values are the Rosta Studio dark ramp
from `reference/RostaStudioSchedule.jsx` (its `NEUTRALS.dark` and
`ACCENTS.blue.dark`).

## Surfaces — the elevation ramp

Five steps. Pick by role, never by "looks about right".

| Token       | Hex       | Used for                                      |
|-------------|-----------|-----------------------------------------------|
| `surface_0` | `#131314` | App canvas. The window background.            |
| `surface_1` | `#1e1f20` | Grids, panels, the sidebar.                   |
| `surface_2` | `#28292a` | Cards, table headers, the top bar.            |
| `surface_3` | `#303134` | Inputs, buttons at rest, menus, popovers.     |
| `surface_4` | `#3c3d40` | Hover and active states, scrollbar handles.   |

Aliases kept in `COLORS` so existing call sites keep working:
`bg_app` to 0, `bg_surface` to 1, `bg_surface_alt` to 2, `bg_control` to 3,
`bg_hover` to 4, `bg_active` to 4.

## Borders

| Token           | Value                        | Used for                         |
|-----------------|------------------------------|----------------------------------|
| `border`        | `rgba(255, 255, 255, 0.09)`  | Default hairline. Almost always. |
| `border_strong` | `rgba(255, 255, 255, 0.16)`  | Hover, popovers, menus.          |

Translucent white, not an opaque gray — it keeps its relationship to
whatever surface sits behind it. Existing keys `border_subtle` and
`border_default` both map to `border`; `border_strong` keeps its name.

## Text

| Token            | Hex       | Used for                                      |
|------------------|-----------|-----------------------------------------------|
| `text_primary`   | `#e8eaed` | Body, values, names. Not pure white.          |
| `text_secondary` | `#9aa0a6` | Labels, inactive nav items, column headers.   |
| `text_tertiary`  | `#5f6368` | Hints, week numbers, out-of-month days.       |

`#ffffff` is not a text color here. It reads as glare against `surface_0`
and is the single loudest tell of an unstyled Qt app.

## Accent — blue

| Token          | Value                          | Used for                        |
|----------------|--------------------------------|---------------------------------|
| `accent`       | `#8ab4f8`                      | Selected text, focus, today.    |
| `accent_hover` | `#aecbfa`                      | Hover on an accent surface.     |
| `accent_on`    | `#062e6f`                      | Text *on* an accent fill.       |
| `accent_soft`  | `rgba(138, 180, 248, 0.16)`    | Selected-pill background.       |

The selected sidebar item is `accent_soft` background plus `accent` text —
never a solid accent fill. Solid `accent` is reserved for the one primary
button per screen (`QPushButton#primary`) and for the selected day in a
date picker.

## Status

| Token         | Value                        |
|---------------|------------------------------|
| `danger`      | `#f28b82`                    |
| `danger_soft` | `rgba(242, 139, 130, 0.15)`  |
| `success`     | `#81c995`                    |
| `warning`     | `#fdd663`                    |

Rule-engine severities map here: hard violation to `danger`, soft violation
to `warning`, clean to `success`. Never signal a violation by color alone;
pair it with an icon or text so it survives a color-blind reader and a
grayscale print.

## Template chips

Fixed five, already in `theme.TEMPLATE_COLOR_HEX`, matching the
reference's `--tpl-*-dot`:

`blue #8ab4f8` · `green #81c995` · `amber #fdd663` · `red #f28b82` ·
`purple #c58af9`

A chip is a `rgba(dot, 0.18)` background with a lighter foreground, not a
saturated fill. Keep the set at five — it is a categorical palette sized to
stay distinguishable, and a sixth hue would collide.

## Type scale

Base is **13px**. Family is `'Segoe UI', 'Inter', sans-serif` — Segoe UI
first because Windows is the v1 target and it is always present.

| px | Role                                                      |
|----|-----------------------------------------------------------|
| 10 | Week numbers, mini-month day heads, dense grid labels.    |
| 11 | Secondary metadata under a name.                          |
| 12 | Column headers, chips, badges, hints.                     |
| 13 | **Base.** Body text, table cells, buttons, nav items.     |
| 14 | Section and period headings.                              |
| 16 | Page title.                                               |
| 20 | Dashboard stat value.                                     |
| 24 | Hero number. At most one per screen.                      |

Weights: 400 body, 500 nav items and buttons, 600 headings and selected
state, 700 column headers and stat values. Nothing else.

## Radius scale

| px  | Role                                                       |
|-----|------------------------------------------------------------|
| 4   | Chips, tiny badges, focus rings.                           |
| 6   | Icon buttons, menu items.                                  |
| 8   | Buttons, inputs, tables, cards. **The default.**           |
| 12  | Popovers, menus, dialogs, grid frames.                     |
| pill| Sidebar items, avatars, circular icon buttons.             |

In QSS a pill is `border-radius: <half the height>px`. A 42px sidebar item
is `21px`, a 40px round button is `20px`. CSS `999px` does not work — Qt
clamps radius per corner and a value larger than half the box can render
wrong, so always write the real half-height.

## Spacing scale

`2 · 4 · 6 · 8 · 12 · 16 · 24 · 32`

4px base, with 2 and 6 allowed for dense control interiors. Layout gutters
are 8 or 12; panel margins are 12 or 16; a page's outer margin is 16.
QSS has no `gap` — set it with `layout.setSpacing()` and
`layout.setContentsMargins()` in Python.

## Fixed geometry

| Element                | Value                          |
|------------------------|--------------------------------|
| Sidebar collapsed      | 64px                           |
| Sidebar expanded       | 226px                          |
| Sidebar item height    | 42px, radius 21px              |
| Top bar height         | 56px                           |
| Icon button            | 28x28, radius 6px              |
| Round icon button      | 40x40, radius 20px             |
| Nav / control icon     | 20x20, 1.8px stroke            |
| Table row (list)       | 3 wrapped lines, see `widgets.three_line_row_height` |
| Scrollbar              | 8px wide, 4px radius handle    |

## Motion

The reference uses `140ms` fast, `220ms` medium,
`cubic-bezier(0.2, 0, 0, 1)`. **QSS has no `transition`.** Either accept an
instant state change — correct for hover and selection, and what the app
does today — or animate deliberately in Python with `QPropertyAnimation`
and `QEasingCurve.OutCubic`. Reserve animation for things that move:
sidebar collapse, a popover opening. Never animate a color on hover; it
costs a repaint per frame across a dense grid.

## Staying light-ready

CLAUDE.md targets dark **and** light with a switchable accent. That is not
built yet. Build dark now, but keep the switch cheap:

- Every color goes through a token lookup, so a second ramp is a second
  dict, not an edit to every panel.
- Never assume "dark" in logic — no `if dark:` branches, no hand-darkened
  one-off hex, no white text baked into a `QColor(...)` literal.
- The reference already carries the full light ramp (`NEUTRALS.light`) and
  five accents in both modes (`ACCENTS.{blue,green,purple,rose,amber}`).
  When the switch is built, those are the values; do not invent new ones.
- `theme.stylesheet()` must stay a function that reads the active token
  dict, not a module-level constant string.
