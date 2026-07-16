from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, isDarkTheme

from ui.widgets.base.question_status_card import QuestionStatusCard
from ui.widgets.base.styled_card import StyledCardWidget


class AnswerCard(QWidget):
    question_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.buttons: list[QuestionStatusCard] = []
        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(4)
        self.grid.setVerticalSpacing(4)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.summary_card = StyledCardWidget(self, radius=12, light_border_alpha=34)
        self.summary_label = BodyLabel("已做题数：0/0", self.summary_card)
        if isDarkTheme():
            self.summary_label.setStyleSheet("color: white;")
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        summary_layout.addWidget(self.summary_label, 0, Qt.AlignmentFlag.AlignLeft)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        root.addLayout(self.grid)
        root.addWidget(self.summary_card)

    def set_questions(self, count: int) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.buttons.clear()

        columns = 6
        for idx in range(count):
            button = QuestionStatusCard(str(idx + 1), self)
            button.clicked.connect(lambda i=idx: self.question_selected.emit(i))
            self.grid.addWidget(button, idx // columns, idx % columns)
            self.buttons.append(button)

        self.update_status({}, 0)

    def update_status(self, results: dict[int, bool], current_index: int) -> None:
        answered = 0
        for idx, button in enumerate(self.buttons):
            if idx not in results:
                state = "default"
            elif results[idx]:
                state = "correct"
                answered += 1
            else:
                state = "wrong"
                answered += 1
            button.set_state(state, is_current=idx == current_index)

        total = len(self.buttons)
        self.summary_label.setText(f"已做题数：{answered}/{total}")

    def update_exam_status(self, states: dict[int, dict], current_index: int) -> None:
        answered = 0
        for idx, button in enumerate(self.buttons):
            payload = states.get(idx, {})
            state = payload.get("state", "default")
            marked = payload.get("marked", False)
            answered_flag = payload.get("answered", False)
            if answered_flag:
                answered += 1
            display_text = str(idx + 1)
            if marked and answered_flag:
                display_text += "*"
            button.set_state(state, is_current=idx == current_index, display_text=display_text)
        total = len(self.buttons)
        self.summary_label.setText(f"已做题数：{answered}/{total}")
