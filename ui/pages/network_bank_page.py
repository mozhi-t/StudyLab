from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import LineEdit, PrimaryPushButton


class NetworkBankPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.url_edit = LineEdit(self)
        self.url_edit.setPlaceholderText("输入题库地址")
        self.connect_button = PrimaryPushButton("连接", self)
        layout.addWidget(self.url_edit)
        layout.addWidget(self.connect_button)
        layout.addWidget(QLabel("网络题库下载接口预留，待接入实际服务协议。", self))
        layout.addStretch(1)
