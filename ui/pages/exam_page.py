from __future__ import annotations

import json
import platform
import socket

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, InfoBar, InfoBarPosition, Pivot, PrimaryPushButton, ScrollArea, StateToolTip, SubtitleLabel, LineEdit

from answer.lan_exam_window import LanExamWindow
from core.lan_exam_client import LanExamClientThread
from core.lan_exam_store import LanExamStore
from ui.styles.title_style import apply_page_title_style
from ui.widgets.lan_exam_dialogs import ExamPasswordDialog, LanExamAuthDialog, LoadingMessageDialog
from ui.widgets.question_card import QuestionCard
from ui.widgets.styled_card import StyledCardWidget


def local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


class LanExamCard(QuestionCard):
    def __init__(self, exam: dict, parent: QWidget | None = None):
        super().__init__(
            title=exam["exam_name"],
            right_meta=f"开始时间：{exam['start_time']}  时长：{exam['duration_minutes']}分钟",
            parent=parent,
        )
        self.enter_button = PrimaryPushButton("进入考试", self)
        self.layout().addWidget(self.enter_button, alignment=Qt.AlignmentFlag.AlignVCenter)


class ExamPage(QWidget):
    def __init__(self, wrong_manager, favorite_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.client_thread: LanExamClientThread | None = None
        self.client_id = ""
        self.auth_mode = 0
        self.username = ""
        self.device_name = platform.node() or platform.system()
        self.ip_address = local_ip()
        self.enabled_exams: list[dict] = []
        self.cards: list[LanExamCard] = []
        self.paper_chunks: list[str] = []
        self.pending_exam_name = ""
        self.loading_dialog: LoadingMessageDialog | None = None
        self.lan_exam_window: LanExamWindow | None = None
        self.store = LanExamStore()
        self.state_tooltip: StateToolTip | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.page_title = SubtitleLabel("考试", self)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)

        self.pivot = Pivot(self)
        self.pivot.currentItemChanged.connect(self._on_pivot_changed)
        self.stack = QStackedWidget(self)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        layout.addLayout(nav_layout)
        layout.addWidget(self.stack, 1)

        self.route_to_index = {}
        self._add_page("local_exam", "本地考试", self._build_local_exam_page())
        self._add_page("lan_exam", "局域网考试", self._build_lan_exam_page())
        self.pivot.setCurrentItem("local_exam")
        self.stack.setCurrentIndex(0)

    def _add_page(self, route_key: str, text: str, page: QWidget) -> None:
        self.stack.addWidget(page)
        self.route_to_index[route_key] = self.stack.indexOf(page)
        self.pivot.addItem(routeKey=route_key, text=text, onClick=lambda: None)

    def _build_local_exam_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(BodyLabel("正在积极开发中...", page))
        layout.addStretch(1)
        return page

    def _build_lan_exam_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.connect_card = StyledCardWidget(page)
        connect_layout = QHBoxLayout(self.connect_card)
        connect_layout.setContentsMargins(12, 12, 12, 12)
        connect_layout.setSpacing(10)
        self.address_input = LineEdit(self.connect_card)
        self.address_input.setPlaceholderText("输入局域网考试地址，如 192.168.1.10:8765")
        self.connect_button = PrimaryPushButton("连接", self.connect_card)
        self.connect_button.clicked.connect(self.toggle_connection)
        connect_layout.addWidget(self.address_input, 1)
        connect_layout.addWidget(self.connect_button)
        layout.addWidget(self.connect_card)

        self.search_card = StyledCardWidget(page)
        search_layout = QVBoxLayout(self.search_card)
        search_layout.setContentsMargins(12, 12, 12, 12)
        self.search_edit = LineEdit(self.search_card)
        self.search_edit.setPlaceholderText("搜索已启用考试")
        self.search_edit.textChanged.connect(self.render_exam_list)
        search_layout.addWidget(self.search_edit)
        layout.addWidget(self.search_card)

        self.content_card = StyledCardWidget(page)
        content_layout = QVBoxLayout(self.content_card)
        content_layout.setContentsMargins(12, 12, 12, 12)
        self.scroll = ScrollArea(self.content_card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(self.scroll.Shape.NoFrame)
        self.content = QWidget(self.scroll)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.placeholder_label = BodyLabel("局域网考试连接结果将在这里显示", self.content)
        self.content_layout.addWidget(self.placeholder_label)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        content_layout.addWidget(self.scroll)
        layout.addWidget(self.content_card, 1)
        return page

    def toggle_connection(self) -> None:
        if self.client_thread and self.client_thread.isRunning():
            self.show_tip("正在断开连接...", "请稍后")
            self.client_thread.send_message({"type": "disconnect", "client_id": self.client_id, "username": self.username})
            return
        address = self.address_input.text().strip()
        if not address:
            self.show_bar("连接失败", "请输入服务端地址", error=True)
            return
        self.show_tip("正在尝试连接到服务端", "请稍后")
        self.client_thread = LanExamClientThread(f"ws://{address}/ws")
        self.client_thread.connected.connect(self.on_socket_connected)
        self.client_thread.message_received.connect(self.handle_message)
        self.client_thread.connection_failed.connect(self.on_connection_failed)
        self.client_thread.disconnected.connect(self.on_disconnected)
        self.client_thread.start()

    def on_socket_connected(self) -> None:
        if not self.client_thread:
            return
        self.client_thread.send_message(
            {
                "type": "hello",
                "device_name": self.device_name,
                "ip_address": self.ip_address,
            }
        )

    def handle_message(self, payload: dict) -> None:
        message_type = payload.get("type")
        if message_type == "hello_ack":
            self.handle_hello_ack(payload)
        elif message_type == "auth_result":
            self.handle_auth_result(payload)
        elif message_type == "disconnect_result":
            self.reset_connection_state()
            self.finish_tip("断开成功", True)
        elif message_type == "heartbeat":
            if self.client_thread:
                self.client_thread.send_message({"type": "heartbeat_ack", "client_id": self.client_id})
        elif message_type == "exam_enabled_update":
            self.enabled_exams = payload.get("enabled_exams", [])
            self.render_exam_list()
        elif message_type == "exam_request_result":
            self.close_loading_dialog()
            self.show_bar("进入考试失败", payload.get("message", ""), error=True)
        elif message_type == "exam_paper_chunk":
            self.paper_chunks.append(payload.get("chunk", ""))
        elif message_type == "exam_paper_done":
            self.handle_exam_ready(payload.get("exam_name", ""))
        elif message_type == "submit_result":
            if self.lan_exam_window:
                self.lan_exam_window.handle_submit_result(payload)

    def handle_hello_ack(self, payload: dict) -> None:
        if not payload.get("success"):
            self.show_bar("连接失败", payload.get("message", ""), error=True)
            return
        self.client_id = payload.get("client_id", "")
        self.auth_mode = int(payload.get("auth_mode", 0))
        if self.auth_mode == 0:
            self.enabled_exams = payload.get("enabled_exams", [])
            self.finish_connection("")
            return
        dialog = LanExamAuthDialog(self.auth_mode, self)
        if not dialog.exec():
            if self.client_thread:
                self.client_thread.send_message({"type": "disconnect", "client_id": self.client_id})
            return
        username, password = dialog.credentials()
        self.username = username
        if self.client_thread:
            self.client_thread.send_message(
                {
                    "type": "auth_submit",
                    "client_id": self.client_id,
                    "device_name": self.device_name,
                    "ip_address": self.ip_address,
                    "username": username,
                    "password": password,
                }
            )

    def handle_auth_result(self, payload: dict) -> None:
        if not payload.get("success"):
            self.show_bar("认证失败", payload.get("message", ""), error=True)
            return
        self.enabled_exams = payload.get("enabled_exams", [])
        self.finish_connection(self.username)

    def finish_connection(self, username: str) -> None:
        self.username = username
        self.address_input.setEnabled(False)
        self.connect_button.setText("断开")
        self.finish_tip("连接成功", True)
        self.render_exam_list()

    def render_exam_list(self) -> None:
        keyword = self.search_edit.text().strip().lower() if hasattr(self, "search_edit") else ""
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        self.placeholder_label.setVisible(not self.enabled_exams)
        for exam in self.enabled_exams:
            if keyword and keyword not in exam["exam_name"].lower():
                continue
            card = LanExamCard(exam, self.content)
            card.enter_button.clicked.connect(lambda checked=False, data=exam: self.enter_exam(data))
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)

    def enter_exam(self, exam: dict) -> None:
        exam_password = ""
        if exam.get("has_password"):
            dialog = ExamPasswordDialog(exam["exam_name"], self)
            if not dialog.exec():
                return
            exam_password = dialog.password()
        self.pending_exam_name = exam["exam_name"]
        self.paper_chunks.clear()
        self.loading_dialog = LoadingMessageDialog("正在获取试题数据...", self)
        self.loading_dialog.show()
        if self.client_thread:
            self.client_thread.send_message(
                {
                    "type": "request_exam",
                    "client_id": self.client_id,
                    "exam_id": exam["exam_id"],
                    "exam_name": exam["exam_name"],
                    "exam_password": exam_password,
                }
            )

    def handle_exam_ready(self, exam_name: str) -> None:
        self.close_loading_dialog()
        paper = json.loads("".join(self.paper_chunks))
        self.store.save_paper(exam_name, paper)
        self.store.save_inputs(exam_name, {"subjects": {}})
        self.lan_exam_window = LanExamWindow(paper, self.wrong_manager, self.favorite_manager)
        self.lan_exam_window.submit_requested.connect(self.submit_exam)
        self.lan_exam_window.show()
        self.lan_exam_window.raise_()
        self.lan_exam_window.activateWindow()

    def submit_exam(self, payload: dict) -> None:
        if not self.client_thread:
            return
        self.client_thread.send_message(
            {
                "type": "submit_exam",
                "client_id": self.client_id,
                "device_name": self.device_name,
                "exam_id": payload["exam_id"],
                "exam_name": payload["exam_name"],
                "subjects": payload["subjects"],
            }
        )

    def on_disconnected(self, message: str) -> None:
        self.reset_connection_state()
        self.finish_tip(message, True)
        self.client_thread = None

    def on_connection_failed(self, message: str) -> None:
        self.reset_connection_state()
        self.client_thread = None
        self.finish_tip(message, False)

    def reset_connection_state(self) -> None:
        self.client_id = ""
        self.username = ""
        self.auth_mode = 0
        self.enabled_exams = []
        self.address_input.setEnabled(True)
        self.connect_button.setText("连接")
        self.close_loading_dialog()
        self.render_exam_list()

    def show_tip(self, title: str, content: str) -> None:
        if self.state_tooltip:
            self.state_tooltip.close()
        self.state_tooltip = StateToolTip(title, content, self)
        self.state_tooltip.show()
        self.state_tooltip.adjustSize()
        margin = 20
        self.state_tooltip.move(QPoint(max(self.width() - self.state_tooltip.width() - margin, margin), margin))

    def finish_tip(self, content: str, success: bool) -> None:
        if not self.state_tooltip:
            return
        self.state_tooltip.setContent(content)
        self.state_tooltip.setState(success)

    def show_bar(self, title: str, content: str, error: bool = False) -> None:
        if error:
            InfoBar.error(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)
        else:
            InfoBar.success(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)

    def close_loading_dialog(self) -> None:
        if self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None

    def _on_pivot_changed(self, route_key: str) -> None:
        self.stack.setCurrentIndex(self.route_to_index.get(route_key, 0))
