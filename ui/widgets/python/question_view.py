from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import PrimaryPushButton, StrongBodyLabel

from ui.widgets.styled_card import StyledCardWidget


class PythonQuestionView(StyledCardWidget):
    answer_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, radius=14, light_border_alpha=34)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        self.title = StrongBodyLabel("题目内容", self)
        self.content = QPlainTextEdit(self)
        self.content.setReadOnly(True)
        self.content.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.content.setStyleSheet("QPlainTextEdit{font-family: Consolas; background: transparent; border: none;}")
        self.answer_button = PrimaryPushButton("答题", self)
        self.answer_button.clicked.connect(self.answer_requested)
        layout.addWidget(self.title)
        layout.addWidget(self.content, 1)
        layout.addWidget(self.answer_button, 0, Qt.AlignmentFlag.AlignRight)

    def set_question(self, question_id: int, source: str) -> None:
        self.title.setText(f"第 {question_id} 题")
        self.content.setPlainText(source)
