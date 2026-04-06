from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QSpacerItem, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, ColorPickerButton, ComboBox, FluentIcon, IconWidget, InfoBar, InfoBarPosition, LineEdit, PushButton, SingleDirectionScrollArea, StrongBodyLabel, SubtitleLabel, isDarkTheme

from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from config.theme import apply_theme
from core.json_store import JsonStore
from ui.styles.title_style import apply_page_title_style
from ui.widgets.styled_card import StyledCardWidget


class PreferenceRow(QWidget):
    def __init__(self, icon, title: str, description: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.setSpacing(0)

        root.addSpacerItem(QSpacerItem(8, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        self.icon_widget = IconWidget(icon, self)
        self.icon_widget.setFixedSize(20, 20)
        root.addWidget(self.icon_widget)
        root.addSpacerItem(QSpacerItem(28, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        title_label = StrongBodyLabel(title, self)
        desc_label = CaptionLabel(description, self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {'rgba(255, 255, 255, 0.62)' if isDarkTheme() else '#7a7a7a'};")
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        root.addLayout(text_layout, 1)
        root.addWidget(control)


class PreferenceCard(StyledCardWidget):
    def __init__(self, icon, title: str, description: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent, radius=10)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 16, 12)
        layout.addWidget(PreferenceRow(icon, title, description, control, self))


class ShortcutEdit(LineEdit):
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setClearButtonEnabled(False)
        self.setText(text)
        self.setFixedWidth(170)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (16777219, 16777223):  # Backspace / Delete
            self.clear()
            event.accept()
            return

        if key in (
            16777248, 16777249, 16777250, 16777251,
            16777252, 16777253, 16777254, 16777255,
        ):
            event.accept()
            return

        sequence = QKeySequence(event.keyCombination()).toString(QKeySequence.SequenceFormat.PortableText)
        if sequence:
            self.setText(sequence)
        event.accept()


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = APP_SETTINGS_TEMPLATE | self.store.load()
        self.settings["answer_shortcuts"] = APP_SETTINGS_TEMPLATE["answer_shortcuts"] | self.settings.get("answer_shortcuts", {})

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(0)

        self.scroll = SingleDirectionScrollArea(self, Qt.Orientation.Vertical)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.enableTransparentBackground()
        root.addWidget(self.scroll)

        self.content = QWidget(self.scroll)
        self.content.setObjectName("settingsPageContent")
        self.content.setStyleSheet("QWidget#settingsPageContent{background: transparent; border: none;}")
        self.scroll.setWidget(self.content)

        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.page_title = SubtitleLabel("设置", self.content)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)
        layout.addSpacing(18)

        self.title_label = SubtitleLabel("个性化", self.content)
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.DemiBold)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)
        layout.addSpacing(18)

        self.theme_combo = ComboBox(self.content)
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Auto"))
        self.theme_combo.currentTextChanged.connect(self.update_settings)
        self.theme_combo.setFixedWidth(170)

        self.language_combo = ComboBox(self.content)
        self.language_combo.addItems(["跟随系统设置", "zh_CN", "en_US"])
        self.language_combo.setCurrentText(self.settings.get("language", "zh_CN"))
        self.language_combo.currentTextChanged.connect(self.update_settings)
        self.language_combo.setFixedWidth(170)

        self.scale_combo = ComboBox(self.content)
        self.scale_combo.addItems(["跟随系统设置", "100%", "110%", "125%"])
        self.scale_combo.setCurrentText(self.settings.get("ui_scale", "跟随系统设置"))
        self.scale_combo.currentTextChanged.connect(self.update_settings)
        self.scale_combo.setFixedWidth(170)

        shortcuts = self.settings["answer_shortcuts"]
        self.prev_shortcut_edit = ShortcutEdit(shortcuts.get("prev_question", "1"), self.content)
        self.prev_shortcut_edit.editingFinished.connect(self.update_settings)
        self.next_shortcut_edit = ShortcutEdit(shortcuts.get("next_question", "2"), self.content)
        self.next_shortcut_edit.editingFinished.connect(self.update_settings)
        self.mark_shortcut_edit = ShortcutEdit(shortcuts.get("mark_question", "3"), self.content)
        self.mark_shortcut_edit.editingFinished.connect(self.update_settings)

        initial_color = QColor(self.settings.get("theme_color", APP_SETTINGS_TEMPLATE["theme_color"]))
        self.theme_color_control = QWidget(self.content)
        self.theme_color_layout = QHBoxLayout(self.theme_color_control)
        self.theme_color_layout.setContentsMargins(0, 0, 0, 0)
        self.theme_color_layout.setSpacing(8)
        self.reset_theme_color_button = PushButton("重置", self.theme_color_control)
        self.reset_theme_color_button.clicked.connect(self.reset_theme_color)
        self.color_button = ColorPickerButton(initial_color, "选择主题色", self.content)
        self.color_button.colorChanged.connect(self.update_color)
        self.theme_color_layout.addWidget(self.reset_theme_color_button)
        self.theme_color_layout.addWidget(self.color_button)

        layout.addWidget(
            PreferenceCard(
                FluentIcon.BRUSH,
                "应用主题",
                "调整您的应用的外观",
                self.theme_combo,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.PALETTE,
                "主题色",
                "调整您的应用的主题色",
                self.theme_color_control,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.FONT_SIZE,
                "界面缩放",
                "调整少部件和字体的大小",
                self.scale_combo,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.LANGUAGE,
                "语言",
                "选择界面所使用的语言",
                self.language_combo,
                self.content,
            )
        )
        self.shortcut_title = SubtitleLabel("快捷键", self.content)
        shortcut_font = QFont(self.shortcut_title.font())
        shortcut_font.setPointSize(16)
        shortcut_font.setWeight(QFont.Weight.DemiBold)
        self.shortcut_title.setFont(shortcut_font)
        layout.addSpacing(18)
        layout.addWidget(self.shortcut_title)
        layout.addSpacing(18)
        layout.addWidget(
            PreferenceCard(
                FluentIcon.LEFT_ARROW,
                "上一题快捷键",
                "答题界面中触发上一题操作",
                self.prev_shortcut_edit,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.RIGHT_ARROW,
                "下一题快捷键",
                "答题界面中触发下一题操作",
                self.next_shortcut_edit,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.TAG,
                "标记题目快捷键",
                "考试界面中标记或取消标记当前题目",
                self.mark_shortcut_edit,
                self.content,
            )
        )
        layout.addStretch(1)

    def update_settings(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["language"] = self.language_combo.currentText()
        self.settings["ui_scale"] = self.scale_combo.currentText()
        self.settings["answer_shortcuts"] = {
            "prev_question": self.prev_shortcut_edit.text().strip() or APP_SETTINGS_TEMPLATE["answer_shortcuts"]["prev_question"],
            "next_question": self.next_shortcut_edit.text().strip() or APP_SETTINGS_TEMPLATE["answer_shortcuts"]["next_question"],
            "mark_question": self.mark_shortcut_edit.text().strip() or APP_SETTINGS_TEMPLATE["answer_shortcuts"]["mark_question"],
        }
        self.store.save(self.settings)
        apply_theme()

    def update_color(self, color):
        self.settings["theme_color"] = color.name()
        self.store.save(self.settings)
        apply_theme()

    def reset_theme_color(self):
        default_color = QColor(APP_SETTINGS_TEMPLATE["theme_color"])
        self.color_button.setColor(default_color)
        self.update_color(default_color)
        self.show_message("主题色已重置", "重置主题色成功")

    def show_message(self, title: str, content: str) -> None:
        InfoBar.success(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)
