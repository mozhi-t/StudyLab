from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, isDarkTheme

from ui.widgets.base.styled_card import StyledCardWidget


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

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        pen_color = (
            QColor(255, 255, 255, 140)
            if self._state in {"correct", "wrong", "pending", "marked"}
            else QColor(0, 120, 212, 170)
        )
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
        elif isDarkTheme():
            self.label.setStyleSheet("color: white;")
        else:
            self.label.setStyleSheet("")
