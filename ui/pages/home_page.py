from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import TransparentPushButton


class HomePage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(24)

        greeting = QLabel(self._greeting(), self)
        greeting.setStyleSheet("font-size: 28px; font-weight: 600;")
        root.addWidget(greeting)
        root.addStretch(1)

        button_row = QHBoxLayout()
        for key, text in [("local_bank", "开始刷题"), ("wrong_book", "错题本"), ("favorite", "收藏夹")]:
            button = TransparentPushButton(text, self)
            button.clicked.connect(lambda checked=False, page=key: self.navigate_requested.emit(page))
            button_row.addWidget(button)
        root.addLayout(button_row)
        root.addStretch(2)

    def _greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            return "早上好，今天的学习计划是什么？"
        if hour < 18:
            return "下午好，保持节奏，今天的你离目标又近了一步。"
        return "晚上好，早点休息吧，明天再继续努力。"
