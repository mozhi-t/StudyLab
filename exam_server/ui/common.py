from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import QHBoxLayout, QSpacerItem, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, CardWidget, IconWidget, StrongBodyLabel, isDarkTheme


def apply_page_title_style(label) -> None:
    font = QFont(label.font())
    font.setPointSize(18)
    font.setWeight(QFont.Weight.DemiBold)
    label.setFont(font)


class StyledCardWidget(CardWidget):
    def __init__(self, parent=None, radius: int = 12, light_border_alpha: int = 28):
        self._light_border_alpha = light_border_alpha
        super().__init__(parent)
        self.setBorderRadius(radius)

    def _normalBackgroundColor(self):
        return QColor(255, 255, 255, 13 if isDarkTheme() else 170)

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = self.borderRadius
        d = 2 * r
        is_dark = isDarkTheme()
        background_color = self._normalBackgroundColor()

        path = QPainterPath()
        path.arcMoveTo(1, h - d - 1, d, d, 240)
        path.arcTo(1, h - d - 1, d, d, 225, -60)
        path.lineTo(1, r)
        path.arcTo(1, 1, d, d, -180, -90)
        path.lineTo(w - r, 1)
        path.arcTo(w - d - 1, 1, d, d, 90, -90)
        path.lineTo(w - 1, h - r)
        path.arcTo(w - d - 1, h - d - 1, d, d, 0, -60)

        top_border_color = QColor(255, 255, 255, 13) if is_dark else QColor(0, 0, 0, self._light_border_alpha)
        painter.strokePath(path, top_border_color)

        path = QPainterPath()
        path.arcMoveTo(1, h - d - 1, d, d, 240)
        path.arcTo(1, h - d - 1, d, d, 240, 30)
        path.lineTo(w - r - 1, h - 1)
        path.arcTo(w - d - 1, h - d - 1, d, d, 270, 30)
        painter.strokePath(path, top_border_color)

        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(background_color)
        painter.drawRoundedRect(rect, r, r)


class PreferenceRow(QWidget):
    def __init__(self, icon, title: str, description: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.setSpacing(0)
        root.addSpacerItem(QSpacerItem(8, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        self.icon_widget = IconWidget(icon, self)
        self.icon_widget.setFixedSize(20, 20)
        root.addWidget(self.icon_widget)
        root.addSpacerItem(QSpacerItem(28, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.addWidget(StrongBodyLabel(title, self))
        desc_label = CaptionLabel(description, self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {'rgba(255, 255, 255, 0.62)' if isDarkTheme() else '#7a7a7a'};")
        text_layout.addWidget(desc_label)
        root.addLayout(text_layout, 1)
        root.addWidget(control)


class PreferenceCard(StyledCardWidget):
    def __init__(self, icon, title: str, description: str, control: QWidget, parent: QWidget | None = None):
        super().__init__(parent, radius=10)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 16, 12)
        layout.addWidget(PreferenceRow(icon, title, description, control, self))
