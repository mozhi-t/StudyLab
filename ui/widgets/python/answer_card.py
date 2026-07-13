from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, SingleDirectionScrollArea, StrongBodyLabel

from ui.widgets.base import QuestionStatusCard, StyledCardWidget


class PythonAnswerCard(StyledCardWidget):
    question_selected = pyqtSignal(int)

    STATE_MAP = {
        "unstarted": "default",
        "modified": "marked",
        "full": "correct",
        "partial": "marked",
        "failed": "wrong",
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, radius=14, light_border_alpha=34)
        self.buttons: list[QuestionStatusCard] = []
        self.states: dict[int, str] = {}
        self.total_possible = 0.0

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 14, 12, 12)
        root.setSpacing(10)
        root.addWidget(StrongBodyLabel("答题卡", self))

        self.scroll = SingleDirectionScrollArea(self, Qt.Orientation.Vertical)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.enableTransparentBackground()
        self.content = QWidget(self.scroll)
        self.content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(7)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

        self.summary = BodyLabel("已提交：0/0\n总得分：0/0", self)
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

    def set_questions(self, count: int, total_possible: float = 0.0) -> None:
        for button in self.buttons:
            button.deleteLater()
        self.buttons.clear()
        self.total_possible = total_possible
        self.states = {index: "unstarted" for index in range(count)}
        for index in range(count):
            button = QuestionStatusCard(str(index + 1), self.content)
            button.setFixedSize(44, 44)
            button.clicked.connect(lambda i=index: self.question_selected.emit(i))
            self.list_layout.insertWidget(self.list_layout.count() - 1, button, 0, Qt.AlignmentFlag.AlignHCenter)
            self.buttons.append(button)
        self.refresh(0, {}, {})

    def refresh(self, current_index: int, states: dict[int, str], scores: dict[int, tuple[float, float]]) -> None:
        self.states.update(states)
        for index, button in enumerate(self.buttons):
            state = self.STATE_MAP.get(self.states.get(index, "unstarted"), "default")
            button.set_state(state, is_current=index == current_index)
        earned = sum(item[0] for item in scores.values())
        submitted = len(scores)
        self.summary.setText(f"已提交：{submitted}/{len(self.buttons)}\n总得分：{earned:g}/{self.total_possible:g}")
