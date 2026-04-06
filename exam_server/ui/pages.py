from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, ColorPickerButton, ComboBox, FluentIcon, InfoBar, InfoBarPosition, LineEdit, PrimaryPushButton, PushButton, SingleDirectionScrollArea, StrongBodyLabel, SubtitleLabel

try:
    from ..core.datetime_utils import format_datetime
    from ..core.json_store import JsonStore
    from ..core.theme import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE, apply_theme
except ImportError:
    from core.datetime_utils import format_datetime
    from core.json_store import JsonStore
    from core.theme import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE, apply_theme
from .common import PreferenceCard, StyledCardWidget, apply_page_title_style


def configure_scroll_area(scroll_area: SingleDirectionScrollArea, content: QWidget, object_name: str) -> None:
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.enableTransparentBackground()
    scroll_area.setStyleSheet("SingleDirectionScrollArea{background: transparent; border: none;}")
    content.setObjectName(object_name)
    content.setStyleSheet(f"QWidget#{object_name}{{background: transparent; border: none;}}")
    scroll_area.setWidget(content)


class ServerHomePage(QWidget):
    service_toggle_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(5)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        self.title_label = SubtitleLabel("StudyLab - 考试服务端", self)
        apply_page_title_style(self.title_label)
        title_row.addWidget(self.title_label)
        title_row.addStretch(1)
        self.service_button = PrimaryPushButton("开启服务", self)
        self.service_button.clicked.connect(self.service_toggle_requested.emit)
        title_row.addWidget(self.service_button)
        root.addLayout(title_row)

        self.address_label = CaptionLabel("当前连接地址：未开启", self)
        root.addWidget(self.address_label)
        root.addSpacing(18)

        self.summary_card = StyledCardWidget(self)
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(20, 20, 20, 20)
        self.connection_label = StrongBodyLabel("当前连接人数：0", self.summary_card)
        summary_layout.addWidget(self.connection_label)
        root.addWidget(self.summary_card)

        self.list_card = StyledCardWidget(self)
        list_layout = QVBoxLayout(self.list_card)
        list_layout.setContentsMargins(12, 12, 12, 12)
        self.scroll = SingleDirectionScrollArea(self.list_card, Qt.Orientation.Vertical)
        self.scroll_content = QWidget(self.scroll)
        configure_scroll_area(self.scroll, self.scroll_content, "serverHomeConnectionsContent")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch(1)
        list_layout.addWidget(self.scroll)
        root.addWidget(self.list_card, 1)
        self.cards: list[QWidget] = []

    def update_connections(self, connections: list[dict]) -> None:
        self.connection_label.setText(f"当前连接人数：{len(connections)}")
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        for item in connections:
            card = StyledCardWidget(self.scroll_content)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 10, 14, 10)
            layout.addWidget(StrongBodyLabel(item.get("device_name") or "未知设备", card))
            layout.addWidget(BodyLabel(f"IP：{item.get('ip_address', '')}", card))
            layout.addWidget(BodyLabel(f"用户：{item.get('username', '') or '未认证'}", card))
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, card)
            self.cards.append(card)

    def set_service_state(self, address: str, running: bool) -> None:
        self.address_label.setText(f"当前连接地址：{address}")
        self.service_button.setText("停止服务" if running else "开启服务")


class ExamActionCard(StyledCardWidget):
    enable_clicked = pyqtSignal(str)
    score_clicked = pyqtSignal(str)
    edit_clicked = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)

    def __init__(self, exam: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.exam_name = exam["exam_name"]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        text_layout = QVBoxLayout()
        text_layout.addWidget(StrongBodyLabel(exam["exam_name"], self))
        text_layout.addWidget(BodyLabel(f"开始时间：{format_datetime(exam['start_time'])}", self))
        text_layout.addWidget(
            CaptionLabel(
                f"设置摘要：禁止重复进入：{'是' if int(exam.get('disallow_reentry_after_submit', 1)) else '否'}",
                self,
            )
        )
        layout.addLayout(text_layout, 1)
        layout.addWidget(BodyLabel(f"时长：{exam['duration_minutes']} 分钟", self))
        self.enable_button = PrimaryPushButton("结束考试" if exam.get("enabled") else "启用考试", self)
        self.score_button = PushButton("查看分数", self)
        self.settings_button = PushButton("设置", self)
        self.delete_button = PushButton("删除", self)
        self.enable_button.clicked.connect(lambda: self.enable_clicked.emit(self.exam_name))
        self.score_button.clicked.connect(lambda: self.score_clicked.emit(self.exam_name))
        self.settings_button.clicked.connect(lambda: self.edit_clicked.emit(self.exam_name))
        self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(self.exam_name))
        layout.addWidget(self.enable_button)
        layout.addWidget(self.score_button)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.delete_button)


class ServerExamListPage(QWidget):
    enable_exam_requested = pyqtSignal(str)
    view_scores_requested = pyqtSignal(str)
    edit_exam_requested = pyqtSignal(str)
    delete_exam_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(5)

        title = SubtitleLabel("考试列表", self)
        apply_page_title_style(title)
        root.addWidget(title)
        root.addSpacing(18)

        self.filter_card = StyledCardWidget(self)
        filter_layout = QVBoxLayout(self.filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        self.search_edit = LineEdit(self.filter_card)
        self.search_edit.setPlaceholderText("搜索考试题库")
        self.search_edit.textChanged.connect(self.filter_changed)
        filter_layout.addWidget(self.search_edit)
        root.addWidget(self.filter_card)

        self.list_card = StyledCardWidget(self)
        list_layout = QVBoxLayout(self.list_card)
        list_layout.setContentsMargins(12, 12, 12, 12)
        self.scroll = SingleDirectionScrollArea(self.list_card, Qt.Orientation.Vertical)
        self.content = QWidget(self.scroll)
        configure_scroll_area(self.scroll, self.content, "serverExamListContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch(1)
        list_layout.addWidget(self.scroll)
        root.addWidget(self.list_card, 1)

        self.exams: list[dict] = []
        self.cards: list[ExamActionCard] = []

    def set_exams(self, exams: list[dict]) -> None:
        self.exams = exams
        self.filter_changed()

    def filter_changed(self) -> None:
        keyword = self.search_edit.text().strip().lower()
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        for exam in self.exams:
            if keyword and keyword not in exam["exam_name"].lower():
                continue
            card = ExamActionCard(exam, self.content)
            card.enable_clicked.connect(self.enable_exam_requested)
            card.score_clicked.connect(self.view_scores_requested)
            card.edit_clicked.connect(self.edit_exam_requested)
            card.delete_clicked.connect(self.delete_exam_requested)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)


class ServerSettingsPage(QWidget):
    settings_changed = pyqtSignal(dict)

    def __init__(self, host_ip: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.host_ip = host_ip
        self.app_settings_store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.app_settings = APP_SETTINGS_TEMPLATE | self.app_settings_store.load()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(0)

        self.scroll = SingleDirectionScrollArea(self, Qt.Orientation.Vertical)
        root.addWidget(self.scroll)

        self.content = QWidget(self.scroll)
        configure_scroll_area(self.scroll, self.content, "serverSettingsContent")

        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)

        title = SubtitleLabel("考试设置", self.content)
        apply_page_title_style(title)
        content_layout.addWidget(title)
        content_layout.addSpacing(18)

        self.section_title = SubtitleLabel("服务端", self.content)
        section_font = QFont(self.section_title.font())
        section_font.setPointSize(16)
        section_font.setWeight(QFont.Weight.DemiBold)
        self.section_title.setFont(section_font)
        content_layout.addWidget(self.section_title)
        content_layout.addSpacing(18)

        self.port_edit = LineEdit(self.content)
        self.port_edit.setPlaceholderText("端口号")
        self.port_edit.setFixedWidth(170)
        self.port_edit.editingFinished.connect(self._emit_settings_changed)

        self.server_name_edit = LineEdit(self.content)
        self.server_name_edit.setPlaceholderText("服务端名称")
        self.server_name_edit.setFixedWidth(170)
        self.server_name_edit.editingFinished.connect(self._emit_settings_changed)

        self.max_clients_edit = LineEdit(self.content)
        self.max_clients_edit.setPlaceholderText("最大连接数")
        self.max_clients_edit.setFixedWidth(170)
        self.max_clients_edit.editingFinished.connect(self._emit_settings_changed)

        self.auth_mode_combo = ComboBox(self.content)
        self.auth_mode_values = [0, 1, 2]
        self.auth_mode_combo.addItems(["无需认证", "仅用户名", "用户名+密码"])
        self.auth_mode_combo.setFixedWidth(170)
        self.auth_mode_combo.currentIndexChanged.connect(self._emit_settings_changed)

        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.GLOBE,
                "端口号",
                "设置服务端对外监听的端口号",
                self.port_edit,
                self.content,
            )
        )
        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.INFO,
                "服务端名称",
                "用于局域网内识别当前考试服务端",
                self.server_name_edit,
                self.content,
            )
        )
        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.PEOPLE,
                "最大连接数",
                "限制同时连接到服务端的客户端数量",
                self.max_clients_edit,
                self.content,
            )
        )
        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.SETTING,
                "认证模式",
                "设置连接时是否需要用户名或用户名密码认证",
                self.auth_mode_combo,
                self.content,
            )
        )
        content_layout.addSpacing(18)

        self.personal_title = SubtitleLabel("个性化", self.content)
        personal_font = QFont(self.personal_title.font())
        personal_font.setPointSize(16)
        personal_font.setWeight(QFont.Weight.DemiBold)
        self.personal_title.setFont(personal_font)
        content_layout.addWidget(self.personal_title)
        content_layout.addSpacing(18)

        self.theme_combo = ComboBox(self.content)
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        self.theme_combo.setCurrentText(self.app_settings.get("theme", APP_SETTINGS_TEMPLATE["theme"]))
        self.theme_combo.setFixedWidth(170)
        self.theme_combo.currentTextChanged.connect(self.update_personalization)

        self.color_button = ColorPickerButton(
            QColor(self.app_settings.get("theme_color", APP_SETTINGS_TEMPLATE["theme_color"])),
            "选择主题色",
            self.content,
        )
        self.color_button.colorChanged.connect(self.update_color)
        self.theme_color_control = QWidget(self.content)
        self.theme_color_layout = QHBoxLayout(self.theme_color_control)
        self.theme_color_layout.setContentsMargins(0, 0, 0, 0)
        self.theme_color_layout.setSpacing(8)
        self.reset_theme_color_button = PushButton("重置", self.theme_color_control)
        self.reset_theme_color_button.clicked.connect(self.reset_theme_color)
        self.theme_color_layout.addWidget(self.reset_theme_color_button)
        self.theme_color_layout.addWidget(self.color_button)

        self.scale_combo = ComboBox(self.content)
        self.scale_combo.addItems(["跟随系统设置", "100%", "110%", "125%"])
        self.scale_combo.setCurrentText(self.app_settings.get("ui_scale", APP_SETTINGS_TEMPLATE["ui_scale"]))
        self.scale_combo.setFixedWidth(170)
        self.scale_combo.currentTextChanged.connect(self.update_personalization)

        self.language_combo = ComboBox(self.content)
        self.language_combo.addItems(["跟随系统设置", "zh_CN", "en_US"])
        language = self.app_settings.get("language", APP_SETTINGS_TEMPLATE["language"])
        self.language_combo.setCurrentText(language if language in ["跟随系统设置", "zh_CN", "en_US"] else APP_SETTINGS_TEMPLATE["language"])
        self.language_combo.setFixedWidth(170)
        self.language_combo.currentTextChanged.connect(self.update_personalization)

        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.BRUSH,
                "应用主题",
                "调整您的应用的外观",
                self.theme_combo,
                self.content,
            )
        )
        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.PALETTE,
                "主题色",
                "调整您的应用的主题色",
                self.theme_color_control,
                self.content,
            )
        )
        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.FONT_SIZE,
                "界面缩放",
                "调整少部件和字体的大小",
                self.scale_combo,
                self.content,
            )
        )
        content_layout.addWidget(
            PreferenceCard(
                FluentIcon.LANGUAGE,
                "语言",
                "选择界面所使用的语言",
                self.language_combo,
                self.content,
            )
        )
        content_layout.addStretch(1)

    def set_settings(self, config: dict) -> None:
        self.port_edit.setText(str(config.get("listen_port", "")))
        self.server_name_edit.setText(str(config.get("server_name", "")))
        self.max_clients_edit.setText(str(config.get("max_clients", "")))
        self.auth_mode_combo.setCurrentIndex(max(min(int(config.get("auth_mode", 0)), 2), 0))

    def _emit_settings_changed(self) -> None:
        self.settings_changed.emit(
            {
                "server_name": self.server_name_edit.text().strip() or "StudyLab Exam Server",
                "max_clients": int(self.max_clients_edit.text().strip() or 30),
                "auth_mode": self.auth_mode_values[self.auth_mode_combo.currentIndex()],
                "listen_port": int(self.port_edit.text().strip() or 9000),
            }
        )

    def update_personalization(self) -> None:
        self.app_settings["theme"] = self.theme_combo.currentText()
        self.app_settings["ui_scale"] = self.scale_combo.currentText()
        self.app_settings["language"] = self.language_combo.currentText()
        self.app_settings_store.save(self.app_settings)
        apply_theme()

    def update_color(self, color) -> None:
        self.app_settings["theme_color"] = color.name()
        self.app_settings_store.save(self.app_settings)
        apply_theme()

    def reset_theme_color(self) -> None:
        default_color = QColor(APP_SETTINGS_TEMPLATE["theme_color"])
        self.color_button.setColor(default_color)
        self.update_color(default_color)
        self.show_message("主题色已重置", "重置主题色成功")

    def show_message(self, title: str, content: str) -> None:
        InfoBar.success(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)


class ServerLogPage(QWidget):
    refresh_requested = pyqtSignal()
    file_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(5)

        title = SubtitleLabel("日志", self)
        apply_page_title_style(title)
        root.addWidget(title)
        root.addSpacing(18)

        self.filter_card = StyledCardWidget(self)
        filter_layout = QHBoxLayout(self.filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(10)
        self.file_combo = ComboBox(self.filter_card)
        self.file_combo.setMinimumWidth(260)
        self.file_combo.currentTextChanged.connect(self._emit_file_changed)
        self.refresh_button = PrimaryPushButton("刷新", self.filter_card)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        filter_layout.addWidget(self.file_combo, 1)
        filter_layout.addWidget(self.refresh_button)
        root.addWidget(self.filter_card)

        self.content_card = StyledCardWidget(self)
        content_layout = QVBoxLayout(self.content_card)
        content_layout.setContentsMargins(12, 12, 12, 12)
        self.log_view = QPlainTextEdit(self.content_card)
        self.log_view.setReadOnly(True)
        self.log_view.setFrameShape(QFrame.Shape.NoFrame)
        self.log_view.setStyleSheet("QPlainTextEdit{background: transparent; border: none;}")
        content_layout.addWidget(self.log_view)
        root.addWidget(self.content_card, 1)

    def set_log_files(self, filenames: list[str], current: str | None = None) -> None:
        selected = current or self.file_combo.currentText()
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        if filenames:
            self.file_combo.addItems(filenames)
            target = selected if selected in filenames else filenames[0]
            self.file_combo.setCurrentText(target)
        self.file_combo.blockSignals(False)

    def set_log_content(self, content: str) -> None:
        self.log_view.setPlainText(content)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def current_file(self) -> str:
        return self.file_combo.currentText().strip()

    def _emit_file_changed(self, filename: str) -> None:
        if filename.strip():
            self.file_changed.emit(filename.strip())
