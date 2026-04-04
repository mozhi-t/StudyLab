from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, ElevatedCardWidget, StrongBodyLabel


class SettingItemCard(ElevatedCardWidget):
    def __init__(self, title: str, description: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        text_layout = QVBoxLayout()
        self.title_label = StrongBodyLabel(title, self)
        self.description_label = CaptionLabel(description, self)
        self.description_label.setWordWrap(True)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.description_label)
        text_layout.addStretch(1)

        root.addLayout(text_layout, 1)
        root.addWidget(control)
