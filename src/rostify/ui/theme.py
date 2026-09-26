"""Theme stylesheet and the token tables it is built from.

Colors are the Rosta Studio ramps from reference/RostaStudioSchedule.jsx:
dark and light neutrals plus five switchable accents. The module starts on
dark + blue; `apply_theme()` switches to the user's saved choice. Porting that prototype's visual look — colors,
sidebar layout, spacing — is in scope per CLAUDE.md, "Reference material"
(decided 2026-09-25).

Two rules hold this module together:

* Every color in the app comes from here. A hex literal anywhere else in
  `ui/` is a defect — see `.claude/skills/rostify-ui/`.
* `stylesheet()` stays a *function* reading the token dicts, not a module
  constant. A light theme and a switchable accent are the stated target
  (CLAUDE.md); keeping this a function is what makes that a second dict
  rather than an edit to every panel.
"""

from __future__ import annotations

from . import icons

# The elevation ramp. Pick a step by role, never by "looks about right":
# 0 canvas · 1 panels and grids · 2 cards and headers · 3 controls at rest ·
# 4 hover and active.
SURFACE = {
    0: "#131314",
    1: "#1e1f20",
    2: "#28292a",
    3: "#303134",
    4: "#3c3d40",
}

# Segoe UI first: Windows is the v1 target and it is always present, it
# carries the `tnum` feature the schedule grid needs, and it is what the
# reference falls back to on Windows anyway.
FONT_FAMILY = "'Segoe UI', 'Inter', sans-serif"
FONT_SIZE_BASE = 13

COLORS = {
    # --- surfaces -------------------------------------------------------
    "bg_app": SURFACE[0],
    "bg_surface": SURFACE[1],
    "bg_surface_alt": SURFACE[2],
    "bg_control": SURFACE[3],
    # `bg_hover` and `bg_active` both land on surface 4: the ramp has one
    # interactive step, and the difference between hover and pressed is
    # carried by the border, not a second fill.
    "bg_hover": SURFACE[4],
    "bg_active": SURFACE[4],
    # --- borders --------------------------------------------------------
    # Translucent white, not an opaque grey, so a border keeps its
    # relationship to whichever surface sits behind it. Qt parses a float
    # alpha here; it does *not* parse the `50%` form.
    "border": "rgba(255, 255, 255, 0.09)",
    "border_subtle": "rgba(255, 255, 255, 0.09)",
    "border_default": "rgba(255, 255, 255, 0.09)",
    "border_strong": "rgba(255, 255, 255, 0.16)",
    # --- text -----------------------------------------------------------
    # Not pure white. #ffffff against surface 0 reads as glare and is the
    # loudest tell of an unstyled Qt app.
    "text_primary": "#e8eaed",
    "text_secondary": "#9aa0a6",
    "text_tertiary": "#5f6368",
    # --- accent ---------------------------------------------------------
    "accent": "#8ab4f8",
    "accent_hover": "#aecbfa",
    "accent_on": "#062e6f",  # text and glyphs drawn *on* an accent fill
    "accent_soft": "rgba(138, 180, 248, 0.16)",  # selected-pill background
    # Text drawn *on* a saturated TEMPLATE_COLOR_HEX fill — the reference's
    # `.roster-shift-badge` color. One value for all five chip hues: they
    # are light enough that dark ink is the readable choice on every one.
    "chip_on": "rgba(0, 0, 0, 0.75)",
    # --- status ---------------------------------------------------------
    "danger": "#f28b82",
    "danger_soft": "rgba(242, 139, 130, 0.15)",
    "success": "#81c995",
    "warning": "#fdd663",
}

# Both neutral ramps, straight from the reference's SURFACE_THEMES. The
# light ramp has no success/warning of its own, so it borrows the light
# green and amber accents from ACCENT_THEMES below.
_NEUTRALS = {
    "dark": {
        "surfaces": ["#131314", "#1e1f20", "#28292a", "#303134", "#3c3d40"],
        "border": "rgba(255, 255, 255, 0.09)",
        "border_strong": "rgba(255, 255, 255, 0.16)",
        "text_primary": "#e8eaed",
        "text_secondary": "#9aa0a6",
        "text_tertiary": "#5f6368",
        "danger": "#f28b82",
        "danger_soft": "rgba(242, 139, 130, 0.15)",
        "success": "#81c995",
        "warning": "#fdd663",
    },
    "light": {
        "surfaces": ["#eef0f2", "#ffffff", "#f6f7f8", "#eceef0", "#e1e3e6"],
        "border": "rgba(0, 0, 0, 0.09)",
        "border_strong": "rgba(0, 0, 0, 0.16)",
        "text_primary": "#1f1f1f",
        "text_secondary": "#5f6368",
        "text_tertiary": "#80868b",
        "danger": "#d93025",
        "danger_soft": "rgba(217, 48, 37, 0.08)",
        "success": "#1e8e4a",
        "warning": "#a6720a",
    },
}

# The five switchable accents, per mode, from the reference's COLOR_THEMES.
ACCENT_THEMES = {
    "blue": {
        "name": "Blue",
        "dark": ("#8ab4f8", "#aecbfa", "#062e6f", "rgba(138, 180, 248, 0.16)"),
        "light": ("#3b6fd6", "#2955ad", "#ffffff", "rgba(59, 111, 214, 0.12)"),
    },
    "green": {
        "name": "Green",
        "dark": ("#81c995", "#a8dab5", "#0b3d1e", "rgba(129, 201, 149, 0.16)"),
        "light": ("#1e8e4a", "#166937", "#ffffff", "rgba(30, 142, 74, 0.12)"),
    },
    "purple": {
        "name": "Purple",
        "dark": ("#c58af9", "#d7aefb", "#3a0d63", "rgba(197, 138, 249, 0.16)"),
        "light": ("#8430ce", "#6b23a8", "#ffffff", "rgba(132, 48, 206, 0.12)"),
    },
    "rose": {
        "name": "Rose",
        "dark": ("#f6a3ae", "#f8bcc4", "#5c0a1c", "rgba(246, 163, 174, 0.18)"),
        "light": ("#d23a63", "#ab2c4f", "#ffffff", "rgba(210, 58, 99, 0.12)"),
    },
    "amber": {
        "name": "Amber",
        "dark": ("#fdd663", "#fde293", "#4a3400", "rgba(253, 214, 99, 0.16)"),
        "light": ("#a6720a", "#845a08", "#ffffff", "rgba(166, 114, 10, 0.12)"),
    },
}


def apply_theme(mode: str, accent: str) -> None:
    """Switch the active tokens to `mode` ("dark"/"light") and `accent`.

    Mutates SURFACE and COLORS *in place*, so every module that imported
    them keeps seeing the live values. Widgets that already baked a color
    into a local stylesheet keep the old one until they are rebuilt — the
    main window is rebuilt after a switch for exactly that reason.
    """
    neutrals = _NEUTRALS.get(mode, _NEUTRALS["dark"])
    accent_theme = ACCENT_THEMES.get(accent, ACCENT_THEMES["blue"])
    accent_hex, accent_hover, accent_on, accent_soft = accent_theme[mode if mode in _NEUTRALS else "dark"]

    for step, value in enumerate(neutrals["surfaces"]):
        SURFACE[step] = value
    COLORS.update(
        bg_app=SURFACE[0],
        bg_surface=SURFACE[1],
        bg_surface_alt=SURFACE[2],
        bg_control=SURFACE[3],
        bg_hover=SURFACE[4],
        bg_active=SURFACE[4],
        border=neutrals["border"],
        border_subtle=neutrals["border"],
        border_default=neutrals["border"],
        border_strong=neutrals["border_strong"],
        text_primary=neutrals["text_primary"],
        text_secondary=neutrals["text_secondary"],
        text_tertiary=neutrals["text_tertiary"],
        accent=accent_hex,
        accent_hover=accent_hover,
        accent_on=accent_on,
        accent_soft=accent_soft,
        danger=neutrals["danger"],
        danger_soft=neutrals["danger_soft"],
        success=neutrals["success"],
        warning=neutrals["warning"],
    )


def accent_swatch(accent: str, mode: str) -> str:
    """The solid color that represents `accent` in `mode`, for the picker."""
    theme = ACCENT_THEMES.get(accent, ACCENT_THEMES["blue"])
    return theme[mode if mode in _NEUTRALS else "dark"][0]

# Fixed 5-color palette for Template chips (core/templates.TEMPLATE_COLORS),
# same hues as reference/RostaStudioSchedule.jsx's dark-mode tpl-*-dot
# values — used on the Templates matrix and the Month/Year calendar.
TEMPLATE_COLOR_HEX = {
    "blue": "#8ab4f8",
    "green": "#81c995",
    "amber": "#fdd663",
    "red": "#f28b82",
    "purple": "#c58af9",
}


def mix(foreground: str, background: str, ratio: float) -> str:
    """Flatten `foreground` over `background` at `ratio` and return a hex
    string.

    For the places that need a tinted *opaque* color rather than a
    translucent overlay — a `QColor` handed to `setBackground` on a table
    item, say, where an alpha channel would blend against whatever happens
    to be behind it instead of against the row. Both inputs must be
    `#rrggbb`.
    """
    fg = foreground.lstrip("#")
    bg = background.lstrip("#")
    channels = (
        round(int(fg[i : i + 2], 16) * ratio + int(bg[i : i + 2], 16) * (1 - ratio))
        for i in (0, 2, 4)
    )
    return "#" + "".join(f"{value:02x}" for value in channels)


def _image_rule(name: str, color: str, size: int = 12) -> str:
    """`image: url(...);` for a QSS sub-control, or "" if the glyph could
    not be rendered (no QGuiApplication yet). An empty `url()` makes Qt
    drop the whole declaration and fall back to the native control, so the
    caller must be able to omit the line entirely.
    """
    path = icons.glyph_png(name, color, size)
    return f"image: url({path});" if path else ""


def stylesheet() -> str:
    c = COLORS
    chevron_down = _image_rule("chevron_down", c["text_secondary"])
    chevron_up = _image_rule("chevron_up", c["text_secondary"])
    check_on_accent = _image_rule("check", c["accent_on"], 12)
    check_muted = _image_rule("check", c["text_tertiary"], 12)

    return f"""
    /* ---------- base ---------------------------------------------------- */
    QMainWindow, QWidget {{
        background-color: {c['bg_app']};
        color: {c['text_primary']};
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BASE}px;
    }}
    QWidget:disabled {{
        color: {c['text_tertiary']};
    }}

    /* ---------- menu bar -------------------------------------------------- */
    QMenuBar {{
        background: {c['bg_surface_alt']};
        color: {c['text_secondary']};
        border-bottom: 1px solid {c['border']};
        padding: 2px 4px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 6px 10px;
        border-radius: 6px;
    }}
    QMenuBar::item:selected {{
        background: {c['bg_hover']};
        color: {c['text_primary']};
    }}

    /* ---------- tabs ------------------------------------------------------ */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background: {c['bg_surface']};
    }}
    QTabBar::tab {{
        background: {c['bg_app']};
        color: {c['text_secondary']};
        padding: 8px 16px;
        border: 1px solid {c['border']};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    QTabBar::tab:selected {{
        background: {c['bg_surface']};
        color: {c['text_primary']};
        border-bottom: 2px solid {c['accent']};
    }}

    /* ---------- tables ---------------------------------------------------- */
    QTableView, QTableWidget {{
        background: {c['bg_surface']};
        alternate-background-color: {c['bg_surface_alt']};
        gridline-color: {c['border']};
        color: {c['text_primary']};
        selection-background-color: {c['accent_soft']};
        selection-color: {c['accent']};
        border: 1px solid {c['border']};
        border-radius: 8px;
    }}
    /* The viewport is a plain child QWidget, so the base QWidget rule paints
       the app canvas into every table's empty area unless this overrides it. */
    QTableView QWidget#qt_scrollarea_viewport {{
        background: {c['bg_surface']};
    }}
    /* The header strip past its last section; without this it shows the
       app canvas as a dark band next to the column headers. */
    QHeaderView {{
        background: {c['bg_surface_alt']};
        border: none;
    }}
    QHeaderView::section {{
        background: {c['bg_surface_alt']};
        color: {c['text_secondary']};
        font-weight: 700;
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid {c['border']};
        border-right: 1px solid {c['border']};
    }}
    QTableCornerButton::section {{
        background: {c['bg_surface_alt']};
        border: none;
        border-bottom: 1px solid {c['border']};
    }}

    /* ---------- buttons --------------------------------------------------- */
    QPushButton {{
        background: {c['bg_control']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 6px 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: {c['bg_hover']};
        border-color: {c['border_strong']};
    }}
    QPushButton:pressed {{
        background: {c['bg_active']};
        border-color: {c['accent']};
    }}
    QPushButton:focus {{
        border-color: {c['accent']};
    }}
    QPushButton:disabled {{
        color: {c['text_tertiary']};
        border-color: {c['border']};
    }}
    QPushButton#primary {{
        background: {c['accent']};
        color: {c['accent_on']};
        border: none;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{
        background: {c['accent_hover']};
    }}

    /* ---------- inputs ---------------------------------------------------- */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QPlainTextEdit, QTextEdit {{
        background: {c['bg_control']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 4px 6px;
        selection-background-color: {c['accent']};
        selection-color: {c['accent_on']};
    }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
    QDateEdit:hover, QTimeEdit:hover {{
        border-color: {c['border_strong']};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QDateEdit:focus, QTimeEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border-color: {c['accent']};
    }}

    /* ---------- combo box -------------------------------------------------- */
    /* Without an explicit ::drop-down and ::down-arrow, Qt draws the native
       Windows arrow — the most visible "unstyled app" tell on a filter row. */
    QComboBox {{
        min-width: 160px;
    }}
    /* A combo holding two or three characters — a time step, a count. The
       160px floor above is a sensible default for a name or a template
       picker and far too wide for these; QSS min-width wins over
       setFixedWidth, so the exemption has to live here. */
    QComboBox#compactCombo {{
        min-width: 0px;
    }}
    /* An editable combo's line edit is a real QLineEdit child, so the input
       rule above gives it a second border and a second set of padding
       *inside* the combo — which clips the value on a narrow field. Strip
       it back: the combo already draws the frame. */
    QComboBox QLineEdit {{
        border: none;
        border-radius: 0px;
        padding: 0px;
        background: transparent;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 22px;
        border: none;
        background: transparent;
    }}
    QComboBox::down-arrow {{
        {chevron_down}
        width: 12px;
        height: 12px;
    }}
    QComboBox::down-arrow:on {{
        {chevron_up}
    }}
    QComboBox QAbstractItemView {{
        background: {c['bg_control']};
        color: {c['text_primary']};
        selection-background-color: {c['bg_hover']};
        selection-color: {c['text_primary']};
        border: 1px solid {c['border_strong']};
        border-radius: 12px;
        padding: 4px;
        outline: none;
    }}

    /* ---------- spin boxes -------------------------------------------------- */
    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QDateEdit::up-button, QTimeEdit::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 18px;
        border: none;
        background: transparent;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button,
    QDateEdit::down-button, QTimeEdit::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 18px;
        border: none;
        background: transparent;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
    QDateEdit::up-arrow, QTimeEdit::up-arrow {{
        {chevron_up}
        width: 10px;
        height: 10px;
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow,
    QDateEdit::down-arrow, QTimeEdit::down-arrow {{
        {chevron_down}
        width: 10px;
        height: 10px;
    }}

    /* ---------- check and radio --------------------------------------------- */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {c['text_primary']};
        background: transparent;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {c['border_strong']};
        background: {c['bg_control']};
    }}
    QCheckBox::indicator {{
        border-radius: 4px;
    }}
    QRadioButton::indicator {{
        border-radius: 8px;
    }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {c['accent']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
        {check_on_accent}
    }}
    QCheckBox::indicator:indeterminate {{
        background: {c['bg_control']};
        border-color: {c['accent']};
    }}
    QCheckBox::indicator:checked:disabled {{
        background: {c['bg_hover']};
        border-color: {c['border']};
        {check_muted}
    }}
    QRadioButton::indicator:checked {{
        background: {c['accent']};
        border: 4px solid {c['bg_control']};
    }}

    /* ---------- labels ------------------------------------------------------ */
    QLabel {{
        background: transparent;
    }}
    QLabel[role="hint"] {{
        color: {c['text_tertiary']};
    }}
    QLabel[role="danger"] {{
        color: {c['danger']};
    }}
    QLabel[role="success"] {{
        color: {c['success']};
    }}
    QLabel[role="warning"] {{
        color: {c['warning']};
    }}
    QLabel[role="heading"] {{
        font-size: 14px;
        font-weight: 600;
    }}

    /* ---------- group boxes -------------------------------------------------- */
    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 12px;
        margin-top: 12px;
        padding-top: 12px;
        color: {c['text_secondary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        font-weight: 600;
    }}

    /* ---------- tooltip and menu ---------------------------------------------- */
    QToolTip {{
        background: {c['bg_control']};
        color: {c['text_primary']};
        border: 1px solid {c['border_strong']};
        border-radius: 6px;
        padding: 4px 6px;
    }}
    QMenu {{
        background: {c['bg_control']};
        color: {c['text_primary']};
        border: 1px solid {c['border_strong']};
        border-radius: 12px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background: {c['bg_hover']};
    }}
    QMenu::item:disabled {{
        color: {c['text_tertiary']};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 8px;
    }}

    /* ---------- scroll bars ----------------------------------------------------- */
    /* Qt's default scroll bar is the loudest native-Windows tell after grey
       backgrounds. add-line/sub-line must be zeroed or the stepper arrows
       stay visible. */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['bg_hover']};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['border_strong']};
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['bg_hover']};
        min-width: 24px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['border_strong']};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0;
        height: 0;
        border: none;
        background: transparent;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    /* ---------- splitter --------------------------------------------------------- */
    QSplitter::handle {{
        background: {c['border']};
    }}
    QSplitter::handle:hover {{
        background: {c['accent_soft']};
    }}

    /* ---------- Sidebar (reference/RostaStudioSchedule.jsx's .sidebar) --- */
    QWidget#sidebar {{
        background: {c['bg_surface']};
        border-right: 1px solid {c['border']};
    }}
    QPushButton#sidebarToggle {{
        background: transparent;
        border: none;
        border-radius: 20px;
        font-size: 14px;
        color: {c['text_secondary']};
        padding: 0px;
    }}
    QPushButton#sidebarToggle:hover {{
        background: {c['bg_hover']};
        color: {c['text_primary']};
    }}
    QFrame#sidebarDivider {{
        background: {c['border']};
        border: none;
    }}
    QListWidget#sidebarNav {{
        background: transparent;
        border: none;
        outline: none;
        padding: 4px 12px;
    }}
    QListWidget#sidebarNav::item {{
        height: 42px;
        padding-left: 10px;
        /* Same shape as the Settings category list. Keep the radius under
           half the painted height (42px item - 2px margin): Qt silently
           drops a larger radius and paints square corners. */
        border-radius: 8px;
        margin-bottom: 2px;
        color: {c['text_secondary']};
        font-weight: 500;
    }}
    QListWidget#sidebarNav::item:hover {{
        background: {c['bg_hover']};
        color: {c['text_primary']};
    }}
    QListWidget#sidebarNav::item:selected {{
        background: {c['accent_soft']};
        color: {c['accent']};
        font-weight: 600;
    }}
    QLabel#sidebarWorkspace {{
        font-size: 12px;
        font-weight: 600;
        color: {c['text_primary']};
    }}

    /* ---------- shared bits --------------------------------------------------- */
    /* A plain container QWidget still paints the app canvas color, which
       shows as a dark patch on a card. Containers that sit on a card set
       this property instead of carrying their own background. */
    QWidget[transparentBg="true"] {{
        background: transparent;
    }}
    QLabel[role="title"] {{
        font-size: 16px;
        font-weight: 600;
        padding-left: 8px;
    }}

    /* ---------- Settings (category list + cards) ------------------------------ */
    QWidget#settingsNavPane {{
        background: {c['bg_surface']};
        border-right: 1px solid {c['border']};
    }}
    QListWidget#settingsNav {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget#settingsNav::item {{
        padding-left: 8px;
        border-radius: 8px;
        margin-bottom: 2px;
        color: {c['text_secondary']};
        font-weight: 500;
    }}
    QListWidget#settingsNav::item:hover {{
        background: {c['bg_hover']};
        color: {c['text_primary']};
    }}
    QListWidget#settingsNav::item:selected {{
        background: {c['accent_soft']};
        color: {c['accent']};
        font-weight: 600;
    }}
    QScrollArea#settingsScroll {{
        background: {c['bg_app']};
        border: none;
    }}
    QFrame#settingsCard {{
        background: {c['bg_surface_alt']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }}
    QWidget#settingsFooter {{
        background: {c['bg_surface']};
        border-top: 1px solid {c['border']};
    }}
    /* Dark / Light toggle: the reference's .settings-mode-btn. */
    QPushButton#segmentButton {{
        min-width: 88px;
        padding: 6px 16px;
    }}
    QPushButton#segmentButton:checked {{
        background: {c['accent_soft']};
        border-color: {c['accent']};
        color: {c['accent']};
        font-weight: 600;
    }}
    /* Accent swatch: the fill is set per swatch; the ring lives here. */
    QPushButton#accentSwatch {{
        border: 2px solid transparent;
        border-radius: 14px;
        padding: 0px;
    }}
    QPushButton#accentSwatch:hover {{
        border-color: {c['border_strong']};
    }}
    QPushButton#accentSwatch:checked {{
        border-color: {c['text_primary']};
    }}
    """
