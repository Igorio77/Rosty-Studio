# Qt Style Sheets: what actually works

QSS looks like CSS and is not CSS. The properties below are the ones a web
design brief reaches for by reflex. Qt does not error on them — it drops
them silently, so the app just quietly looks wrong.

## Silently ignored — never write these in QSS

| CSS property           | What to do instead                                  |
|------------------------|-----------------------------------------------------|
| `font-variant-numeric` | `QFont.setFeature` in Python. See below.            |
| `box-shadow`           | `QGraphicsDropShadowEffect`, sparingly. See below.  |
| `gap`                  | `layout.setSpacing(n)`.                             |
| `transition`           | `QPropertyAnimation`, or accept an instant change.  |
| `text-transform`       | Uppercase the string in Python: `label.upper()`.    |
| `letter-spacing`       | `QFont.setLetterSpacing(QFont.AbsoluteSpacing, n)`. |
| `cursor`               | `widget.setCursor(Qt.PointingHandCursor)`.          |
| `opacity`              | `QGraphicsOpacityEffect`, or an rgba color.         |
| `flex`, `grid`         | `QHBoxLayout` / `QVBoxLayout` / `QGridLayout`.      |
| `:not()`, `>`, `~`     | A dynamic property selector. See below.             |
| `::before`, `::after`  | A real child widget, or paint it.                   |
| `transform`            | `QTransform` on a painted widget.                   |
| `min-width` on a label | `setMinimumWidth()` — QSS min-width is box-only.    |

`calc()`, CSS custom properties (`--token`, `var()`) and media queries do
not exist either. Tokens are interpolated in Python f-strings.

**`rgba()` alpha:** Qt parses `rgba(255, 255, 255, 0.09)` (float) and
`rgba(255, 255, 255, 23)` (0-255 int). It does **not** parse the
`rgba(255, 255, 255, 9%)` percentage form — that declaration is dropped and
the element paints opaque. Verified against this project's venv. Every
border token here uses the float form.

**No CSS triangle trick.** Building an arrow out of transparent borders
(`width: 0; border-left: 4px solid transparent; border-top: 5px solid ...`)
renders as a small filled rectangle in Qt, not a triangle. A sub-control
arrow needs a real `image:` — see "Sub-control glyphs" below.

## Tabular numbers

The rota grid is columns of hours, times and counts. They must line up.
`font-variant-numeric: tabular-nums` does nothing in QSS. PySide6 6.11
supports OpenType features on `QFont`:

```python
from PySide6.QtGui import QFont

def tabular(font: QFont) -> QFont:
    """Same font with proportional digits switched to fixed-width ones."""
    out = QFont(font)
    out.setFeature(QFont.Tag("tnum"), 1)
    return out
```

The tag must be a `QFont.Tag`. Passing the plain string `"tnum"` raises
`ValueError` on PySide6 6.11 despite what the signature advertises —
verified against this project's venv.

Apply it to the widget that shows the numbers, not globally — body text
reads better with proportional figures:

```python
table.setFont(tabular(table.font()))
```

Segoe UI carries `tnum`. If a future font does not, fall back to
`QFont.Monospace` for those cells rather than shipping ragged columns.

## Focus rings

`outline` is one of the few CSS-looking properties Qt *does* support, and
`outline: none` is the documented way to kill the dotted focus rectangle
that makes an item view look like Windows 98. Rendering of a *visible*
outline varies by widget and style, so remove it with `outline` and
indicate focus with a border color change:

```
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid {accent};
}
QPushButton:focus {
    border: 1px solid {accent};
}
```

Never remove focus indication without replacing it — keyboard users need
it, and this app has a data-entry grid. For widgets where a border change
is invisible, set `setFocusPolicy(Qt.NoFocus)` so they are skipped in the
tab order instead of focusable-but-unmarked.

## Shadows

`box-shadow` is ignored. `QGraphicsDropShadowEffect` works but re-renders
the widget through a software path — it is slow and it breaks child widget
clipping. Rules:

- Allowed on a popover, a menu, a dialog, a drag ghost. One at a time.
- Never on a table row, a grid cell, a chip, or anything in a repeated list.
- Prefer elevation by surface step (`surface_2` card on a `surface_1`
  panel) plus a `border_strong` hairline. That is how the reference reads
  at density anyway.

## Backgrounds on a plain QWidget

A bare `QWidget` ignores its QSS `background` unless you tell it to paint
one:

```python
panel.setAttribute(Qt.WA_StyledBackground, True)
```

This is the single most common "my stylesheet does nothing" cause.
`QFrame` and most concrete widgets do not need it; `QWidget` subclasses
used as containers do.

## Border radius does not clip children

Setting `border-radius` on a container rounds the container's own painted
background only. A child `QTableView` will still square off the corners.
Either give the child the same radius, or accept the square child and put
the radius on the outermost painted surface only.

## State via dynamic properties

QSS has no `:not()` and no arbitrary class selector. Use a Qt dynamic
property, which the codebase already does (`QLabel[role="hint"]`):

```
QLabel[role="hint"]   { color: {text_tertiary}; }
QLabel[role="danger"] { color: {danger}; }
QFrame[state="violation"] { border: 1px solid {danger}; }
```

```python
label.setProperty("role", "hint")
```

**A property changed after the widget is shown does not restyle itself.**
Force it:

```python
def repolish(widget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
```

Forgetting `repolish` is why a violation highlight "does not appear until
you resize the window".

## When a local stylesheet is allowed

The global sheet in `theme.stylesheet()` is the default. A per-widget
`setStyleSheet` is justified only when:

1. The rule targets one instance that QSS cannot select — a specific
   calendar cell whose background depends on runtime data.
2. It overrides geometry the global sheet sets too generously, e.g.
   `widgets.icon_button` stripping the global 6px/14px button padding down
   to fit a 28x28 box.

Even then, interpolate tokens: `f"background: {COLORS['bg_hover']};"`,
never `"background: #3c3d40;"`.

Cost to know: a local stylesheet on a parent is re-parsed for every child
that inherits it. Setting one inside a loop over calendar days is a real
performance problem — 42 cells times a re-parse per repaint. Prefer a
dynamic property plus one global rule.

## Scrollbars

Qt's default scrollbar is the loudest native-Windows tell after gray
backgrounds. Style all four sub-controls or it looks half-done:

```
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: {surface_4};
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: {border_strong};
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
```

Repeat for `:horizontal` with `height: 8px` and `min-width: 24px`. Omitting
`add-line`/`sub-line` leaves the native stepper arrows visible.

## Sub-control glyphs

`QComboBox::down-arrow`, `QCheckBox::indicator:checked` and the spin-box
arrows can only be changed through QSS, and QSS takes neither inline SVG
nor a `data:` URI — only `image: url(<path>)` pointing at a real file. This
project ships no binary icon assets, so `ui/icons.glyph_png()` renders the
few glyphs the stylesheet needs into a per-process temp directory at
startup and returns a path.

Two rules when adding one:

- Add the path body to `icons._QSS_PATHS`, not to `_PATHS` — QSS glyphs
  render at 10-12px and need the heavier `_QSS_STROKE_WIDTH`, where the
  nav icons' 1.8px stroke would disappear.
- Guard for an empty path. `glyph_png` returns `""` before a
  `QGuiApplication` exists, and emitting `image: url();` makes Qt drop the
  whole declaration and fall back to the native control. `theme._image_rule`
  is the wrapper that handles this; use it.

A check box indicator does not need an image to look right — border,
radius and an accent fill already read as checked. The tick is there
because "checked" should not rest on color alone.

## HiDPI icons

`ui/icons.py` builds a `QPixmap(size, size)` and renders SVG into it. On a
125% or 150% display Qt scales that bitmap up and it blurs. Render at the
device ratio:

```python
from PySide6.QtGui import QGuiApplication

def icon(name: str, color: str, size: int = 20) -> QIcon:
    ratio = QGuiApplication.primaryScreen().devicePixelRatio()
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    ...
```

Same rule for `widgets.color_dot_icon` and anything else that paints into a
fixed-size `QPixmap`.

## Table chrome

`QTableView` / `QTableWidget` need explicit work to stop looking native:

- `setShowGrid(False)` when the design uses row separators instead.
- `verticalHeader().setVisible(False)` unless row numbers are meaningful.
- `setAlternatingRowColors(True)` pairs with the `alternate-background-color`
  QSS property, which is the only way to set the stripe.
- `setFrameShape(QFrame.NoFrame)` if the container already draws a border,
  otherwise you get a double line.
- `horizontalHeader().setHighlightSections(False)` — the default bolds the
  header of the selected column, which fights the design.
- Selection colors come from QSS `selection-background-color` and
  `selection-color`, not from a palette call.

## QSS selector reference that does work

```
QPushButton                      type
QPushButton#primary              objectName
QPushButton[role="ghost"]        dynamic property
QWidget#sidebar QPushButton      descendant
QPushButton:hover:!pressed       state combination
QComboBox::drop-down             sub-control
QComboBox QAbstractItemView      the popup, styled separately
```

The popup list of a `QComboBox` is a separate widget and is **not** covered
by rules on `QComboBox`. Style `QComboBox QAbstractItemView` explicitly or
the dropdown stays native white.

## Object name registry

Keep these stable; QSS object names are case-sensitive and a typo fails
silently.

| objectName        | Widget                                 |
|-------------------|----------------------------------------|
| `sidebar`         | The left nav container                 |
| `sidebarToggle`   | Hamburger button                       |
| `sidebarNav`      | Either nav `QListWidget`               |
| `sidebarDivider`  | Line above the bottom nav group        |
| `primary`         | The one primary button on a screen     |
| `topBar`          | Top bar container                      |
| `monthGridFrame`  | Month calendar frame                   |
| `miniMonthFrame`  | Year-view mini month frame             |
| `dayViewBanner`   | Day view's date + template banner      |
| `compactCombo`    | Any combo exempt from the 160px floor  |

Existing names are lowercase-first camelCase. Stay with that convention.
