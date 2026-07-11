from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, ProgressBar

from ui.styles.home.base import HomeWelcomeStyle


class HomeStyleTwo(HomeWelcomeStyle):
    """样式二：用户信息下方显示横向目标进度。"""

    style_name = "样式二"

    def __init__(self, avatar_factory: Callable, radar_factory: Callable, parent=None):
        super().__init__(avatar_factory, radar_factory, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 10, 30, 10)
        layout.setSpacing(18)

        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 12, 0, 8)
        left_layout.setSpacing(7)
        identity_layout = QHBoxLayout()
        identity_layout.setSpacing(14)
        identity_layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignTop)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 9, 0, 0)
        text_layout.setSpacing(2)
        title_font = QFont(self.greeting_label.font())
        title_font.setPointSize(17)
        self.greeting_label.setFont(title_font)
        text_layout.addWidget(self.greeting_label)
        text_layout.addWidget(self.subtitle_label)
        text_layout.addStretch(1)
        identity_layout.addLayout(text_layout, 1)
        left_layout.addLayout(identity_layout)

        goal_widget = QWidget(left)
        goal_widget.setFixedWidth(300)
        goal_layout = QVBoxLayout(goal_widget)
        goal_layout.setContentsMargins(0, 0, 0, 0)
        goal_layout.setSpacing(3)
        header = QHBoxLayout()
        header.addWidget(CaptionLabel("每日目标完成度", goal_widget))
        header.addStretch(1)
        self.percent_label = CaptionLabel("0%", goal_widget)
        header.addWidget(self.percent_label)
        self.progress = ProgressBar(goal_widget)
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(4)
        goal_layout.addLayout(header)
        goal_layout.addWidget(self.progress)
        left_layout.addWidget(goal_widget, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(left, 1)
        layout.addWidget(self.radar, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_completion(self, completion: float) -> None:
        self.percent_label.setText(f"{completion:.0f}%")
        self.progress.setValue(min(round(completion), 100))
