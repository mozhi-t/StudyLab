from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget


class ExamPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        for name in ["本地考试", "局域网考试"]:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.addWidget(QLabel("正在开发中", page))
            page_layout.addStretch(1)
            tabs.addTab(page, name)
        layout.addWidget(tabs)
