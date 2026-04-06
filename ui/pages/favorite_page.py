from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ComboBox, LineEdit, PipsPager, PipsScrollButtonDisplayMode, SingleDirectionScrollArea, SubtitleLabel

from config.settings import SUBJECTS
from ui.styles.title_style import apply_page_title_style
from ui.widgets.question_card import QuestionCard
from ui.widgets.question_detail_dialog import QuestionDetailDialog
from ui.widgets.styled_card import StyledCardWidget


class FavoritePage(QWidget):
    def __init__(self, favorite_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.favorite_manager = favorite_manager
        self.current_page = 1
        self.total_count = 0
        self.cards: list[QuestionCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        self.page_title = SubtitleLabel("收藏夹", self)
        apply_page_title_style(self.page_title)
        root.addWidget(self.page_title)

        self.filter_card = StyledCardWidget(self)
        filter_layout = QVBoxLayout(self.filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_widget = QWidget(self.filter_card)
        top = QHBoxLayout(filter_widget)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        self.subject_combo = ComboBox(self)
        self.subject_combo.addItem("全部科目", "")
        for key, label in SUBJECTS.items():
            self.subject_combo.addItem(label, userData=key)
        self.subject_combo.currentIndexChanged.connect(self._reset_then_reload)
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索收藏题目")
        self.search_edit.textChanged.connect(self._reset_then_reload)
        top.addWidget(self.subject_combo)
        top.addWidget(self.search_edit, 1)
        filter_layout.addWidget(filter_widget)
        root.addWidget(self.filter_card)

        self.list_card = StyledCardWidget(self)
        list_layout_root = QVBoxLayout(self.list_card)
        list_layout_root.setContentsMargins(10, 10, 10, 10)
        list_layout_root.setSpacing(10)
        list_widget = QWidget(self.list_card)
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        self.page_info = BodyLabel("", self)
        self.page_info.hide()
        list_layout.addWidget(self.page_info)

        self.scroll = SingleDirectionScrollArea(self, Qt.Orientation.Vertical)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget(self.scroll)
        self.content.setObjectName("favoriteListContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        self.scroll.enableTransparentBackground()
        self.content.setStyleSheet("QWidget#favoriteListContent{background: transparent; border: none;}")
        list_layout.addWidget(self.scroll, 1)

        pager = QHBoxLayout()
        self.pager = PipsPager(self)
        self.pager.setPreviousButtonDisplayMode(PipsScrollButtonDisplayMode.ALWAYS)
        self.pager.setNextButtonDisplayMode(PipsScrollButtonDisplayMode.ALWAYS)
        self.pager.currentIndexChanged.connect(self.on_page_changed)
        pager.addStretch(1)
        pager.addWidget(self.pager)
        pager.addStretch(1)
        list_layout.addLayout(pager)
        list_layout_root.addWidget(list_widget)
        root.addWidget(self.list_card, 1)

        self.reload()

    def _reset_then_reload(self):
        self.current_page = 1
        self.reload()

    def reload(self):
        subject = self.subject_combo.currentData()
        items, total = self.favorite_manager.list_favorites(subject=subject or None, keyword=self.search_edit.text(), page=self.current_page)
        self.total_count = total
        self._clear_cards()
        for item in items:
            card = QuestionCard(
                title=item.question,
                checkable=True,
                parent=self.content,
            )
            card.mouseDoubleClickEvent = lambda event, payload=item: self.show_detail(payload)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)
        max_page = max((self.total_count - 1) // 50 + 1, 1)
        self._sync_pager(max_page)

    def show_detail(self, item):
        QuestionDetailDialog(item.bank_name, item.question, item.options, item.answer, item.explanation, self).exec()

    def on_page_changed(self, index: int):
        page = index + 1
        if page != self.current_page:
            self.current_page = page
            self.reload()

    def _clear_cards(self):
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()

    def _sync_pager(self, max_page: int) -> None:
        self.pager.blockSignals(True)
        self.pager.setPageNumber(max_page)
        self.pager.setCurrentIndex(max(self.current_page - 1, 0))
        self.pager.blockSignals(False)
