from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import Pivot, SubtitleLabel

from ui.styles.title_style import apply_page_title_style
from ui.widgets.styled_card import StyledCardWidget


class NetworkBankPage(QWidget):
    PAGE_TABS = {
        "question_manage": "题目管理",
        "local_paper": "本地组卷",
        "smart_paper": "智能组卷",
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_page = "question_manage"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.page_title = SubtitleLabel("题库", self)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)

        self.pivot = Pivot(self)
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        layout.addLayout(nav_layout)

        self.page_stack = QStackedWidget(self)
        for route_key, text in self.PAGE_TABS.items():
            self.pivot.addItem(routeKey=route_key, text=text, onClick=lambda: None)
            self.page_stack.addWidget(self._create_blank_page(route_key))
        self.pivot.setCurrentItem(self.current_page)

        layout.addWidget(self.page_stack, 1)
        self.pivot.currentItemChanged.connect(self._on_page_changed)

    def _create_blank_page(self, route_key: str) -> QWidget:
        card = StyledCardWidget(self)
        card.setObjectName(f"{route_key}Page")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.addStretch(1)
        return card

    def _on_page_changed(self, route_key: str) -> None:
        self.current_page = route_key
        index = list(self.PAGE_TABS).index(route_key)
        self.page_stack.setCurrentIndex(index)
