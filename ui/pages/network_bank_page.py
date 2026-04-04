from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, LineEdit, PrimaryPushButton
from ui.widgets.styled_card import StyledCardWidget


class NetworkBankPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.connect_card = StyledCardWidget(self)
        connect_root = QVBoxLayout(self.connect_card)
        connect_root.setContentsMargins(20, 20, 20, 20)
        connect_widget = QWidget(self.connect_card)
        connect_layout = QVBoxLayout(connect_widget)
        self.url_edit = LineEdit(self)
        self.url_edit.setPlaceholderText("输入题库地址")
        self.connect_button = PrimaryPushButton("连接", self)
        connect_layout.addWidget(self.url_edit)
        connect_layout.addWidget(self.connect_button)
        connect_root.addWidget(connect_widget)
        layout.addWidget(self.connect_card)

        self.list_card = StyledCardWidget(self)
        list_root = QVBoxLayout(self.list_card)
        list_root.setContentsMargins(20, 20, 20, 20)
        list_widget = QWidget(self.list_card)
        list_layout = QVBoxLayout(list_widget)
        list_layout.addWidget(BodyLabel("网络题库下载接口预留，待接入实际服务协议。", self))
        list_root.addWidget(list_widget)
        layout.addWidget(self.list_card, 1)
