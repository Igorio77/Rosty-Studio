"""Settings page, laid out like a desktop mail client's settings: a
category list on the left, the chosen category's cards on the right.

Categories:

* General        — workspace name and the department it plans.
* Appearance     — dark/light mode and the accent color (the reference's
                   Appearance section, reference/RostaStudioSchedule.jsx).
* Lists          — Department / Subdepartment / Position lists and the
                   Location code catalog (`list_control_panel.py`).
* Rules          — one card per rule, built entirely from each Rule's
                   `param_schema` (CLAUDE.md: "the settings UI builds its
                   form automatically from that schema"). Adding a rule
                   under rules/builtin/ makes it appear here with zero
                   changes to this file.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from rostify.rules.base import ParamField, Rule, Severity
from rostify.rules.engine import RuleEngine
from rostify.services.app_settings import ACCENTS, AppSettings, save_app_settings
from rostify.services.config import save_rules_config
from rostify.services.persistence import Repository

from .. import icons
from ..theme import ACCENT_THEMES, COLORS, accent_swatch
from .list_control_panel import ListControlPanel
from .widgets import SettingsCard

# Width of the readable column on the right. Wider than this and a label
# ends up a screen away from its field.
_CONTENT_MAX_WIDTH = 760
_NAV_WIDTH = 220
_NAV_ITEM_HEIGHT = 36
_SWATCH_SIZE = 28
_CATEGORY_TIPS = {
    "general": "Workspace name and department",
    "appearance": "Dark or light mode and the accent color",
    "lists": "Departments, subdepartments, positions and location codes",
    "rules": "Scheduling rules: switch on/off, hard or soft, their settings",
}


def _make_param_widget(field: ParamField, value):
    if field.type == "int":
        widget = QSpinBox()
        widget.setRange(int(field.min_value or 0), int(field.max_value or 1_000_000))
        widget.setValue(int(value))
        return widget, lambda: widget.value()
    if field.type == "float":
        widget = QDoubleSpinBox()
        widget.setRange(float(field.min_value or 0), float(field.max_value or 1_000_000))
        widget.setValue(float(value))
        return widget, lambda: widget.value()
    if field.type == "bool":
        widget = QCheckBox()
        widget.setChecked(bool(value))
        return widget, lambda: widget.isChecked()
    if field.type == "choice":
        widget = QComboBox()
        widget.addItems(field.choices)
        if value in field.choices:
            widget.setCurrentText(str(value))
        return widget, lambda: widget.currentText()
    # default: "str"
    widget = QLineEdit(str(value))
    return widget, lambda: widget.text()


def _changed_signal(widget: QWidget):
    """The "value edited" signal for any widget `_make_param_widget` builds."""
    for name in ("valueChanged", "toggled", "currentTextChanged", "textChanged"):
        signal = getattr(widget, name, None)
        if signal is not None:
            return signal
    return None


def _page(*cards: QWidget) -> QScrollArea:
    """A scrollable column of cards, capped at a readable width and pinned
    to the top-left like every other settings pane."""
    column = QWidget()
    column.setMaximumWidth(_CONTENT_MAX_WIDTH)
    column_layout = QVBoxLayout(column)
    column_layout.setContentsMargins(0, 0, 0, 0)
    column_layout.setSpacing(12)
    for card in cards:
        column_layout.addWidget(card)
    column_layout.addStretch(1)

    holder = QWidget()
    holder_layout = QHBoxLayout(holder)
    holder_layout.setContentsMargins(24, 16, 24, 24)
    holder_layout.addWidget(column, stretch=1)
    holder_layout.addStretch(0)

    scroll = QScrollArea()
    scroll.setObjectName("settingsScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(holder)
    return scroll


class RuleCard(SettingsCard):
    """One rule: name, on/off and hard/soft in the header, its description,
    then its own parameters. Parameters grey out while the rule is off."""

    edited = Signal()

    def __init__(self, rule: Rule, parent: QWidget | None = None) -> None:
        super().__init__(rule.name, rule.description, parent)
        self._rule = rule

        self._severity_combo = QComboBox()
        self._severity_combo.setObjectName("compactCombo")
        for severity in Severity:
            self._severity_combo.addItem(severity.value.capitalize(), severity.value)
        self._severity_combo.setCurrentIndex(self._severity_combo.findData(rule.severity.value))
        self._severity_combo.setToolTip("Hard blocks the change. Soft only warns.")

        self._enabled_check = QCheckBox("On")
        self._enabled_check.setChecked(rule.enabled)
        self._enabled_check.setToolTip("Turn this rule on or off")

        self.add_header_widget(self._severity_combo)
        self.add_header_widget(self._enabled_check)

        self._param_getters: dict[str, Callable] = {}
        self._params = QWidget()
        self._params.setProperty("transparentBg", True)
        form = QFormLayout(self._params)
        form.setContentsMargins(0, 4, 0, 0)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        for param_field in rule.param_schema:
            widget, getter = _make_param_widget(param_field, rule.params[param_field.name])
            widget.setMinimumWidth(200)
            if param_field.help_text:
                widget.setToolTip(param_field.help_text)
            form.addRow(param_field.label, widget)
            self._param_getters[param_field.name] = getter
            signal = _changed_signal(widget)
            if signal is not None:
                signal.connect(self.edited.emit)
        if rule.param_schema:
            self.body.addWidget(self._params)

        self._enabled_check.toggled.connect(self._params.setEnabled)
        self._enabled_check.toggled.connect(self.edited.emit)
        self._severity_combo.currentIndexChanged.connect(self.edited.emit)
        self._params.setEnabled(rule.enabled)

    def apply_to_rule(self) -> None:
        """Write the card's current values back onto the underlying Rule
        instance (mutated in place, so the RuleEngine that already holds
        this instance picks the change up immediately).
        """
        self._rule.enabled = self._enabled_check.isChecked()
        self._rule.severity = Severity(self._severity_combo.currentData())
        for name, getter in self._param_getters.items():
            self._rule.params[name] = getter()

    def to_config_entry(self) -> dict:
        return {
            "id": self._rule.id,
            "enabled": self._rule.enabled,
            "severity": self._rule.severity.value,
            "params": dict(self._rule.params),
        }


class SettingsPanel(QWidget):
    #: New (theme_mode, accent) picked. The owner rebuilds the window with it.
    appearance_changed = Signal(str, str)
    #: Workspace name edited and saved.
    workspace_changed = Signal(str)
    #: A different department picked. The owner rebuilds the pages for it.
    department_changed = Signal(str)

    CATEGORIES = [
        ("general", "general", "General"),
        ("appearance", "palette", "Appearance"),
        ("lists", "list", "Lists"),
        ("rules", "shield", "Rules"),
    ]

    def __init__(
        self,
        rule_engine: RuleEngine,
        config_path: str | Path,
        repository: Repository,
        app_settings: AppSettings | None = None,
        app_settings_path: str | Path | None = None,
        on_location_codes_change: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rule_engine = rule_engine
        self._config_path = config_path
        self._app_settings = app_settings or AppSettings()
        self._app_settings_path = app_settings_path
        self._rule_cards: list[RuleCard] = []
        self._repository = repository

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_general_page())
        self.pages.addWidget(self._build_appearance_page())
        self.lists = ListControlPanel(repository, on_location_codes_change=on_location_codes_change)
        self.pages.addWidget(_page(self.lists))
        self.pages.addWidget(self._build_rules_page())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_nav())
        layout.addWidget(self.pages, stretch=1)

    # --- navigation ------------------------------------------------------

    def _build_nav(self) -> QWidget:
        pane = QWidget()
        pane.setObjectName("settingsNavPane")
        pane.setFixedWidth(_NAV_WIDTH)

        title = QLabel("Settings")
        title.setProperty("role", "title")

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setFocusPolicy(Qt.NoFocus)
        self.nav.setFrameShape(QFrame.NoFrame)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for key, icon_name, label in self.CATEGORIES:
            item = QListWidgetItem(icons.icon(icon_name, COLORS["text_secondary"], 18), label)
            item.setData(Qt.UserRole, key)
            item.setToolTip(_CATEGORY_TIPS.get(key, ""))
            item.setSizeHint(QSize(0, _NAV_ITEM_HEIGHT))
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)

        layout = QVBoxLayout(pane)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self.nav, stretch=1)
        return pane

    def select_category(self, key: str) -> None:
        keys = [k for k, _, _ in self.CATEGORIES]
        if key in keys:
            self.nav.setCurrentRow(keys.index(key))

    def current_category(self) -> str:
        return self.CATEGORIES[max(self.nav.currentRow(), 0)][0]

    # --- General -----------------------------------------------------------

    def _build_general_page(self) -> QWidget:
        card = SettingsCard("Workspace", "The name of this schedule, shown in the sidebar and the window title.")
        self._workspace_edit = QLineEdit(self._app_settings.workspace_name)
        self._workspace_edit.setMaximumWidth(320)
        self._workspace_edit.setPlaceholderText("e.g. the ship or casino name")
        self._workspace_edit.editingFinished.connect(self._save_workspace)
        card.body.addWidget(self._workspace_edit)

        department_card = SettingsCard(
            "Department",
            "Which department this workspace plans. Team, Templates and Schedule show only its "
            "subdepartments and employees. Departments are added in Lists.",
        )
        self._department_combo = QComboBox()
        self._department_combo.setToolTip("The department every page works with")
        self._department_combo.addItems(self._repository.load_departments())
        self._department_combo.setCurrentText(self._app_settings.department)
        self._department_combo.setMaximumWidth(320)
        self._department_combo.activated.connect(lambda _: self._save_department())
        department_card.body.addWidget(self._department_combo)
        return _page(card, department_card)

    def _save_department(self) -> None:
        name = self._department_combo.currentText()
        if not name or name == self._app_settings.department:
            return
        self._app_settings.department = name
        self._persist_app_settings()
        self.department_changed.emit(name)

    def _save_workspace(self) -> None:
        name = self._workspace_edit.text().strip()
        if not name or name == self._app_settings.workspace_name:
            self._workspace_edit.setText(self._app_settings.workspace_name)
            return
        self._app_settings.workspace_name = name
        self._persist_app_settings()
        self.workspace_changed.emit(name)

    # --- Appearance ----------------------------------------------------------

    def _build_appearance_page(self) -> QWidget:
        mode_card = SettingsCard("Mode", "Dark is easier on the eyes on a dim casino floor. Light prints closer to paper.")
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self._mode_group = QButtonGroup(self)
        for mode, label in (("dark", "Dark"), ("light", "Light")):
            button = QPushButton(label)
            button.setObjectName("segmentButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setChecked(mode == self._app_settings.theme_mode)
            button.setProperty("mode", mode)
            self._mode_group.addButton(button)
            mode_row.addWidget(button)
        mode_row.addStretch(1)
        mode_card.body.addLayout(mode_row)
        self._mode_group.buttonClicked.connect(
            lambda button: self._set_appearance(button.property("mode"), self._app_settings.accent)
        )

        accent_card = SettingsCard("Accent color", "Used for the selected item, focus rings and the main button.")
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(12)
        mode = self._app_settings.theme_mode
        for accent in ACCENTS:
            swatch = QPushButton()
            swatch.setObjectName("accentSwatch")
            swatch.setCheckable(True)
            swatch.setChecked(accent == self._app_settings.accent)
            swatch.setFixedSize(_SWATCH_SIZE, _SWATCH_SIZE)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.setToolTip(ACCENT_THEMES[accent]["name"])
            # The fill is per-swatch data, so it can't live in the global
            # sheet; the ring and radius do (QPushButton#accentSwatch).
            swatch.setStyleSheet(f"QPushButton#accentSwatch {{ background: {accent_swatch(accent, mode)}; }}")
            swatch.clicked.connect(lambda _checked=False, a=accent: self._set_appearance(self._app_settings.theme_mode, a))
            swatch_row.addWidget(swatch)
        swatch_row.addStretch(1)
        accent_card.body.addLayout(swatch_row)

        return _page(mode_card, accent_card)

    def _set_appearance(self, mode: str, accent: str) -> None:
        if (mode, accent) == (self._app_settings.theme_mode, self._app_settings.accent):
            return
        self._app_settings.theme_mode = mode
        self._app_settings.accent = accent
        self._persist_app_settings()
        self.appearance_changed.emit(mode, accent)

    def _persist_app_settings(self) -> None:
        if self._app_settings_path is not None:
            save_app_settings(self._app_settings_path, self._app_settings)

    # --- Rules -------------------------------------------------------------------

    def _build_rules_page(self) -> QWidget:
        intro = QLabel(
            "Checks run every time the schedule changes. Hard rules block the change; soft rules only warn."
        )
        intro.setWordWrap(True)
        intro.setProperty("role", "hint")

        cards: list[QWidget] = [intro]
        for rule in self._rule_engine.rules:
            card = RuleCard(rule)
            card.edited.connect(self._mark_rules_dirty)
            self._rule_cards.append(card)
            cards.append(card)

        self._save_button = QPushButton("Save")
        self._save_button.setObjectName("primary")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._save_rules)

        self._status_label = QLabel("")
        self._status_label.setProperty("role", "hint")

        footer = QWidget()
        footer.setObjectName("settingsFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 12, 24, 12)
        footer_layout.addWidget(self._status_label, stretch=1)
        footer_layout.addWidget(self._save_button)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(_page(*cards), stretch=1)
        layout.addWidget(footer)
        return page

    def _mark_rules_dirty(self) -> None:
        self._save_button.setEnabled(True)
        self._status_label.setText("Unsaved changes")

    def _save_rules(self) -> None:
        entries = []
        for card in self._rule_cards:
            card.apply_to_rule()
            entries.append(card.to_config_entry())
        save_rules_config(self._config_path, entries)
        self._save_button.setEnabled(False)
        self._status_label.setText("Saved")
