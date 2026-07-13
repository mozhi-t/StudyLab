from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, SubtitleLabel, isDarkTheme, themeColor

from config.settings import SUBJECTS
from ui.widgets.base.styled_card import StyledCardWidget


class AbilityRadarWidget(QWidget):
    clicked = pyqtSignal()
    SUBJECT_LABELS = [SUBJECTS[key] for key in SUBJECTS]

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        expanded: bool = False,
        interactive: bool = True,
    ):
        super().__init__(parent)
        self._values = [50.0] * len(self.SUBJECT_LABELS)
        self._expanded = expanded
        self._interactive = interactive

        if expanded:
            self.setMinimumSize(560, 400)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            self.setFixedSize(245, 146)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.setAccessibleName("学科能力雷达图")
        if interactive:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("点击放大查看能力图")

    def set_values(self, values: dict[str, float]) -> None:
        self._values = [max(0.0, min(float(values.get(key, 50)), 100.0)) for key in SUBJECTS]
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._interactive and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        scale = min(self.width() / 245, self.height() / 146)
        label_size = min(13.0, max(9.0, 9.0 * scale)) if self._expanded else 9.0
        label_font = QFont(self.font())
        label_font.setPointSizeF(label_size)
        painter.setFont(label_font)
        metrics = painter.fontMetrics()

        center = QPointF(self.width() / 2, self.height() / 2 + 2)
        horizontal_margin = max(58.0, metrics.horizontalAdvance("计算机基础 100") / 2 + 18)
        vertical_margin = max(30.0, metrics.height() + 18.0)
        radius = max(min(self.width() / 2 - horizontal_margin, self.height() / 2 - vertical_margin), 28)
        axis_count = len(self.SUBJECT_LABELS)
        grid_color = QColor(255, 255, 255, 42) if isDarkTheme() else QColor(30, 30, 30, 35)
        text_color = QColor(235, 235, 235) if isDarkTheme() else QColor(55, 55, 55)
        accent = themeColor()

        grid_width = 1.4 if self._expanded else 1.0
        painter.setPen(QPen(grid_color, grid_width))
        for level in range(1, 6):
            level_radius = radius * level / 5
            painter.drawPolygon(self._polygon(center, level_radius, axis_count))
        for index in range(axis_count):
            point = self._point(center, radius, index, axis_count)
            painter.drawLine(center, point)

        radar_points = QPolygonF()
        for index, value in enumerate(self._values):
            radar_points.append(self._point(center, radius * value / 100, index, axis_count))
        painter.setPen(QPen(accent, 2.8 if self._expanded else 2.0))
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 72))
        painter.drawPolygon(radar_points)
        painter.setBrush(accent)
        point_radius = 4.0 if self._expanded else 2.5
        for point in radar_points:
            painter.drawEllipse(point, point_radius, point_radius)

        painter.setPen(text_color)
        label_offset = metrics.height() + (8 if self._expanded else 2)
        for index, (label, value) in enumerate(zip(self.SUBJECT_LABELS, self._values)):
            text = f"{label} {value:.0f}"
            point = self._point(center, radius + label_offset, index, axis_count)
            width = metrics.horizontalAdvance(text)
            painter.drawText(QPointF(point.x() - width / 2, point.y() + metrics.ascent() / 2), text)

    @staticmethod
    def _point(center: QPointF, radius: float, index: int, count: int) -> QPointF:
        angle = -math.pi / 2 + 2 * math.pi * index / count
        return QPointF(center.x() + radius * math.cos(angle), center.y() + radius * math.sin(angle))

    @classmethod
    def _polygon(cls, center: QPointF, radius: float, count: int) -> QPolygonF:
        return QPolygonF([cls._point(center, radius, index, count) for index in range(count)])


class AbilityRadarWindow(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("学科能力详情")
        self.resize(820, 620)
        self.setMinimumSize(640, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(6)
        root.addWidget(SubtitleLabel("学科能力", self))
        root.addWidget(CaptionLabel("各学科能力指数，满分为 100", self))

        radar_card = StyledCardWidget(self, radius=16)
        radar_layout = QVBoxLayout(radar_card)
        radar_layout.setContentsMargins(20, 18, 20, 20)
        self.radar = AbilityRadarWidget(radar_card, expanded=True, interactive=False)
        radar_layout.addWidget(self.radar)
        root.addWidget(radar_card, 1)

    def set_values(self, values: dict[str, float]) -> None:
        self.radar.set_values(values)
