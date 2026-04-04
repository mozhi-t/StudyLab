from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QComboBox, QFormLayout, QWidget
from qfluentwidgets import ColorPickerButton

from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from config.theme import apply_theme
from core.json_store import JsonStore


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = self.store.load()

        layout = QFormLayout(self)
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Auto"))
        self.theme_combo.currentTextChanged.connect(self.update_settings)

        self.language_combo = QComboBox(self)
        self.language_combo.addItems(["zh_CN", "en_US"])
        self.language_combo.setCurrentText(self.settings.get("language", "zh_CN"))
        self.language_combo.currentTextChanged.connect(self.update_settings)

        initial_color = QColor(self.settings.get("theme_color", APP_SETTINGS_TEMPLATE["theme_color"]))
        self.color_button = ColorPickerButton(initial_color, "选择主题色", self)
        self.color_button.colorChanged.connect(self.update_color)

        layout.addRow("应用主题", self.theme_combo)
        layout.addRow("应用语言", self.language_combo)
        layout.addRow("主题色", self.color_button)

    def update_settings(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["language"] = self.language_combo.currentText()
        self.store.save(self.settings)
        apply_theme()

    def update_color(self, color):
        self.settings["theme_color"] = color.name()
        self.store.save(self.settings)
        apply_theme()
