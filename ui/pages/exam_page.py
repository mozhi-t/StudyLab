from __future__ import annotations

from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, HeaderCardWidget, SegmentedWidget


class ExamPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.exam_card = HeaderCardWidget("考试模式", self)
        card_widget = QWidget(self.exam_card)
        card_layout = QVBoxLayout(card_widget)
        self.segmented = SegmentedWidget(self)
        self.stack = QStackedWidget(self)
        card_layout.addWidget(self.segmented)
        card_layout.addWidget(self.stack, 1)
        self.exam_card.viewLayout.addWidget(card_widget)
        layout.addWidget(self.exam_card, 1)

        self._add_page("local_exam", "本地考试")
        self._add_page("lan_exam", "局域网考试")
        self.segmented.setCurrentItem("local_exam")
        self.stack.setCurrentIndex(0)

    def _add_page(self, route_key: str, text: str) -> None:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(BodyLabel("正在开发中", page))
        page_layout.addStretch(1)
        self.stack.addWidget(page)
        index = self.stack.indexOf(page)
        self.segmented.addItem(
            routeKey=route_key,
            text=text,
            onClick=lambda i=index: self.stack.setCurrentIndex(i),
        )
