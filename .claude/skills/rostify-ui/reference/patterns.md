# Shell and component patterns

How Rostify's screens are built. Match these; do not invent a second way to
do the same job.

## App shell

```
QMainWindow
└── central QWidget
    └── QVBoxLayout (0 margins, 0 spacing)
        ├── TopBar            QWidget#topBar, fixed height 56
        └── QHBoxLayout (0 margins, 0 spacing)
            ├── Sidebar       QWidget#sidebar, fixed width 64 or 226
            └── QStackedWidget  stretch 1
```

Today `main_window.py` has no top bar — the sidebar and stack sit directly
in the central widget. When the top bar is added it goes above that row, at
full window width, so the sidebar starts below it. That is what the
reference does.

Rule: the shell owns navigation and chrome; a page owns nothing outside its
own stack slot. A panel must never reach up and restyle the sidebar or the
window.

## Sidebar

Built in `ui/sidebar.py`. Two `QListWidget`s — main nav and a bottom group
separated by a `QFrame#sidebarDivider` — so Settings sits at the bottom the
way the reference does. Only one list ever holds a selection; selecting in
one clears the other.

- Collapsed 64px, expanded 226px, items 42px tall with a 21px radius.
- Selected item: `accent_soft` background, `accent` text.
- `NAV_ITEMS` order **is** the `QStackedWidget` page order. Adding a page
  means adding to that list and to the stack in the same position.
- Collapsing clears each item's text and leaves the icon. Do not build a
  second icon-only widget set.

## Top bar

Per the reference's `.top-bar`: 56px, `surface_2`, bottom hairline, items
laid out left to right with 24px between groups.

Contents, in order: workspace or page title, department filter
(`DepartmentSubdepartmentSelector` from `panels/widgets.py`), the temporal
stepper (prev / date box / next), and the scale switcher
(Year / Month / Week / Day).

The stepper's arrows are 28x28 round buttons; the date box is a
`surface_3` control with a `border` hairline and 8px radius.

## Pages

One `QWidget` subclass per page, in `ui/panels/`. A page:

- takes its data through the constructor (`schedule`, `repository`,
  callbacks) — it never imports `main_window`;
- reports changes through a callback such as `on_change`, so persistence
  stays in `MainWindow._persist`;
- sets a 16px outer margin and 12px spacing unless it is a dense grid.

## Shared widgets

`ui/panels/widgets.py` already provides, and you should reuse:

| Helper                             | Use for                                  |
|------------------------------------|------------------------------------------|
| `icon_button(glyph, tooltip)`      | 28x28 add/edit/delete buttons            |
| `IconTableEditor`                  | Any list with add/edit/delete            |
| `SimpleFormDialog`                 | Any add/edit form except Employee        |
| `DepartmentSubdepartmentSelector`  | The cascading department pair            |
| `color_dot_icon(hex)`              | A template's color marker                |
| `three_line_row_height(table)`     | Default row height for list tables       |
| `chars_width(widget, n)`           | Default column width                     |

Writing a fourth cascading-combo pair or a second add/edit button row is a
defect, not a style choice.

## Chips and badges

A template chip is the reference's `.roster-shift-badge`: 12px text,
weight 600, 4px radius, `rgba(dot, 0.18)` background, lighter-hue
foreground, 2px/6px padding. It carries a name, never a bare color — color
alone is not an accessible label.

## Empty states

Every table, calendar and list needs one: a centered `text_tertiary` line
saying what is missing and what to do, at 13px. "No employees yet — use +
to add one." Never leave a blank surface; a blank grid reads as a bug.

## The schedule grid and Gantt

The timeline is the hardest surface and the one that must not be built from
widgets. Rules:

- **Do not** create one widget per cell. A month across a department is
  thousands of cells; a `QWidget` each will not scroll at 60fps and will
  eat memory.
- Use a **custom-painted `QWidget`** with `paintEvent`, or `QGraphicsView`
  with `QGraphicsItem`s, for the timeline and Gantt bars. Paint only the
  visible viewport rect.
- Time-to-x is one function, shared by painting and hit-testing, so a click
  always lands where the bar is drawn. Snap to the configured time step —
  that step is a rule parameter (`position_time_step`), read it, do not
  hardcode 15 or 30 minutes.
- Row height, bar radius (4px) and chip colors come from tokens, same as
  everything else.
- Hit-testing must return the domain object, not a row index, so the panel
  above it stays free of pixel math.
- Keyboard: arrow keys move the selection, Enter opens the editor. A grid
  that is mouse-only fails a scheduler working at speed.

`ui/panels/calendar_views.py` currently builds month and year views out of
`QPushButton` cells. That is acceptable at 42 cells per month; it is not
the pattern to copy for the day timeline.

## Dialogs

`SimpleFormDialog` covers nearly all of them. A dialog:

- has a real title describing the action ("Edit employee", not "Dialog");
- uses `QDialogButtonBox.Ok | Cancel` so button order follows the platform;
- validates before `accept()` and shows the error inline in a
  `QLabel[role="danger"]`, not in a second popup;
- never blocks on a `QMessageBox` for something it could show inline.

## Icons

`ui/icons.py` renders 24x24 viewBox SVG bodies with a 1.8px stroke, no
fill, round caps and joins — the thin-line language of the reference's
lucide icons. To add an icon, add a path body to `_PATHS`; do not import an
icon library and do not paste third-party path data.

Every nav item has an icon. Toolbar actions use a glyph via `icon_button`
until the icon set covers them.
