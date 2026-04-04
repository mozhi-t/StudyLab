from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, SubtitleLabel, TransparentPushButton
from ui.styles.title_style import apply_page_title_style


class HomePage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(24)

        self.page_title = SubtitleLabel("主页", self)
        apply_page_title_style(self.page_title)
        root.addWidget(self.page_title)
        root.addStretch(1)

        greeting = SubtitleLabel(self._greeting(), self)
        greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(greeting)

        description = BodyLabel("从主页快速进入本地题库、错题本或收藏夹。", self)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(description)

        quick_widget = QWidget(self)
        button_row = QVBoxLayout(quick_widget)
        button_row.setSpacing(10)
        for key, text in [("local_bank", "开始刷题"), ("wrong_book", "错题本"), ("favorite", "收藏夹")]:
            button = TransparentPushButton(text, self)
            button.clicked.connect(lambda checked=False, page=key: self.navigate_requested.emit(page))
            button_row.addWidget(button)
        root.addWidget(quick_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

    def _greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            return "早上好，今天的学习计划是什么？"
        if hour < 18:
            return "下午好，保持节奏，今天的你离目标又近了一步。"
        return "晚上好，早点休息吧，明天再继续努力。"
