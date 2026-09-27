"""Left sidebar navigation — replaces the old top QTabWidget tabs.

Visual reference: reference/RostaStudioSchedule.jsx's `Sidebar` component
and its `.sidebar`/`.sidebar-item` CSS — porting that look is now in scope
(see CLAUDE.md, "Reference material"), not its React code. Same numbers as
that CSS: 64px collapsed / 226px expanded, 42px items with 8px rounded corners (same as the Settings category list), a
bordered-off bottom group for Settings (the reference's About/Guide aren't
built yet, so the bottom group here is just Settings for now).

The reference's per-nav-item icon recoloring on ``is-active`` (icon and
label both turn accent-colored) isn't replicated — Qt would need a custom
item delegate for that; the pill background + accent-colored *label* text
(via QSS `::item:selected`) already reads clearly as "selected" without it.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons

COLLAPSED_WIDTH = 64
EXPANDED_WIDTH = 226
ITEM_HEIGHT = 42

# (key, icon name, label) — key order here is also the QStackedWidget page
# order MainWindow builds, so NAV_ITEMS is the one place that mapping lives.
# "Schedule" hosts the Year/Month/Custom/Day scale switcher (see
# schedule_calendar_panel.py) — Custom view and Day view moved inside it, so
# they're no longer separate top-level items. "Assignments" is the older
# flat list (still useful as a raw audit view / rule-engine demo).
MAIN_NAV_ITEMS = [
    ("staff", "staff", "Team"),  # nav key stays "staff" (MainWindow's page-order key); only the label changed
    ("templates", "templates", "Templates"),
    ("schedule", "schedule", "Schedule"),
]
# The old flat "Assignments" audit list is deliberately not in the nav —
# the user's plan is a dedicated Assignments Log later, with its own logic;
# `SchedulePanel` (schedule_panel.py) still exists and is still tested, just
# not mounted anywhere right now.
BOTTOM_NAV_ITEMS = [
    ("settings", "settings", "Settings"),
]
NAV_ITEMS = MAIN_NAV_ITEMS + BOTTOM_NAV_ITEMS
_NAV_TIPS = {
    "staff": "Team: employees, archive and availability",
    "templates": "Templates: day plans and their shift timings",
    "schedule": "Schedule: year, month, custom range and day rotation",
    "settings": "Settings: workspace, appearance, lists and rules",
}


def _build_list(items: list[tuple[str, str, str]], icon_color: str) -> QListWidget:
    lst = QListWidget()
    lst.setObjectName("sidebarNav")
    lst.setIconSize(QSize(20, 20))
    lst.setFocusPolicy(Qt.NoFocus)
    lst.setFrameShape(QListWidget.NoFrame)
    lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    lst.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    for key, icon_name, label in items:
        item = QListWidgetItem(icons.icon(icon_name, icon_color), label)
        item.setData(Qt.UserRole, key)
        item.setToolTip(_NAV_TIPS.get(key, label))
        item.setSizeHint(QSize(0, ITEM_HEIGHT))
        lst.addItem(item)
    return lst


class Sidebar(QWidget):
    page_selected = Signal(str)  # emits the nav item key

    def __init__(self, icon_color: str, workspace_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._expanded = True

        self._toggle_button = QPushButton("☰")  # hamburger glyph
        self._toggle_button.setObjectName("sidebarToggle")
        self._toggle_button.setFixedSize(40, 40)
        self._toggle_button.setCursor(Qt.PointingHandCursor)
        self._toggle_button.setToolTip("Collapse sidebar")
        self._toggle_button.clicked.connect(self._toggle)

        self.main_list = _build_list(MAIN_NAV_ITEMS, icon_color)
        self.bottom_list = _build_list(BOTTOM_NAV_ITEMS, icon_color)
        # Exactly as tall as its items. Left to its default size hint, the
        # list is ~200px tall with Settings at its top, so Settings floated
        # mid-way up the sidebar and moved whenever the window was resized.
        # 2px item margin + 4px list padding top and bottom, per theme.py.
        self.bottom_list.setFixedHeight(len(BOTTOM_NAV_ITEMS) * (ITEM_HEIGHT + 2) + 8)
        # Only one of the two lists ever has a selection — clicking in one
        # clears the other, so there's a single visible "active" item across
        # both groups, same as the reference's single `activeItem` value.
        self.main_list.currentRowChanged.connect(lambda row: self._on_selected(self.main_list, self.bottom_list, row))
        self.bottom_list.currentRowChanged.connect(lambda row: self._on_selected(self.bottom_list, self.main_list, row))

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFixedHeight(1)

        # The reference's `.profile-workspace`: which schedule this is.
        self._workspace_label = QLabel(workspace_name)
        self._workspace_label.setObjectName("sidebarWorkspace")

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(12, 12, 12, 8)
        toggle_row.setSpacing(8)
        toggle_row.addWidget(self._toggle_button)
        toggle_row.addWidget(self._workspace_label)
        toggle_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)
        layout.addLayout(toggle_row)
        layout.addWidget(self.main_list, stretch=1)
        layout.addWidget(divider)
        layout.addWidget(self.bottom_list)

        self.setFixedWidth(EXPANDED_WIDTH)
        self.main_list.setCurrentRow(0)

    def set_workspace_name(self, name: str) -> None:
        self._workspace_label.setText(name)

    def select(self, key: str) -> None:
        """Select the nav item for `key`, exactly as a click would."""
        for lst, items in ((self.main_list, MAIN_NAV_ITEMS), (self.bottom_list, BOTTOM_NAV_ITEMS)):
            keys = [item_key for item_key, _, _ in items]
            if key in keys:
                lst.setCurrentRow(keys.index(key))
                return

    def _on_selected(self, active_list: QListWidget, other_list: QListWidget, row: int) -> None:
        if row < 0:
            return
        other_list.blockSignals(True)
        other_list.setCurrentRow(-1)
        other_list.blockSignals(False)
        key = active_list.item(row).data(Qt.UserRole)
        self.page_selected.emit(key)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        for lst, items in ((self.main_list, MAIN_NAV_ITEMS), (self.bottom_list, BOTTOM_NAV_ITEMS)):
            for i, (_, _, label) in enumerate(items):
                lst.item(i).setText(label if self._expanded else "")
        self._workspace_label.setVisible(self._expanded)
        self.setFixedWidth(EXPANDED_WIDTH if self._expanded else COLLAPSED_WIDTH)
        self._toggle_button.setToolTip("Collapse sidebar" if self._expanded else "Expand sidebar")
