from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import ColorPickerButton, ComboBox, FluentIcon, GroupHeaderCardWidget

from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from config.theme import apply_theme
from core.json_store import JsonStore


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = self.store.load()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.main_card = GroupHeaderCardWidget("外观与语言", self)

        self.theme_combo = ComboBox(self)
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Auto"))
        self.theme_combo.currentTextChanged.connect(self.update_settings)

        self.language_combo = ComboBox(self)
        self.language_combo.addItems(["zh_CN", "en_US"])
        self.language_combo.setCurrentText(self.settings.get("language", "zh_CN"))
        self.language_combo.currentTextChanged.connect(self.update_settings)

        initial_color = QColor(self.settings.get("theme_color", APP_SETTINGS_TEMPLATE["theme_color"]))
        self.color_button = ColorPickerButton(initial_color, "选择主题色", self)
        self.color_button.colorChanged.connect(self.update_color)

        self.main_card.addGroup(FluentIcon.BRUSH, "应用主题", "切换亮色、暗色或跟随系统。", self._build_setting_control(self.theme_combo))
        self.main_card.addGroup(FluentIcon.LANGUAGE, "应用语言", "当前版本以中文为主，语言选项先做配置预留。", self._build_setting_control(self.language_combo))
        self.main_card.addGroup(FluentIcon.PALETTE, "主题色", "选择 Fluent 主题强调色，保存后立即生效。", self._build_setting_control(self.color_button))
        layout.addWidget(self.main_card)
        layout.addStretch(1)

    def _build_setting_control(self, control: QWidget) -> QWidget:
        wrapper = QWidget(self)
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(control)
        return wrapper

    def update_settings(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["language"] = self.language_combo.currentText()
        self.store.save(self.settings)
        apply_theme()

    def update_color(self, color):
        self.settings["theme_color"] = color.name()
        self.store.save(self.settings)
        apply_theme()
