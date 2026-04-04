from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, LineEdit, PrimaryPushButton, SubtitleLabel
from ui.styles.title_style import apply_page_title_style
from ui.widgets.styled_card import StyledCardWidget


class NetworkBankPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.page_title = SubtitleLabel("网络题库", self)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)

        self.connect_card = StyledCardWidget(self)
        connect_root = QVBoxLayout(self.connect_card)
        connect_root.setContentsMargins(12, 12, 12, 12)
        connect_widget = QWidget(self.connect_card)
        connect_layout = QHBoxLayout(connect_widget)
        connect_layout.setContentsMargins(0, 0, 0, 0)
        connect_layout.setSpacing(8)
        self.url_edit = LineEdit(self)
        self.url_edit.setPlaceholderText("输入题库地址")
        self.connect_button = PrimaryPushButton("连接", self)
        connect_layout.addWidget(self.url_edit)
        connect_layout.addWidget(self.connect_button)
        connect_root.addWidget(connect_widget)
        layout.addWidget(self.connect_card)

        self.list_card = StyledCardWidget(self)
        list_root = QVBoxLayout(self.list_card)
        list_root.setContentsMargins(10, 10, 10, 10)
        self.result_container = QWidget(self.list_card)
        result_layout = QVBoxLayout(self.result_container)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.addWidget(BodyLabel("网络题库下载接口预留，待接入实际服务协议。", self))
        self.result_container.setStyleSheet("background: transparent; border: none;")
        list_root.addWidget(self.result_container)
        layout.addWidget(self.list_card, 1)
