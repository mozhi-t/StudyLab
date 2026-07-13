from __future__ import annotations

import sys

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import QApplication, QFileDialog, QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ColorPickerButton, ComboBox, ComboBoxSettingCard, ExpandGroupSettingCard, FluentIcon, InfoBar, InfoBarPosition, MessageBox, MessageBoxBase, OptionsConfigItem, OptionsValidator, PushButton, PushSettingCard, SettingCard, SingleDirectionScrollArea, StateToolTip, SubtitleLabel, SwitchButton, qconfig
from qfluentwidgets.components.settings.expand_setting_card import GroupWidget

from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from config.theme import apply_theme
from core.base.index_checker import GlobalIndexChecker
from core.base.json_store import JsonStore
from core.python.pycharm_launcher import PyCharmLauncher
from ui.languages import LanguageManager
from ui.styles.home import HOME_STYLE_CLASSES
from ui.styles.title_style import apply_page_title_style
from ui.widgets.base.dialogs import CustomIntervalDialog, CustomLearningGoalDialog, InvalidBankTimeDialog


# Keys that are not a valid shortcut on their own: modifiers, lock keys, etc.
_IGNORED_KEYS = {
    Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
    Qt.Key.Key_AltGr, Qt.Key.Key_CapsLock, Qt.Key.Key_NumLock, Qt.Key.Key_ScrollLock,
    Qt.Key.Key_Mode_switch,
}


class LocalComboBoxSettingCard(ComboBoxSettingCard):
    """ComboBoxSettingCard that leaves persistence to StudyLab's settings file."""

    def setValue(self, value) -> None:
        if value not in self.optionToText:
            return

        self.comboBox.setCurrentText(self.optionToText[value])
        qconfig.set(self.configItem, value, save=False)

    def _onCurrentIndexChanged(self, index: int) -> None:
        qconfig.set(self.configItem, self.comboBox.itemData(index), save=False)


class WheelTransparentGroupWidget(GroupWidget):
    """Group row that lets page scroll areas handle wheel events."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class WheelTransparentExpandGroupSettingCard(ExpandGroupSettingCard):
    """ExpandGroupSettingCard whose expanded content does not trap wheel events."""

    def wheelEvent(self, event) -> None:
        event.ignore()

    def addGroup(self, icon, title: str, content: str, widget: QWidget, stretch=0) -> GroupWidget:
        group = WheelTransparentGroupWidget(icon, title, content, widget, stretch)
        self.addGroupWidget(group)
        return group


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
    learning_goal_changed = pyqtSignal()
    home_page_style_changed = pyqtSignal()

    def __init__(self, question_index_manager=None, wrong_manager=None, favorite_manager=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = APP_SETTINGS_TEMPLATE | self.store.load()
        if self.settings.get("language") == "跟随系统设置":
            self.settings["language"] = "system"
        self.language_manager = LanguageManager(self.settings.get("language", "system"))
        self.settings["answer_shortcuts"] = APP_SETTINGS_TEMPLATE["answer_shortcuts"] | self.settings.get("answer_shortcuts", {})
        self.settings["eye_care"] = APP_SETTINGS_TEMPLATE["eye_care"] | self.settings.get("eye_care", {})
        self.settings["python_answer"] = APP_SETTINGS_TEMPLATE["python_answer"] | self.settings.get("python_answer", {})
        self.question_index_manager = question_index_manager
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.index_checker = GlobalIndexChecker()
        self.index_check_thread: IndexCheckThread | None = None
        self.state_tooltip: StateToolTip | None = None
        self.reset_shortcut_buttons: list[PushButton] = []

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

        self.theme_card = self._create_combo_setting_card(
            "theme",
            self.settings.get("theme", "Auto"),
            ["Light", "Dark", "Auto"],
            FluentIcon.BRUSH,
            "应用主题",
            "调整您的应用的外观",
        )
        self.theme_combo = self.theme_card.comboBox
        self.theme_combo.currentTextChanged.connect(self.update_settings)
        layout.addWidget(self.theme_card)

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
        self.theme_color_card = self._create_control_setting_card(
                FluentIcon.PALETTE,
                "主题色",
                "调整您的应用的主题色",
                self.theme_color_control,
        )
        layout.addWidget(self.theme_color_card)

        self.scale_card = self._create_combo_setting_card(
            "ui_scale",
            self.settings.get("ui_scale", "跟随系统设置"),
            ["跟随系统设置", "100%", "110%", "125%"],
            FluentIcon.FONT_SIZE,
            "界面缩放",
            "调整少部件和字体的大小",
        )
        self.scale_combo = self.scale_card.comboBox
        self.scale_combo.currentTextChanged.connect(self.update_scale)
        layout.addWidget(self.scale_card)

        self.language_card = self._create_combo_setting_card(
            "language",
            self.settings.get("language", "zh_CN"),
            ["system", "zh_CN", "en_US"],
            FluentIcon.LANGUAGE,
            "语言",
            "选择界面所使用的语言",
            [
                self.language_manager.text("language_system"),
                self.language_manager.text("language_zh"),
                self.language_manager.text("language_en"),
            ],
        )
        self.language_combo = self.language_card.comboBox
        self.language_combo.currentIndexChanged.connect(self.update_language)
        layout.addWidget(self.language_card)

        self.home_style_card = self._create_combo_setting_card(
            "home_page_style",
            self.settings.get("home_page_style", "样式一"),
            [style_class.style_name for style_class in HOME_STYLE_CLASSES],
            FluentIcon.HOME,
            "主页样式",
            "切换主页的显示样式",
        )
        self.home_style_combo = self.home_style_card.comboBox
        self.home_style_combo.currentTextChanged.connect(self.update_home_page_style)
        layout.addWidget(self.home_style_card)

        self.window_memory_card = self._create_combo_setting_card(
            "window_memory_mode",
            self.settings.get("window_memory_mode", "default"),
            ["default", "size", "position", "size_position"],
            FluentIcon.FIT_PAGE,
            "窗口记忆",
            "选择是否记忆主窗口的大小和位置",
            self._window_memory_texts(),
        )
        self.window_memory_combo = self.window_memory_card.comboBox
        self.window_memory_combo.currentIndexChanged.connect(self.update_window_memory)
        layout.addWidget(self.window_memory_card)
        self.shortcut_title = SubtitleLabel("快捷键", self.content)
        shortcut_font = QFont(self.shortcut_title.font())
        shortcut_font.setPointSize(16)
        shortcut_font.setWeight(QFont.Weight.DemiBold)
        self.shortcut_title.setFont(shortcut_font)
        layout.addSpacing(18)
        layout.addWidget(self.shortcut_title)
        layout.addSpacing(18)
        self.prev_shortcut_card = self._create_control_setting_card(
                FluentIcon.LEFT_ARROW,
                "上一题快捷键",
                "答题界面中触发上一题操作",
                self.prev_shortcut_control,
        )
        layout.addWidget(self.prev_shortcut_card)
        self.next_shortcut_card = self._create_control_setting_card(
                FluentIcon.RIGHT_ARROW,
                "下一题快捷键",
                "答题界面中触发下一题操作",
                self.next_shortcut_control,
        )
        layout.addWidget(self.next_shortcut_card)
        self.mark_shortcut_card = self._create_control_setting_card(
                FluentIcon.TAG,
                "标记题目快捷键",
                "答题界面中标记或取消标记当前题目",
                self.mark_shortcut_control,
        )
        layout.addWidget(self.mark_shortcut_card)
        # ===== 学习设置 =====
        self.learning_goal_combo = ComboBox(self.content)
        self._learning_goal_presets = ["20", "50", "100", "150", "200"]
        self.learning_goal_combo.addItems([f"{count} 题" for count in self._learning_goal_presets])
        self.learning_goal_combo.addItem("自定义...")
        self._refresh_learning_goal_text(int(self.settings.get("daily_question_goal", 50)))
        self.learning_goal_combo.setFixedWidth(170)
        self.learning_goal_combo.activated.connect(self._on_learning_goal_changed)
        self.learning_goal_card = self._create_control_setting_card(
            FluentIcon.EDUCATION,
            "每日学习目标",
            "设置每天计划完成的刷题数量",
            self.learning_goal_combo,
        )

        # ===== 休息提醒 =====
        eye_care = self.settings["eye_care"]

        self.eye_care_group_card = WheelTransparentExpandGroupSettingCard(
            FluentIcon.CAFE,
            "休息提醒",
            "间隔提醒您远眺放松眼睛",
            parent=self.content,
        )
        self.eye_care_switch = SwitchButton(self.eye_care_group_card)
        self.eye_care_switch.setOnText("")
        self.eye_care_switch.setOffText("")
        self.eye_care_switch.setChecked(bool(eye_care.get("enabled", True)))
        self.eye_care_switch.checkedChanged.connect(self._on_eye_care_enabled_changed)
        self.eye_care_group_card.addWidget(self.eye_care_switch)

        self.eye_care_interval_combo = ComboBox(self.eye_care_group_card.view)
        self._eye_care_presets = ["20", "30", "40", "50", "60"]
        self.eye_care_interval_combo.addItems([f"{m} 分钟" for m in self._eye_care_presets])
        self.eye_care_interval_combo.addItem("自定义...")
        self._refresh_eye_care_interval_text(int(eye_care.get("interval_minutes", 20)))
        self.eye_care_interval_combo.setFixedWidth(170)
        self.eye_care_interval_combo.activated.connect(self._on_eye_care_interval_changed)

        self.eye_care_mode_combo = ComboBox(self.eye_care_group_card.view)
        self.eye_care_mode_combo.addItem("弹窗", userData="dialog")
        self.eye_care_mode_combo.addItem("顶部通知", userData="infobar")
        mode_index = 0 if eye_care.get("reminder_mode", "dialog") == "dialog" else 1
        self.eye_care_mode_combo.setCurrentIndex(mode_index)
        self.eye_care_mode_combo.setFixedWidth(170)
        self.eye_care_mode_combo.currentIndexChanged.connect(self._on_eye_care_mode_changed)
        self.eye_care_interval_group = self.eye_care_group_card.addGroup(
            FluentIcon.DATE_TIME,
            "提醒间隔",
            "设置多久提醒一次",
            self.eye_care_interval_combo,
        )
        self.eye_care_mode_group = self.eye_care_group_card.addGroup(
            FluentIcon.MESSAGE,
            "提醒方式",
            "选择提醒以何种形式出现",
            self.eye_care_mode_combo,
        )
        if self.eye_care_switch.isChecked():
            self.eye_care_group_card.setExpand(True)
        self._refresh_eye_care_controls_enabled()

        self.eye_care_title = SubtitleLabel("学习", self.content)
        eye_care_font = QFont(self.eye_care_title.font())
        eye_care_font.setPointSize(16)
        eye_care_font.setWeight(QFont.Weight.DemiBold)
        self.eye_care_title.setFont(eye_care_font)
        layout.addSpacing(18)
        layout.addWidget(self.eye_care_title)
        layout.addSpacing(18)
        layout.addWidget(self.learning_goal_card)
        layout.addWidget(self.eye_care_group_card)

        self.answer_title = SubtitleLabel("答题", self.content)
        answer_font = QFont(self.answer_title.font())
        answer_font.setPointSize(16)
        answer_font.setWeight(QFont.Weight.DemiBold)
        self.answer_title.setFont(answer_font)
        layout.addSpacing(18)
        layout.addWidget(self.answer_title)
        layout.addSpacing(18)

        python_settings = self.settings["python_answer"]
        self.python_answer_group_card = WheelTransparentExpandGroupSettingCard(
            FluentIcon.CODE,
            "Python",
            "配置 Python 编程题的答题方式和外部编辑器",
            parent=self.content,
        )
        self.python_mode_combo = ComboBox(self.python_answer_group_card.view)
        self.python_mode_combo.addItem("内置编辑器", userData="builtin")
        self.python_mode_combo.addItem("PyCharm", userData="pycharm")
        mode_index = 1 if python_settings.get("default_mode", "builtin") == "pycharm" else 0
        self.python_mode_combo.setCurrentIndex(mode_index)
        self.python_mode_combo.setFixedWidth(180)
        self.python_mode_combo.currentIndexChanged.connect(self._on_python_mode_changed)
        self.python_mode_group = self.python_answer_group_card.addGroup(
            FluentIcon.CODE,
            "默认答题模式",
            "选择进入 Python 编程题时默认使用的编辑方式",
            self.python_mode_combo,
        )

        saved_pycharm_dir = str(python_settings.get("pycharm_install_dir", "") or "")
        self.pycharm_path_control = QWidget(self.python_answer_group_card.view)
        pycharm_path_layout = QHBoxLayout(self.pycharm_path_control)
        pycharm_path_layout.setContentsMargins(0, 0, 0, 0)
        pycharm_path_layout.setSpacing(8)
        self.pycharm_browse_button = PushButton("选择目录", self.pycharm_path_control)
        self.pycharm_browse_button.clicked.connect(self._choose_pycharm_dir)
        self.pycharm_detect_button = PushButton("自动侦测", self.pycharm_path_control)
        self.pycharm_detect_button.clicked.connect(self._auto_detect_pycharm)
        self.pycharm_test_button = PushButton("检查", self.pycharm_path_control)
        self.pycharm_test_button.clicked.connect(self._test_saved_pycharm_path)
        pycharm_path_layout.addWidget(self.pycharm_browse_button)
        pycharm_path_layout.addWidget(self.pycharm_detect_button)
        pycharm_path_layout.addWidget(self.pycharm_test_button)
        self.pycharm_path_group = self.python_answer_group_card.addGroup(
            FluentIcon.COMMAND_PROMPT,
            "PyCharm安装目录",
            saved_pycharm_dir or "未设置",
            self.pycharm_path_control,
        )
        self.python_answer_group_card.setExpand(True)
        layout.addWidget(self.python_answer_group_card)

        self.advanced_title = SubtitleLabel("高级", self.content)
        advanced_font = QFont(self.advanced_title.font())
        advanced_font.setPointSize(16)
        advanced_font.setWeight(QFont.Weight.DemiBold)
        self.advanced_title.setFont(advanced_font)
        layout.addSpacing(18)
        layout.addWidget(self.advanced_title)
        layout.addSpacing(18)

        self.index_check_card = PushSettingCard(
            "检查索引",
            FluentIcon.SYNC,
            "全局索引检查",
            "检查并尝试修复题库、错题本、收藏夹的索引文件，仅当数据出现问题时使用",
            self.content,
        )
        self.index_check_button = self.index_check_card.button
        self.index_check_card.clicked.connect(self.show_index_check_dialog)
        layout.addWidget(self.index_check_card)
        layout.addStretch(1)
        self._apply_language()

    def _create_combo_setting_card(
        self,
        name: str,
        value: str,
        options: list[str],
        icon,
        title: str,
        content: str,
        texts: list[str] | None = None,
    ) -> ComboBoxSettingCard:
        if value not in options:
            value = options[0]
        config_item = OptionsConfigItem("StudyLabSettings", name, value, OptionsValidator(options))
        qconfig.set(config_item, value, save=False)
        card = LocalComboBoxSettingCard(config_item, icon, title, content, texts or options, self.content)
        card.comboBox.setFixedWidth(170)
        return card

    def _create_control_setting_card(self, icon, title: str, content: str, control: QWidget) -> SettingCard:
        card = SettingCard(icon, title, content, self.content)
        card.hBoxLayout.addWidget(control, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)
        return card

    def _refresh_eye_care_interval_text(self, minutes: int) -> None:
        """根据存储的分钟数，把间隔 ComboBox 的显示文本对到正确项。"""
        combo = self.eye_care_interval_combo
        combo.blockSignals(True)
        custom_index = combo.count() - 1
        if str(minutes) in self._eye_care_presets:
            combo.setItemText(custom_index, self.language_manager.text("custom"))
            combo.setCurrentText(self.language_manager.text("minutes", value=minutes))
        else:
            combo.setItemText(
                custom_index,
                f'{self.language_manager.text("minutes", value=minutes)} ({self.language_manager.text("custom").rstrip(".")})',
            )
            combo.setCurrentIndex(custom_index)
        combo.blockSignals(False)

    def _refresh_learning_goal_text(self, count: int) -> None:
        combo = self.learning_goal_combo
        combo.blockSignals(True)
        custom_index = combo.count() - 1
        if str(count) in self._learning_goal_presets:
            combo.setItemText(custom_index, self.language_manager.text("custom"))
            combo.setCurrentText(self.language_manager.text("questions", value=count))
        else:
            combo.setItemText(
                custom_index,
                f'{self.language_manager.text("questions", value=count)} ({self.language_manager.text("custom").rstrip(".")})',
            )
            combo.setCurrentIndex(custom_index)
        combo.blockSignals(False)

    def _on_learning_goal_changed(self, index: int) -> None:
        combo = self.learning_goal_combo
        if index == combo.count() - 1:
            current = int(self.settings.get("daily_question_goal", 50))
            dialog = CustomLearningGoalDialog(current, self.window())
            if dialog.exec():
                count = dialog.value
                self.settings["daily_question_goal"] = count
                self.store.save(self.settings)
                self._refresh_learning_goal_text(count)
                self.learning_goal_changed.emit()
            else:
                self._refresh_learning_goal_text(current)
            return

        try:
            count = int(combo.itemText(index).split()[0])
        except (ValueError, IndexError):
            count = 50
        self.settings["daily_question_goal"] = count
        self.store.save(self.settings)
        self.learning_goal_changed.emit()

    def _on_eye_care_enabled_changed(self, checked: bool) -> None:
        self.settings["eye_care"]["enabled"] = bool(checked)
        self.store.save(self.settings)
        if checked:
            self.eye_care_group_card.setExpand(True)
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

    def _on_python_mode_changed(self, index: int) -> None:
        self.settings["python_answer"]["default_mode"] = self.python_mode_combo.itemData(index) or "builtin"
        self.store.save(self.settings)

    def _choose_pycharm_dir(self) -> None:
        current = str(self.settings["python_answer"].get("pycharm_install_dir", "") or "")
        selected = QFileDialog.getExistingDirectory(
            self, "选择 PyCharm 安装目录", current
        )
        if selected:
            self._save_pycharm_path(selected)
            self._test_pycharm_path(selected)

    def _save_pycharm_path(self, value: str) -> None:
        value = value.strip()
        self.pycharm_path_group.setContent(value or "未设置")
        self.settings["python_answer"]["pycharm_install_dir"] = value
        self.store.save(self.settings)

    def _auto_detect_pycharm(self) -> None:
        launcher = PyCharmLauncher()
        executable = launcher.detect()
        if executable is None:
            self.show_error_message("自动侦测失败", "未在系统中找到 PyCharm")
            return
        install_dir = str(launcher.install_dir_for(executable))
        self._save_pycharm_path(install_dir)
        self.show_message("已侦测到 PyCharm", install_dir)

    def _test_saved_pycharm_path(self) -> None:
        value = str(self.settings["python_answer"].get("pycharm_install_dir", "") or "")
        if not value:
            self.show_error_message("尚未设置目录", "请先选择目录或使用自动侦测")
            return
        self._test_pycharm_path(value)

    def _test_pycharm_path(self, value: str) -> None:
        launcher = PyCharmLauncher()
        executable = launcher.resolve(value.strip())
        if executable:
            install_dir = str(launcher.install_dir_for(executable))
            self._save_pycharm_path(install_dir)
            self.show_message("PyCharm配置有效", str(executable))
        else:
            self.pycharm_path_group.setContent(f"{value}（未找到 PyCharm）")
            self.show_error_message("未找到 PyCharm", "请选择包含 bin/pycharm64.exe 的安装目录")

    def update_settings(self, *_args):
        self.settings["theme"] = self.theme_combo.currentText()
        self.store.save(self.settings)
        apply_theme()

    def update_language(self, index: int) -> None:
        language = self.language_combo.itemData(index) or "system"
        self.settings["language"] = language
        self.store.save(self.settings)
        self.language_manager.set_language(language)
        self._apply_language()

    def _apply_language(self) -> None:
        tr = self.language_manager.text
        self.page_title.setText(tr("settings"))
        self.title_label.setText(tr("personalization"))
        self.shortcut_title.setText(tr("shortcuts"))
        self.eye_care_title.setText(tr("study"))
        self.answer_title.setText("答题")
        self.advanced_title.setText(tr("advanced"))

        card_texts = (
            (self.theme_card, "theme", "theme_desc"),
            (self.theme_color_card, "theme_color", "theme_color_desc"),
            (self.scale_card, "ui_scale", "ui_scale_desc"),
            (self.language_card, "language", "language_desc"),
            (self.home_style_card, "home_style", "home_style_desc"),
            (self.window_memory_card, "window_memory", "window_memory_desc"),
            (self.prev_shortcut_card, "prev_shortcut", "prev_shortcut_desc"),
            (self.next_shortcut_card, "next_shortcut", "next_shortcut_desc"),
            (self.mark_shortcut_card, "mark_shortcut", "mark_shortcut_desc"),
            (self.learning_goal_card, "daily_goal", "daily_goal_desc"),
            (self.eye_care_group_card, "eye_care", "eye_care_desc"),
            (self.index_check_card, "index_check", "index_check_desc"),
        )
        for card, title_key, content_key in card_texts:
            target = card.card if hasattr(card, "card") else card
            target.setTitle(tr(title_key))
            target.setContent(tr(content_key))

        language_texts = (tr("language_system"), tr("language_zh"), tr("language_en"))
        for index, text in enumerate(language_texts):
            self.language_combo.setItemText(index, text)
        for index, text in enumerate(self._window_memory_texts()):
            self.window_memory_combo.setItemText(index, text)
        self.reset_theme_color_button.setText(tr("reset"))
        for button in self.reset_shortcut_buttons:
            button.setText(tr("reset"))
        self.index_check_button.setText(tr("check_index"))
        self.eye_care_interval_group.setTitle(tr("interval"))
        self.eye_care_interval_group.setContent(tr("interval_desc"))
        self.eye_care_mode_group.setTitle(tr("reminder_mode"))
        self.eye_care_mode_group.setContent(tr("reminder_mode_desc"))
        self.eye_care_interval_combo.setItemText(0, tr("minutes", value=20))
        for index, minutes in enumerate(self._eye_care_presets):
            self.eye_care_interval_combo.setItemText(index, tr("minutes", value=minutes))
        for index, count in enumerate(self._learning_goal_presets):
            self.learning_goal_combo.setItemText(index, tr("questions", value=count))
        self.eye_care_mode_combo.setItemText(0, tr("mode_dialog"))
        self.eye_care_mode_combo.setItemText(1, tr("mode_infobar"))
        self._refresh_eye_care_interval_text(
            int(self.settings["eye_care"].get("interval_minutes", 20))
        )
        self._refresh_learning_goal_text(int(self.settings.get("daily_question_goal", 50)))

    def update_home_page_style(self, *_args) -> None:
        self.settings["home_page_style"] = self.home_style_combo.currentText()
        self.store.save(self.settings)
        self.home_page_style_changed.emit()

    def update_window_memory(self, index: int) -> None:
        self.settings["window_memory_mode"] = self.window_memory_combo.itemData(index) or "default"
        self.store.save(self.settings)

    def _window_memory_texts(self) -> list[str]:
        tr = self.language_manager.text
        return [
            tr("window_default"),
            tr("window_size"),
            tr("window_position"),
            tr("window_size_position"),
        ]

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
        self.reset_shortcut_buttons.append(reset_button)
        reset_button.clicked.connect(lambda: self.reset_shortcut(key, label_map[key]))
        layout.addWidget(reset_button)
        layout.addWidget(button)
        return control

    def update_scale(self, *_args):
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
