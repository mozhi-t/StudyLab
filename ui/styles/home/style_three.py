from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, ProgressRing

from ui.styles.home.base import HomeWelcomeStyle


class HomeStyleThree(HomeWelcomeStyle):
    """样式三：右侧显示目标进度，能力图移至主页下方独立卡片。"""

    style_name = "样式三"
    shows_separate_ability_card = True

    def __init__(self, avatar_factory: Callable, radar_factory: Callable, parent=None):
        super().__init__(avatar_factory, radar_factory, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 10, 30, 10)
        layout.setSpacing(18)

        identity = QWidget(self)
        identity_layout = QHBoxLayout(identity)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(14)
        identity_layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_font = QFont(self.greeting_label.font())
        title_font.setPointSize(18)
        self.greeting_label.setFont(title_font)
        text_layout.addWidget(self.greeting_label)
        text_layout.addWidget(self.subtitle_label)
        identity_layout.addLayout(text_layout, 1)
        layout.addWidget(identity, 1)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setFixedHeight(104)
        separator.setStyleSheet("QFrame{color: rgba(128, 128, 128, 0.32); max-width: 1px;}")
        layout.addWidget(separator, 0, Qt.AlignmentFlag.AlignVCenter)

        goal_widget = QWidget(self)
        goal_widget.setFixedWidth(245)
        goal_layout = QVBoxLayout(goal_widget)
        goal_layout.setContentsMargins(0, 4, 0, 4)
        goal_layout.setSpacing(4)
        goal_title = CaptionLabel("每日目标完成度", goal_widget)
        goal_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress = ProgressRing(goal_widget)
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setFixedSize(82, 82)
        goal_layout.addWidget(goal_title)
        goal_layout.addWidget(self.progress, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(goal_widget, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_completion(self, completion: float) -> None:
        self.progress.setValue(min(round(completion), 100))
