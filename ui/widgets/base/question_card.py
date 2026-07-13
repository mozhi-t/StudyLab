from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, CheckBox, FluentIcon, PushButton, StrongBodyLabel

from config.settings import SUBJECTS


class QuestionCard(CardWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        meta: str = "",
        action_text: str | None = None,
        action_icon=None,
        right_meta: str = "",
        checkable: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.checkbox = CheckBox(self) if checkable else None
        self.action_button = PushButton(action_text or "", self) if (action_text or action_icon) else None
        self.right_meta_label = CaptionLabel(right_meta, self) if right_meta else None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        if self.checkbox:
            layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        self.title_label = StrongBodyLabel(title, self)
        self.subtitle_label = BodyLabel(subtitle, self)
        self.meta_label = CaptionLabel(meta, self)
        self.subtitle_label.setWordWrap(True)
        self.meta_label.setWordWrap(True)
        text_layout.addWidget(self.title_label)
        if subtitle:
            text_layout.addWidget(self.subtitle_label)
        if meta:
            text_layout.addWidget(self.meta_label)
        layout.addLayout(text_layout, 1)

        if self.right_meta_label:
            layout.addWidget(self.right_meta_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        if self.action_button:
            if action_icon:
                self.action_button.setIcon(action_icon)
            if not action_text:
                self.action_button.setFixedWidth(36)
            layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignVCenter)


def bank_card_title(subject: str, bank_name: str) -> str:
    return f"{SUBJECTS.get(subject, subject)} · {bank_name}"
