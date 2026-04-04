from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, Pivot, PrimaryPushButton, SubtitleLabel, LineEdit

from ui.styles.title_style import apply_page_title_style
from ui.widgets.styled_card import StyledCardWidget


class ExamPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.page_title = SubtitleLabel("考试", self)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)

        self.pivot = Pivot(self)
        self.pivot.currentItemChanged.connect(self._on_pivot_changed)
        self.stack = QStackedWidget(self)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        layout.addLayout(nav_layout)
        layout.addWidget(self.stack, 1)

        self.route_to_index = {}
        self._add_page("local_exam", "本地考试", self._build_local_exam_page())
        self._add_page("lan_exam", "局域网考试", self._build_lan_exam_page())
        self.pivot.setCurrentItem("local_exam")
        self.stack.setCurrentIndex(0)

    def _add_page(self, route_key: str, text: str, page: QWidget) -> None:
        self.stack.addWidget(page)
        index = self.stack.indexOf(page)
        self.route_to_index[route_key] = index
        self.pivot.addItem(routeKey=route_key, text=text, onClick=lambda: None)

    def _build_local_exam_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = BodyLabel("正在积极开发中...", page)
        layout.addWidget(label)
        layout.addStretch(1)
        return page

    def _build_lan_exam_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.connect_card = StyledCardWidget(page)
        connect_layout = QHBoxLayout(self.connect_card)
        connect_layout.setContentsMargins(12, 12, 12, 12)
        connect_layout.setSpacing(10)
        self.address_input = LineEdit(self.connect_card)
        self.address_input.setPlaceholderText("输入局域网考试地址")
        self.connect_button = PrimaryPushButton("连接", self.connect_card)
        connect_layout.addWidget(self.address_input, 1)
        connect_layout.addWidget(self.connect_button)
        layout.addWidget(self.connect_card)

        self.content_card = StyledCardWidget(page)
        content_layout = QVBoxLayout(self.content_card)
        content_layout.setContentsMargins(12, 12, 12, 12)
        self.placeholder_label = BodyLabel("局域网考试连接结果将在这里显示", self.content_card)
        content_layout.addWidget(self.placeholder_label)
        content_layout.addStretch(1)
        layout.addWidget(self.content_card, 1)

        return page

    def _on_pivot_changed(self, route_key: str) -> None:
        index = self.route_to_index.get(route_key, 0)
        self.stack.setCurrentIndex(index)
