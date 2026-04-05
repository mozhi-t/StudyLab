from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel

from ui.widgets.styled_card import StyledCardWidget


class QuestionStatusCard(StyledCardWidget):
    clicked = pyqtSignal()

    def __init__(self, text: str, parent: QWidget | None = None):
        self._state = "default"
        self._is_current = False
        self._display_text = text
        super().__init__(parent, radius=10, light_border_alpha=34)
        self.setFixedSize(36, 36)

        self.label = BodyLabel(text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self.label.font())
        font.setPointSize(9)
        font.setBold(True)
        self.label.setFont(font)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

    def set_state(self, state: str, is_current: bool = False, display_text: str | None = None) -> None:
        self._state = state
        self._is_current = is_current
        if display_text is not None:
            self._display_text = display_text
            self.label.setText(display_text)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _normalBackgroundColor(self):
        if self._state == "correct":
            return QColor(15, 163, 97, 235)
        if self._state == "wrong":
            return QColor(224, 72, 72, 235)
        if self._state == "pending":
            return QColor(0, 120, 212, 235)
        if self._state == "marked":
            return QColor(243, 156, 18, 235)
        return super()._normalBackgroundColor()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._is_current:
            self._apply_text_color()
            return

        from PyQt6.QtGui import QPainter

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        pen_color = QColor(255, 255, 255, 140) if self._state in {"correct", "wrong", "pending", "marked"} else QColor(0, 120, 212, 170)
        pen = painter.pen()
        pen.setColor(pen_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)
        self._apply_text_color()

    def _apply_text_color(self) -> None:
        if self._state in {"correct", "wrong", "pending", "marked"}:
            self.label.setStyleSheet("color: white;")
        else:
            self.label.setStyleSheet("")


class AnswerCard(QWidget):
    question_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.buttons: list[QuestionStatusCard] = []
        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(4)
        self.grid.setVerticalSpacing(4)

        self.summary_card = StyledCardWidget(self, radius=12, light_border_alpha=34)
        self.summary_label = BodyLabel("已做题数：0/0", self.summary_card)
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
