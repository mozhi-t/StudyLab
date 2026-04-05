from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, ComboBox, FluentIcon, LineEdit, PrimaryPushButton, PushButton, ScrollArea, StrongBodyLabel, SubtitleLabel

from ui.pages.settings_page import PreferenceCard
from ui.styles.title_style import apply_page_title_style
from ui.widgets.styled_card import StyledCardWidget


class ServerHomePage(QWidget):
    service_toggle_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(5)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        self.title_label = SubtitleLabel("Study Lab - 考试服务端", self)
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
        self.scroll = ScrollArea(self.list_card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(self.scroll.Shape.NoFrame)
        self.scroll_content = QWidget(self.scroll)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch(1)
        self.scroll.setWidget(self.scroll_content)
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
        text_layout.addWidget(BodyLabel(f"开始时间：{exam['start_time']}", self))
        layout.addLayout(text_layout, 1)
        layout.addWidget(BodyLabel(f"时长：{exam['duration_minutes']} 分钟", self))
        self.enable_button = PrimaryPushButton("结束考试" if exam.get("enabled") else "启用考试", self)
        self.settings_button = PushButton("设置", self)
        self.delete_button = PushButton("删除", self)
        self.enable_button.clicked.connect(lambda: self.enable_clicked.emit(self.exam_name))
        self.settings_button.clicked.connect(lambda: self.edit_clicked.emit(self.exam_name))
        self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(self.exam_name))
        layout.addWidget(self.enable_button)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.delete_button)


class ServerExamListPage(QWidget):
    enable_exam_requested = pyqtSignal(str)
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
        self.scroll = ScrollArea(self.list_card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(self.scroll.Shape.NoFrame)
        self.content = QWidget(self.scroll)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
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
            card.edit_clicked.connect(self.edit_exam_requested)
            card.delete_clicked.connect(self.delete_exam_requested)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)


class ServerSettingsPage(QWidget):
    settings_changed = pyqtSignal(dict)

    def __init__(self, host_ip: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.host_ip = host_ip
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(5)

        title = SubtitleLabel("考试设置", self)
        apply_page_title_style(title)
        root.addWidget(title)
        root.addSpacing(18)

        self.section_title = SubtitleLabel("服务端", self)
        section_font = QFont(self.section_title.font())
        section_font.setPointSize(16)
        section_font.setWeight(QFont.Weight.DemiBold)
        self.section_title.setFont(section_font)
        root.addWidget(self.section_title)
        root.addSpacing(18)

        self.port_edit = LineEdit(self)
        self.port_edit.setPlaceholderText("端口号")
        self.port_edit.setFixedWidth(170)
        self.port_edit.editingFinished.connect(self._emit_settings_changed)

        self.server_name_edit = LineEdit(self)
        self.server_name_edit.setPlaceholderText("服务端名称")
        self.server_name_edit.setFixedWidth(170)
        self.server_name_edit.editingFinished.connect(self._emit_settings_changed)

        self.max_clients_edit = LineEdit(self)
        self.max_clients_edit.setPlaceholderText("最大连接数")
        self.max_clients_edit.setFixedWidth(170)
        self.max_clients_edit.editingFinished.connect(self._emit_settings_changed)

        self.auth_mode_combo = ComboBox(self)
        self.auth_mode_values = [0, 1, 2]
        self.auth_mode_combo.addItems(["无需认证", "仅用户名", "用户名+密码"])
        self.auth_mode_combo.setFixedWidth(170)
        self.auth_mode_combo.currentIndexChanged.connect(self._emit_settings_changed)

        root.addWidget(
            PreferenceCard(
                FluentIcon.GLOBE,
                "端口号",
                "设置服务端对外监听的端口号",
                self.port_edit,
                self,
            )
        )
        root.addWidget(
            PreferenceCard(
                FluentIcon.INFO,
                "服务端名称",
                "用于局域网内识别当前考试服务端",
                self.server_name_edit,
                self,
            )
        )
        root.addWidget(
            PreferenceCard(
                FluentIcon.PEOPLE,
                "最大连接数",
                "限制同时连接到服务端的客户端数量",
                self.max_clients_edit,
                self,
            )
        )
        root.addWidget(
            PreferenceCard(
                FluentIcon.SETTING,
                "认证模式",
                "设置连接时是否需要用户名或用户名密码认证",
                self.auth_mode_combo,
                self,
            )
        )
        root.addStretch(1)

    def set_settings(self, config: dict) -> None:
        self.port_edit.setText(str(config.get("listen_port", "")))
        self.server_name_edit.setText(str(config.get("server_name", "")))
        self.max_clients_edit.setText(str(config.get("max_clients", "")))
        self.auth_mode_combo.setCurrentIndex(max(min(int(config.get("auth_mode", 0)), 2), 0))

    def _emit_settings_changed(self) -> None:
        self.settings_changed.emit(
            {
                "server_name": self.server_name_edit.text().strip() or "Study Lab Exam Server",
                "max_clients": int(self.max_clients_edit.text().strip() or 30),
                "auth_mode": self.auth_mode_values[self.auth_mode_combo.currentIndex()],
                "listen_port": int(self.port_edit.text().strip() or 8765),
            }
        )
