"""Settings tab: rule configuration forms built entirely from each Rule's
`param_schema` (CLAUDE.md: "the settings UI builds its form automatically
from that schema"). Adding a new rule under rules/builtin/ makes it appear
here with zero changes to this file.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from rostify.rules.base import ParamField, Rule, Severity
from rostify.rules.engine import RuleEngine
from rostify.services.config import save_rules_config
from rostify.services.persistence import Repository

from .list_control_panel import ListControlPanel


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


class RuleGroupBox(QGroupBox):
    """One rule's editable form: enabled + severity + its own params."""

    def __init__(self, rule: Rule, parent: QWidget | None = None) -> None:
        super().__init__(rule.name, parent)
        self._rule = rule

        form = QFormLayout()

        self._enabled_check = QCheckBox()
        self._enabled_check.setChecked(rule.enabled)
        form.addRow("Enabled", self._enabled_check)

        self._severity_combo = QComboBox()
        self._severity_combo.addItems([s.value for s in Severity])
        self._severity_combo.setCurrentText(rule.severity.value)
        form.addRow("Severity", self._severity_combo)

        if rule.description:
            desc = QLabel(rule.description)
            desc.setWordWrap(True)
            desc.setProperty("role", "hint")
            form.addRow(desc)

        self._param_getters: dict[str, callable] = {}
        for param_field in rule.param_schema:
            widget, getter = _make_param_widget(param_field, rule.params[param_field.name])
            if param_field.help_text:
                widget.setToolTip(param_field.help_text)
            form.addRow(param_field.label, widget)
            self._param_getters[param_field.name] = getter

        self.setLayout(form)

    def apply_to_rule(self) -> None:
        """Write the form's current values back onto the underlying Rule
        instance (mutated in place, so the RuleEngine that already holds
        this instance picks the change up immediately).
        """
        self._rule.enabled = self._enabled_check.isChecked()
        self._rule.severity = Severity(self._severity_combo.currentText())
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
    """Two sub-tabs: **Rules** (unchanged rule-config forms) and
    **List Control** (admin-managed Department/Subdepartment/Position lists
    that Staff and Templates dropdowns read from — see `list_control_panel.py`).
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        config_path: str | Path,
        repository: Repository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rule_engine = rule_engine
        self._config_path = config_path
        self._rule_boxes: list[RuleGroupBox] = []

        tabs = QTabWidget()
        tabs.addTab(self._build_rules_tab(rule_engine), "Rules")
        tabs.addTab(ListControlPanel(repository), "List Control")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

    def _build_rules_tab(self, rule_engine: RuleEngine) -> QWidget:
        content = QWidget()
        content_layout = QVBoxLayout(content)
        for rule in rule_engine.rules:
            box = RuleGroupBox(rule)
            self._rule_boxes.append(box)
            content_layout.addWidget(box)
        content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        save_button = QPushButton("Save rule settings")
        save_button.setObjectName("primary")
        save_button.clicked.connect(self._save)

        self._status_label = QLabel("")
        self._status_label.setProperty("role", "hint")

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(scroll)
        layout.addWidget(save_button)
        layout.addWidget(self._status_label)
        return tab

    def _save(self) -> None:
        entries = []
        for box in self._rule_boxes:
            box.apply_to_rule()
            entries.append(box.to_config_entry())
        save_rules_config(self._config_path, entries)
        self._status_label.setText(f"Saved to {self._config_path}")
