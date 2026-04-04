from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, CheckBox, PushButton

from config.settings import SUBJECTS


class QuestionCard(CardWidget):
    def __init__(
        self,
        title: str,
        subtitle: str,
        meta: str = "",
        action_text: str | None = None,
        checkable: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.checkbox = CheckBox(self) if checkable else None
        self.action_button = PushButton(action_text, self) if action_text else None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        if self.checkbox:
            layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        self.title_label = QLabel(title, self)
        self.subtitle_label = QLabel(subtitle, self)
        self.meta_label = QLabel(meta, self)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.subtitle_label.setWordWrap(True)
        self.meta_label.setStyleSheet("color: gray;")
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.subtitle_label)
        if meta:
            text_layout.addWidget(self.meta_label)
        layout.addLayout(text_layout, 1)

        if self.action_button:
            layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignVCenter)


def bank_card_title(subject: str, bank_name: str) -> str:
    return f"{SUBJECTS.get(subject, subject)} · {bank_name}"
