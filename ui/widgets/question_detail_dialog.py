from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout
from qfluentwidgets import MessageBoxBase, SubtitleLabel


class QuestionDetailDialog(MessageBoxBase):
    def __init__(self, title: str, question: str, options: dict[str, str], answer: str, explanation: str, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)

        content = QVBoxLayout()
        question_label = QLabel(f"题目：{question}", self)
        question_label.setWordWrap(True)
        content.addWidget(question_label)

        for key, value in options.items():
            option_label = QLabel(f"{key}. {value}", self)
            option_label.setWordWrap(True)
            content.addWidget(option_label)

        answer_label = QLabel(f"答案：{answer}", self)
        explanation_label = QLabel(f"解析：{explanation}", self)
        explanation_label.setWordWrap(True)
        content.addWidget(answer_label)
        content.addWidget(explanation_label)

        self.viewLayout.addLayout(content)
        self.yesButton.setText("关闭")
        self.cancelButton.hide()
