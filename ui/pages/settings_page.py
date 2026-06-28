from __future__ import annotations

import sys

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QSpacerItem, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, ColorPickerButton, ComboBox, FluentIcon, IconWidget, InfoBar, InfoBarPosition, MessageBox, MessageBoxBase, PushButton, SingleDirectionScrollArea, SpinBox, StateToolTip, StrongBodyLabel, SubtitleLabel, SwitchButton, isDarkTheme

from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from config.theme import apply_theme
from core.index_checker import GlobalIndexChecker
from core.json_store import JsonStore
from ui.styles.title_style import apply_page_title_style
from ui.widgets.invalid_bank_time_dialog import InvalidBankTimeDialog
from ui.widgets.eye_care_dialog import CustomIntervalDialog
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


# Keys that are not a valid shortcut on their own: modifiers, lock keys, etc.
_IGNORED_KEYS = {
    Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
    Qt.Key.Key_AltGr, Qt.Key.Key_CapsLock, Qt.Key.Key_NumLock, Qt.Key.Key_ScrollLock,
    Qt.Key.Key_Mode_switch,
}


class ShortcutCaptureDialog(MessageBoxBase):
    """Dialog that captures a keyboard shortcut from the next pressed key."""

    def __init__(self, current: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._captured = current

        self.titleLabel = SubtitleLabel("请键入快捷键", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.hint_label = BodyLabel(current or "按下任意键以设置快捷键", self)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewLayout.addWidget(self.hint_label)

        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(320)

    @property
    def captured(self) -> str:
        return self._captured

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self._captured = ""
            self.hint_label.setText("按下任意键以设置快捷键")
            event.accept()
            return

        if key in _IGNORED_KEYS or key == Qt.Key.Key_unknown:
            event.accept()
            return

        sequence = QKeySequence(event.keyCombination()).toString(QKeySequence.SequenceFormat.PortableText)
        if sequence:
            self._captured = sequence
            self.hint_label.setText(sequence)
        event.accept()


class ShortcutButton(PushButton):
    """A button whose label reflects the current shortcut; clicking opens a capture dialog."""

    changed = pyqtSignal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._value = value
        self.setFixedWidth(90)
        self.clicked.connect(self._on_clicked)
        self._refresh_label()

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        self._value = value
        self._refresh_label()

    def _on_clicked(self) -> None:
        dialog = ShortcutCaptureDialog(self._value, self.window())
        if dialog.exec() and dialog.captured and dialog.captured != self._value:
            self._value = dialog.captured
            self._refresh_label()
            self.changed.emit(self._value)

    def _refresh_label(self) -> None:
        self.setText(self._value or "未设置")


class IndexCheckThread(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, checker: GlobalIndexChecker):
        super().__init__()
        self.checker = checker

    def run(self):
        try:
            self.completed.emit(self.checker.check_and_repair())
        except Exception as exc:
            self.failed.emit(str(exc))


class SettingsPage(QWidget):
    eye_care_changed = pyqtSignal()

    def __init__(self, question_index_manager=None, wrong_manager=None, favorite_manager=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = APP_SETTINGS_TEMPLATE | self.store.load()
        self.settings["answer_shortcuts"] = APP_SETTINGS_TEMPLATE["answer_shortcuts"] | self.settings.get("answer_shortcuts", {})
        self.settings["eye_care"] = APP_SETTINGS_TEMPLATE["eye_care"] | self.settings.get("eye_care", {})
        self.question_index_manager = question_index_manager
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.index_checker = GlobalIndexChecker()
        self.index_check_thread: IndexCheckThread | None = None
        self.state_tooltip: StateToolTip | None = None

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
        self.scale_combo.currentTextChanged.connect(self.update_scale)
        self.scale_combo.setFixedWidth(170)

        shortcuts = self.settings["answer_shortcuts"]
        self.prev_shortcut_button = ShortcutButton(shortcuts.get("prev_question", "1"), self.content)
        self.prev_shortcut_button.changed.connect(lambda v: self.save_shortcut("prev_question", "上一题快捷键", v))
        self.prev_shortcut_control = self._wrap_shortcut_control(self.prev_shortcut_button, "prev_question")
        self.next_shortcut_button = ShortcutButton(shortcuts.get("next_question", "2"), self.content)
        self.next_shortcut_button.changed.connect(lambda v: self.save_shortcut("next_question", "下一题快捷键", v))
        self.next_shortcut_control = self._wrap_shortcut_control(self.next_shortcut_button, "next_question")
        self.mark_shortcut_button = ShortcutButton(shortcuts.get("mark_question", "3"), self.content)
        self.mark_shortcut_button.changed.connect(lambda v: self.save_shortcut("mark_question", "标记题目快捷键", v))
        self.mark_shortcut_control = self._wrap_shortcut_control(self.mark_shortcut_button, "mark_question")

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
                self.prev_shortcut_control,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.RIGHT_ARROW,
                "下一题快捷键",
                "答题界面中触发下一题操作",
                self.next_shortcut_control,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.TAG,
                "标记题目快捷键",
                "考试界面中标记或取消标记当前题目",
                self.mark_shortcut_control,
                self.content,
            )
        )
        # ===== 休息提醒 =====
        eye_care = self.settings["eye_care"]

        self.eye_care_switch = SwitchButton(self.content)
        self.eye_care_switch.setOnText("")
        self.eye_care_switch.setOffText("")
        self.eye_care_switch.setChecked(bool(eye_care.get("enabled", True)))
        self.eye_care_switch.checkedChanged.connect(self._on_eye_care_enabled_changed)

        self.eye_care_interval_combo = ComboBox(self.content)
        self._eye_care_presets = ["20", "30", "40", "50", "60"]
        self.eye_care_interval_combo.addItems([f"{m} 分钟" for m in self._eye_care_presets])
        self.eye_care_interval_combo.addItem("自定义...")
        self._refresh_eye_care_interval_text(int(eye_care.get("interval_minutes", 20)))
        self.eye_care_interval_combo.setFixedWidth(170)
        self.eye_care_interval_combo.activated.connect(self._on_eye_care_interval_changed)

        self.eye_care_mode_combo = ComboBox(self.content)
        self.eye_care_mode_combo.addItem("弹窗", userData="dialog")
        self.eye_care_mode_combo.addItem("顶部通知", userData="infobar")
        mode_index = 0 if eye_care.get("reminder_mode", "dialog") == "dialog" else 1
        self.eye_care_mode_combo.setCurrentIndex(mode_index)
        self.eye_care_mode_combo.setFixedWidth(170)
        self.eye_care_mode_combo.currentIndexChanged.connect(self._on_eye_care_mode_changed)
        self._refresh_eye_care_controls_enabled()

        self.eye_care_title = SubtitleLabel("休息提醒", self.content)
        eye_care_font = QFont(self.eye_care_title.font())
        eye_care_font.setPointSize(16)
        eye_care_font.setWeight(QFont.Weight.DemiBold)
        self.eye_care_title.setFont(eye_care_font)
        layout.addSpacing(18)
        layout.addWidget(self.eye_care_title)
        layout.addSpacing(18)
        layout.addWidget(
            PreferenceCard(
                FluentIcon.CAFE,
                "休息提醒",
                "间隔提醒您远眺放松眼睛",
                self.eye_care_switch,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.DATE_TIME,
                "提醒间隔",
                "设置多久提醒一次",
                self.eye_care_interval_combo,
                self.content,
            )
        )
        layout.addWidget(
            PreferenceCard(
                FluentIcon.MESSAGE,
                "提醒方式",
                "选择提醒以何种形式出现",
                self.eye_care_mode_combo,
                self.content,
            )
        )

        self.advanced_title = SubtitleLabel("高级", self.content)
        advanced_font = QFont(self.advanced_title.font())
        advanced_font.setPointSize(16)
        advanced_font.setWeight(QFont.Weight.DemiBold)
        self.advanced_title.setFont(advanced_font)
        layout.addSpacing(18)
        layout.addWidget(self.advanced_title)
        layout.addSpacing(18)

        self.index_check_button = PushButton("检查索引", self.content)
        self.index_check_button.clicked.connect(self.show_index_check_dialog)
        layout.addWidget(
            PreferenceCard(
                FluentIcon.SYNC,
                "全局索引检查",
                "检查并尝试修复题库、错题本、收藏夹的索引文件，仅当数据出现问题时使用",
                self.index_check_button,
                self.content,
            )
        )
        layout.addStretch(1)

    def _refresh_eye_care_interval_text(self, minutes: int) -> None:
        """根据存储的分钟数，把间隔 ComboBox 的显示文本对到正确项。"""
        combo = self.eye_care_interval_combo
        combo.blockSignals(True)
        custom_index = combo.count() - 1
        if str(minutes) in self._eye_care_presets:
            combo.setItemText(custom_index, "自定义...")
            combo.setCurrentText(f"{minutes} 分钟")
        else:
            combo.setItemText(custom_index, f"{minutes} 分钟 (自定义)")
            combo.setCurrentIndex(custom_index)
        combo.blockSignals(False)

    def _on_eye_care_enabled_changed(self, checked: bool) -> None:
        self.settings["eye_care"]["enabled"] = bool(checked)
        self.store.save(self.settings)
        self._refresh_eye_care_controls_enabled()
        self.eye_care_changed.emit()

    def _refresh_eye_care_controls_enabled(self) -> None:
        enabled = bool(self.eye_care_switch.isChecked())
        self.eye_care_interval_combo.setEnabled(enabled)
        self.eye_care_mode_combo.setEnabled(enabled)

    def _on_eye_care_interval_changed(self, index: int) -> None:
        combo = self.eye_care_interval_combo
        is_custom_item = index == combo.count() - 1
        if is_custom_item:
            current = int(self.settings["eye_care"].get("interval_minutes", 20))
            dialog = CustomIntervalDialog(current, self.window())
            if dialog.exec():
                minutes = dialog.value
                self.settings["eye_care"]["interval_minutes"] = minutes
                self.store.save(self.settings)
                self._refresh_eye_care_interval_text(minutes)
                self.eye_care_changed.emit()
            else:
                # 用户取消，恢复到上次保存的显示
                self._refresh_eye_care_interval_text(int(self.settings["eye_care"].get("interval_minutes", 20)))
        else:
            # 形如 "20 分钟"
            text = combo.itemText(index)
            try:
                minutes = int(text.split()[0])
            except (ValueError, IndexError):
                minutes = 20
            self.settings["eye_care"]["interval_minutes"] = minutes
            self.store.save(self.settings)
            self.eye_care_changed.emit()

    def _on_eye_care_mode_changed(self, _index: int) -> None:
        self.settings["eye_care"]["reminder_mode"] = self.eye_care_mode_combo.currentData()
        self.store.save(self.settings)
        self.eye_care_changed.emit()

    def update_settings(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["language"] = self.language_combo.currentText()
        self.store.save(self.settings)
        apply_theme()

    def save_shortcut(self, key: str, label: str, value: str) -> None:
        self._persist_shortcut(
            key, value,
            success_message=(None, f"{label}已设置为 {value}"),
        )

    def reset_shortcut(self, key: str, label: str) -> None:
        default_value = APP_SETTINGS_TEMPLATE["answer_shortcuts"][key]
        button_map = {
            "prev_question": self.prev_shortcut_button,
            "next_question": self.next_shortcut_button,
            "mark_question": self.mark_shortcut_button,
        }
        button_map[key].value = default_value
        self._persist_shortcut(
            key, default_value,
            success_message=("已重置", ""),
            failure_title="重置失败",
        )

    def _persist_shortcut(
        self,
        key: str,
        value: str,
        success_message: tuple[str | None, str | None] = (None, None),
        failure_title: str = "快捷键冲突",
    ) -> None:
        button_map = {
            "prev_question": self.prev_shortcut_button,
            "next_question": self.next_shortcut_button,
            "mark_question": self.mark_shortcut_button,
        }
        label_map = {
            "prev_question": "上一题快捷键",
            "next_question": "下一题快捷键",
            "mark_question": "标记题目快捷键",
        }
        for other_key, other_button in button_map.items():
            if other_key == key:
                continue
            if other_button.value == value:
                self.show_error_message(
                    failure_title,
                    f"该快捷键已被「{label_map[other_key]}」占用",
                )
                button_map[key].value = self.settings["answer_shortcuts"].get(key, APP_SETTINGS_TEMPLATE["answer_shortcuts"][key])
                return

        self.settings["answer_shortcuts"][key] = value
        self.store.save(self.settings)
        title, content = success_message
        if title:
            self.show_message(title, content or "")

    def _wrap_shortcut_control(self, button: ShortcutButton, key: str) -> QWidget:
        label_map = {
            "prev_question": "上一题快捷键",
            "next_question": "下一题快捷键",
            "mark_question": "标记题目快捷键",
        }
        control = QWidget(self.content)
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        reset_button = PushButton("重置", control)
        reset_button.clicked.connect(lambda: self.reset_shortcut(key, label_map[key]))
        layout.addWidget(reset_button)
        layout.addWidget(button)
        return control

    def update_scale(self):
        self.settings["ui_scale"] = self.scale_combo.currentText()
        self.store.save(self.settings)
        self._prompt_restart_for_scale()

    def _prompt_restart_for_scale(self) -> None:
        dialog = MessageBox(
            "重启应用以生效",
            "界面缩放设置将在重启应用后生效，是否立即重启？",
            self.window(),
        )
        dialog.yesButton.setText("立即重启")
        dialog.cancelButton.setText("稍后")
        if dialog.exec():
            self._restart_app()

    def _restart_app(self) -> None:
        from PyQt6.QtCore import QProcess

        QProcess.startDetached(sys.executable, sys.argv)
        QApplication.quit()

    def update_color(self, color):
        self.settings["theme_color"] = color.name()
        self.store.save(self.settings)
        apply_theme()

    def reset_theme_color(self):
        default_color = QColor(APP_SETTINGS_TEMPLATE["theme_color"])
        self.color_button.setColor(default_color)
        self.update_color(default_color)
        self.show_message("主题色已重置", "")

    def show_index_check_dialog(self) -> None:
        if self.index_check_thread and self.index_check_thread.isRunning():
            return
        dialog = MessageBox(
            "是否要进行索引检查",
            "该功能会检查并尝试修复所有索引文件的内容缺失或格式缺失问题，您可能等待较长时间",
            self.window(),
        )
        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")
        if dialog.exec():
            self.start_index_check()

    def start_index_check(self) -> None:
        self.show_tip("正在检查索引...", "请稍后")
        self.index_check_thread = IndexCheckThread(self.index_checker)
        self.index_check_thread.completed.connect(self.finish_index_check)
        self.index_check_thread.failed.connect(self.fail_index_check)
        self.index_check_thread.start()

    def finish_index_check(self, payload: dict) -> None:
        self.index_check_thread = None
        issue_count = int(payload.get("issue_count", 0))
        self.finish_tip(f"检查完成，{'未发现问题' if issue_count == 0 else f'发现 {issue_count} 个问题'}", True)
        self._refresh_index_pages()
        invalid_times = payload.get("invalid_times", [])
        if invalid_times:
            InvalidBankTimeDialog(invalid_times, self.window()).exec()

    def fail_index_check(self, message: str) -> None:
        self.index_check_thread = None
        self.finish_tip(message, False)

    def _refresh_index_pages(self) -> None:
        window = self.window()
        for page_name in ("local_bank_page", "wrong_book_page", "favorite_page"):
            page = getattr(window, page_name, None)
            reload_method = getattr(page, "reload", None)
            if callable(reload_method):
                reload_method()

    def show_message(self, title: str, content: str) -> None:
        InfoBar.success(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)

    def show_error_message(self, title: str, content: str) -> None:
        InfoBar.error(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self)

    def show_tip(self, title: str, content: str) -> None:
        if self.state_tooltip and not sip.isdeleted(self.state_tooltip):
            self.state_tooltip.close()
        self.state_tooltip = StateToolTip(title, content, self)
        self.state_tooltip.show()
        self.state_tooltip.adjustSize()
        margin = 20
        self.state_tooltip.move(QPoint(max(self.width() - self.state_tooltip.width() - margin, margin), margin))

    def finish_tip(self, content: str, success: bool) -> None:
        if not self.state_tooltip or sip.isdeleted(self.state_tooltip):
            self.state_tooltip = None
            if not success:
                self.show_error_message("索引检查失败", content)
            return
        self.state_tooltip.setContent(content)
        self.state_tooltip.setState(success)
        if not success:
            self.state_tooltip.close()
            self.state_tooltip = None
