from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PillPushButton


class AnswerCard(QWidget):
    question_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.buttons: list[PillPushButton] = []
        self.grid = QGridLayout()
        self.summary_label = QLabel("已答题数: 0 / 未答题数: 0", self)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        root = QVBoxLayout(self)
        root.addLayout(self.grid)
        root.addWidget(self.summary_label)

    def set_questions(self, count: int) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.buttons.clear()
        columns = 4
        for idx in range(count):
            button = PillPushButton(str(idx + 1), self)
            button.clicked.connect(lambda checked=False, i=idx: self.question_selected.emit(i))
            self.grid.addWidget(button, idx // columns, idx % columns)
            self.buttons.append(button)
        self.update_status(set(), 0)

    def update_status(self, answered_indices: set[int], current_index: int) -> None:
        for idx, button in enumerate(self.buttons):
            button.setChecked(idx == current_index)
            button.setText(f"{idx + 1}*" if idx in answered_indices else str(idx + 1))
        total = len(self.buttons)
        answered = len(answered_indices)
        self.summary_label.setText(f"已答题数: {answered} / 未答题数: {total - answered}")
