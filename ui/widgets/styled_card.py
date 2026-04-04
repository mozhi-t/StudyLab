from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from qfluentwidgets import CardWidget


class StyledCardWidget(CardWidget):
    def __init__(self, parent=None, radius: int = 12, background_alpha: int = 232, border_alpha: int = 28):
        self._base_color = QColor(255, 255, 255, background_alpha)
        super().__init__(parent)
        self.setBorderRadius(radius)
        self.setBackgroundColor(self._base_color)
        self._border_color = QColor(0, 0, 0, border_alpha)

    def _normalBackgroundColor(self):
        return self._base_color

    def _hoverBackgroundColor(self):
        return self._base_color

    def _pressedBackgroundColor(self):
        return self._base_color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = self.borderRadius
        d = 2 * r

        path = QPainterPath()
        path.arcMoveTo(1, h - d - 1, d, d, 240)
        path.arcTo(1, h - d - 1, d, d, 225, -60)
        path.lineTo(1, r)
        path.arcTo(1, 1, d, d, -180, -90)
        path.lineTo(w - r, 1)
        path.arcTo(w - d - 1, 1, d, d, 90, -90)
        path.lineTo(w - 1, h - r)
        path.arcTo(w - d - 1, h - d - 1, d, d, 0, -60)
        painter.strokePath(path, self._border_color)

        path = QPainterPath()
        path.arcMoveTo(1, h - d - 1, d, d, 240)
        path.arcTo(1, h - d - 1, d, d, 240, 30)
        path.lineTo(w - r - 1, h - 1)
        path.arcTo(w - d - 1, h - d - 1, d, d, 270, 30)
        painter.strokePath(path, self._border_color)

        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(self.backgroundColor)
        painter.drawRoundedRect(rect, r, r)
