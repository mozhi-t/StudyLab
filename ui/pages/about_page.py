from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, HeaderCardWidget, SubtitleLabel
from ui.styles.title_style import apply_page_title_style
from ui.widgets.styled_card import StyledCardWidget


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        self.page_title = SubtitleLabel("关于", self)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)
        self.main_card = StyledCardWidget(self)
        card_layout = QVBoxLayout(self.main_card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        layout.addStretch(1)
        self.about_card = HeaderCardWidget("关于项目", self.main_card)
        card_widget = QWidget(self.about_card)
        info_layout = QVBoxLayout(card_widget)
        for label in [
            SubtitleLabel("Study Lab", self),
            BodyLabel("MoZhi", self),
            CaptionLabel("Beta 开发版本", self),
        ]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_layout.addWidget(label)
        self.about_card.viewLayout.addWidget(card_widget)
        card_layout.addWidget(self.about_card)
        layout.addWidget(self.main_card)
        layout.addStretch(1)
