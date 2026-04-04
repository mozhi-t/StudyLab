from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import LineEdit, PrimaryPushButton, PushButton

from config.settings import SUBJECTS
from ui.widgets.question_card import QuestionCard, bank_card_title
from ui.widgets.question_detail_dialog import QuestionDetailDialog


class WrongBookPage(QWidget):
    def __init__(self, wrong_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.wrong_manager = wrong_manager
        self.current_page = 1
        self.total_count = 0
        self.cards: list[QuestionCard] = []

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索错题")
        self.search_edit.textChanged.connect(self._reset_then_reload)
        self.subject_combo = QComboBox(self)
        self.subject_combo.addItem("全部科目", "")
        for key, label in SUBJECTS.items():
            self.subject_combo.addItem(label, key)
        self.subject_combo.currentIndexChanged.connect(self._reset_then_reload)
        self.refresh_button = PrimaryPushButton("刷新", self)
        self.refresh_button.clicked.connect(self.refresh_index)
        top.addWidget(self.search_edit)
        top.addWidget(self.subject_combo)
        top.addWidget(self.refresh_button)
        root.addLayout(top)

        self.page_info = QLabel("", self)
        root.addWidget(self.page_info)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.content = QWidget(self.scroll)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

        pager = QHBoxLayout()
        prev_button = PushButton("上一页", self)
        next_button = PushButton("下一页", self)
        prev_button.clicked.connect(self.prev_page)
        next_button.clicked.connect(self.next_page)
        pager.addWidget(prev_button)
        pager.addWidget(next_button)
        root.addLayout(pager)

        self.reload()

    def _reset_then_reload(self):
        self.current_page = 1
        self.reload()

    def refresh_index(self):
        self.wrong_manager.refresh_index()
        self.reload()

    def reload(self):
        subject = self.subject_combo.currentData()
        items, total = self.wrong_manager.list_wrongs(subject=subject or None, keyword=self.search_edit.text(), page=self.current_page)
        self.total_count = total
        self._clear_cards()
        for item in items:
            card = QuestionCard(
                title=bank_card_title(item.subject, item.bank_name),
                subtitle=item.question,
                meta=f"错误次数：{item.error_count}",
                checkable=True,
                parent=self.content,
            )
            card.mouseDoubleClickEvent = lambda event, payload=item: self.show_detail(payload)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)
        self.page_info.setText(f"共 {total} 条错题")

    def show_detail(self, item):
        QuestionDetailDialog(item.bank_name, item.question, item.options, item.answer, item.explanation, self).exec()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.reload()

    def next_page(self):
        max_page = max((self.total_count - 1) // 50 + 1, 1)
        if self.current_page < max_page:
            self.current_page += 1
            self.reload()

    def _clear_cards(self):
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
