from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, LineEdit, MessageBox, PipsPager, PipsScrollButtonDisplayMode, Pivot, SingleDirectionScrollArea, SubtitleLabel

from core.base.datetime_utils import format_datetime
from ui.styles.title_style import apply_page_title_style
from ui.widgets.base import QuestionCard, StyledCardWidget


class LocalBankPage(QWidget):
    open_bank_requested = pyqtSignal(str, str)

    SUBJECT_TABS = {
        "chinese": "语文",
        "math": "数学",
        "english": "英语",
        "computer_basic": "计算机基础",
        "python": "Python",
        "mysql": "MySQL",
    }

    def __init__(self, question_index_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.question_index_manager = question_index_manager
        self.current_subject = "chinese"
        self.current_page = 1
        self.total_count = 0
        self.page_size = 50
        self.cards: list[QuestionCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        self.page_title = SubtitleLabel("刷题", self)
        apply_page_title_style(self.page_title)
        root.addWidget(self.page_title)

        self.pivot = Pivot(self)
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        root.addLayout(nav_layout)
        for subject, text in self.SUBJECT_TABS.items():
            self.pivot.addItem(routeKey=subject, text=text, onClick=lambda: None)
        self.pivot.setCurrentItem(self.current_subject)

        self.filter_card = StyledCardWidget(self)
        filter_layout = QVBoxLayout(self.filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        toolbar_widget = QWidget(self.filter_card)
        toolbar = QVBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索题库")
        self.search_edit.textChanged.connect(self._reset_then_reload)
        toolbar.addWidget(self.search_edit)
        filter_layout.addWidget(toolbar_widget)
        root.addWidget(self.filter_card)

        self.list_card = StyledCardWidget(self)
        self.list_layout_root = QVBoxLayout(self.list_card)
        self.list_layout_root.setContentsMargins(10, 10, 10, 10)
        self.list_layout_root.setSpacing(10)
        self.scroll = SingleDirectionScrollArea(self.list_card, Qt.Orientation.Vertical)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget(self.scroll)
        self.content.setObjectName("bankListContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        self.scroll.enableTransparentBackground()
        self.content.setStyleSheet("QWidget#bankListContent{background: transparent; border: none;}")
        self.list_layout_root.addWidget(self.scroll, 1)

        pager = QHBoxLayout()
        self.pager = PipsPager(self)
        self.pager.setPreviousButtonDisplayMode(PipsScrollButtonDisplayMode.ALWAYS)
        self.pager.setNextButtonDisplayMode(PipsScrollButtonDisplayMode.ALWAYS)
        self.pager.currentIndexChanged.connect(self.on_page_changed)
        pager.addStretch(1)
        pager.addWidget(self.pager)
        pager.addStretch(1)
        self.list_layout_root.addLayout(pager)
        root.addWidget(self.list_card, 1)

        self.pivot.currentItemChanged.connect(self._on_subject_changed)
        self.reload()

    def _reset_then_reload(self):
        self.current_page = 1
        self.reload()

    def reload(self):
        keyword = self.search_edit.text()
        items, total = self.question_index_manager.list_banks(
            subject=self.current_subject,
            keyword=keyword,
            page=self.current_page,
            page_size=self.page_size,
        )
        self.total_count = total
        max_page = max((self.total_count - 1) // self.page_size + 1, 1)
        if self.current_page > max_page:
            self.current_page = max_page
        self._clear_cards()
        for item in items:
            card = QuestionCard(
                title=self._format_bank_title(item.subject, item.name),
                right_meta=f"创建时间：{format_datetime(item.create_time)}",
                action_text="删除",
                action_icon=FluentIcon.DELETE,
                parent=self.content,
            )
            if card.action_button:
                card.action_button.clicked.connect(lambda checked=False, s=item.subject, n=item.name: self.confirm_delete_bank(s, n))
            card.mouseDoubleClickEvent = lambda event, s=item.subject, n=item.name: self.confirm_open_bank(s, n)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)
        max_page = self._update_page_info()
        self._sync_pager(max_page)

    def confirm_open_bank(self, subject: str, bank_name: str) -> None:
        dialog = MessageBox("进入题库", f"是否要进入[{bank_name}]题库", self)
        dialog.yesButton.setText("进入")
        dialog.cancelButton.setText("取消")
        if dialog.exec():
            self.open_bank_requested.emit(subject, bank_name)

    def confirm_delete_bank(self, subject: str, bank_name: str) -> None:
        dialog = MessageBox("删除题库", f"是否要删除[{bank_name}]题库", self)
        dialog.yesButton.setText("删除")
        dialog.cancelButton.setText("取消")
        if dialog.exec():
            self.delete_bank(subject, bank_name)

    def delete_bank(self, subject: str, bank_name: str):
        self.question_index_manager.remove_bank(subject, bank_name)
        self.reload()

    def on_page_changed(self, index: int):
        page = index + 1
        if page == self.current_page:
            return
        self.current_page = page
        self.reload()

    def _on_subject_changed(self, route_key: str) -> None:
        self.current_subject = route_key
        self._reset_then_reload()

    def _clear_cards(self):
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()

    def _update_page_info(self) -> int:
        max_page = max((self.total_count - 1) // self.page_size + 1, 1)
        return max_page

    def _sync_pager(self, max_page: int) -> None:
        self.pager.blockSignals(True)
        self.pager.setPageNumber(max_page)
        self.pager.setCurrentIndex(max(self.current_page - 1, 0))
        self.pager.blockSignals(False)

    def _format_bank_title(self, subject: str, bank_name: str) -> str:
        return bank_name
