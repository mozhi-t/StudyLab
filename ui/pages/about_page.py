from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, SubtitleLabel
from ui.styles.title_style import apply_page_title_style


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        self.page_title = SubtitleLabel("关于", self)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)
        layout.addStretch(1)
        for label in [
            SubtitleLabel("Study Lab", self),
            BodyLabel("MoZhi", self),
            CaptionLabel("Beta 开发版本", self),
        ]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        layout.addStretch(1)
