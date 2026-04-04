from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, ColorPickerButton, ComboBox, FluentIcon, IconWidget, StrongBodyLabel, SubtitleLabel

from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from config.theme import apply_theme
from core.json_store import JsonStore
from ui.widgets.styled_card import StyledCardWidget


class PreferenceRow(QWidget):
    def __init__(self, icon, title: str, description: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.setSpacing(12)

        self.icon_widget = IconWidget(icon, self)
        self.icon_widget.setFixedSize(20, 20)
        root.addWidget(self.icon_widget)

        text_layout = QVBoxLayout()
        title_label = StrongBodyLabel(title, self)
        desc_label = CaptionLabel(description, self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7a7a7a;")
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        root.addLayout(text_layout, 1)
        root.addWidget(control)


class PreferenceCard(StyledCardWidget):
    def __init__(self, icon, title: str, description: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent, radius=10)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(PreferenceRow(icon, title, description, control, self))


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = APP_SETTINGS_TEMPLATE | self.store.load()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)

        self.title_label = SubtitleLabel("个性化", self)
        layout.addWidget(self.title_label)

        self.theme_combo = ComboBox(self)
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Auto"))
        self.theme_combo.currentTextChanged.connect(self.update_settings)
        self.theme_combo.setFixedWidth(170)

        self.language_combo = ComboBox(self)
        self.language_combo.addItems(["跟随系统设置", "zh_CN", "en_US"])
        self.language_combo.setCurrentText(self.settings.get("language", "zh_CN"))
        self.language_combo.currentTextChanged.connect(self.update_settings)
        self.language_combo.setFixedWidth(170)

        self.scale_combo = ComboBox(self)
        self.scale_combo.addItems(["跟随系统设置", "100%", "110%", "125%"])
        self.scale_combo.setCurrentText(self.settings.get("ui_scale", "跟随系统设置"))
        self.scale_combo.currentTextChanged.connect(self.update_settings)
        self.scale_combo.setFixedWidth(170)

        initial_color = QColor(self.settings.get("theme_color", APP_SETTINGS_TEMPLATE["theme_color"]))
        self.color_button = ColorPickerButton(initial_color, "选择主题色", self)
        self.color_button.colorChanged.connect(self.update_color)

        layout.addWidget(
            PreferenceCard(
                FluentIcon.BRUSH,
                "应用主题",
                "调整您的应用的外观",
                self.theme_combo,
                self,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.PALETTE,
                "主题色",
                "调整您的应用的主题色",
                self.color_button,
                self,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.FONT_SIZE,
                "界面缩放",
                "调整少部件和字体的大小",
                self.scale_combo,
                self,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.LANGUAGE,
                "语言",
                "选择界面所使用的语言",
                self.language_combo,
                self,
            )
        )
        layout.addStretch(1)

    def update_settings(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["language"] = self.language_combo.currentText()
        self.settings["ui_scale"] = self.scale_combo.currentText()
        self.store.save(self.settings)
        apply_theme()

    def update_color(self, color):
        self.settings["theme_color"] = color.name()
        self.store.save(self.settings)
        apply_theme()
