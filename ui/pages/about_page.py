from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        for text, style in [
            ("Study Lab", "font-size: 28px; font-weight: 700;"),
            ("MoZhi", "font-size: 18px;"),
            ("Beta 开发版本", "font-size: 12px; color: gray;"),
        ]:
            label = QLabel(text, self)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(style)
            layout.addWidget(label)
        layout.addStretch(1)
