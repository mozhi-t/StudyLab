from __future__ import annotations

from PyQt6.QtCore import QPoint, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import ComboBox, FluentIcon, LineEdit, PipsPager, PrimaryPushButton, SingleDirectionScrollArea, StateToolTip, SubtitleLabel

from config.settings import SUBJECTS
from ui.styles.title_style import apply_page_title_style
from ui.widgets.index_refresh_dialog import IndexRefreshDialog
from ui.widgets.question_card import QuestionCard, bank_card_title
from ui.widgets.styled_card import StyledCardWidget


class IndexRefreshThread(QThread):
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        try:
            self.completed.emit(self.manager.refresh_index())
        except Exception as exc:
            self.failed.emit(str(exc))


class LocalBankPage(QWidget):
    open_bank_requested = pyqtSignal(str, str)

    def __init__(self, question_index_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.question_index_manager = question_index_manager
        self.current_page = 1
        self.total_count = 0
        self.page_size = 50
        self.cards: list[QuestionCard] = []
        self.refresh_thread: IndexRefreshThread | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        self.page_title = SubtitleLabel("本地题库", self)
        apply_page_title_style(self.page_title)
        root.addWidget(self.page_title)

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

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        self.subject_combo = ComboBox(self)
        self.subject_combo.addItem("全部科目", "")
        for key, label in SUBJECTS.items():
            self.subject_combo.addItem(label, key)
        self.subject_combo.currentIndexChanged.connect(self._reset_then_reload)
        filter_row.addWidget(self.subject_combo)

        self.refresh_button = PrimaryPushButton("刷新索引", self)
        self.refresh_button.clicked.connect(self.refresh_index)
        filter_row.addWidget(self.refresh_button)
        toolbar.addLayout(filter_row)
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
        self.pager.currentIndexChanged.connect(self.on_page_changed)
        pager.addStretch(1)
        pager.addWidget(self.pager)
        pager.addStretch(1)
        self.list_layout_root.addLayout(pager)
        root.addWidget(self.list_card, 1)

        self.reload()

    def _reset_then_reload(self):
        self.current_page = 1
        self.reload()

    def reload(self):
        subject = self.subject_combo.currentData()
        keyword = self.search_edit.text()
        items, total = self.question_index_manager.list_banks(
            subject=subject or None,
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
                title=bank_card_title(item.subject, item.name),
                right_meta=f"创建时间：{item.create_time}",
                action_text="删除",
                action_icon=FluentIcon.DELETE,
                parent=self.content,
            )
            if card.action_button:
                card.action_button.clicked.connect(lambda checked=False, s=item.subject, n=item.name: self.delete_bank(s, n))
            card.mouseDoubleClickEvent = lambda event, s=item.subject, n=item.name: self.open_bank_requested.emit(s, n)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)
        max_page = self._update_page_info()
        self._sync_pager(max_page)

    def refresh_index(self):
        dialog = IndexRefreshDialog(self)
        if not dialog.exec():
            return
        tooltip = StateToolTip("正在检查题库...", "请稍后", self)
        tooltip.show()
        self._move_tooltip_top_right(tooltip)
        self.refresh_thread = IndexRefreshThread(self.question_index_manager)
        self.refresh_thread.completed.connect(lambda result: self._finish_refresh(tooltip, True, result))
        self.refresh_thread.failed.connect(lambda detail: self._finish_refresh(tooltip, False, detail))
        self.refresh_thread.start()

    def delete_bank(self, subject: str, bank_name: str):
        self.question_index_manager.remove_bank(subject, bank_name)
        self.reload()

    def on_page_changed(self, index: int):
        page = index + 1
        if page == self.current_page:
            return
        self.current_page = page
        self.reload()

    def _finish_refresh(self, tooltip: StateToolTip, success: bool, payload):
        tooltip.setContent("刷新成功" if success else str(payload))
        tooltip.setState(success)
        self._move_tooltip_top_right(tooltip)
        if success:
            self.current_page = 1
            self.reload()

    def _move_tooltip_top_right(self, tooltip: StateToolTip) -> None:
        tooltip.adjustSize()
        margin = 20
        tooltip.move(QPoint(max(self.width() - tooltip.width() - margin, margin), margin))

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
