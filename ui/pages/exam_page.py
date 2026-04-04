from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, Pivot, SubtitleLabel
from ui.styles.title_style import apply_page_title_style


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
        self._add_item("local_exam", "本地考试", "正在积极开发中...")
        self._add_item("lan_exam", "局域网考试", "马上就好")
        self.pivot.setCurrentItem("local_exam")
        self.stack.setCurrentIndex(0)

    def _add_item(self, route_key: str, text: str, content: str) -> None:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        label = BodyLabel(content, page)
        page_layout.addWidget(label)
        page_layout.addStretch(1)
        self.stack.addWidget(page)
        index = self.stack.indexOf(page)
        self.route_to_index[route_key] = index
        self.pivot.addItem(
            routeKey=route_key,
            text=text,
            onClick=lambda: None,
        )

    def _on_pivot_changed(self, route_key: str) -> None:
        index = self.route_to_index.get(route_key, 0)
        self.stack.setCurrentIndex(index)
