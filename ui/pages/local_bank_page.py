from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import LineEdit, PrimaryPushButton, PushButton, StateToolTip

from config.settings import SUBJECTS
from ui.widgets.index_refresh_dialog import IndexRefreshDialog
from ui.widgets.question_card import QuestionCard, bank_card_title


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
        self.cards: list[QuestionCard] = []
        self.refresh_thread: IndexRefreshThread | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        toolbar = QVBoxLayout()
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索题库")
        self.search_edit.textChanged.connect(self._reset_then_reload)
        toolbar.addWidget(self.search_edit)

        filter_row = QHBoxLayout()
        self.subject_combo = QComboBox(self)
        self.subject_combo.addItem("全部科目", "")
        for key, label in SUBJECTS.items():
            self.subject_combo.addItem(label, key)
        self.subject_combo.currentIndexChanged.connect(self._reset_then_reload)
        filter_row.addWidget(self.subject_combo)

        self.refresh_button = PrimaryPushButton("刷新索引", self)
        self.refresh_button.clicked.connect(self.refresh_index)
        filter_row.addWidget(self.refresh_button)
        toolbar.addLayout(filter_row)
        root.addLayout(toolbar)

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
        self.prev_button = PushButton("上一页", self)
        self.next_button = PushButton("下一页", self)
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        pager.addWidget(self.prev_button)
        pager.addWidget(self.next_button)
        root.addLayout(pager)

        self.reload()

    def _reset_then_reload(self):
        self.current_page = 1
        self.reload()

    def reload(self):
        subject = self.subject_combo.currentData()
        keyword = self.search_edit.text()
        items, total = self.question_index_manager.list_banks(subject=subject or None, keyword=keyword, page=self.current_page)
        self.total_count = total
        self._clear_cards()
        for item in items:
            card = QuestionCard(
                title=bank_card_title(item.subject, item.name),
                subtitle="双击进入答题",
                meta=f"创建时间：{item.create_time}",
                action_text="删除",
                parent=self.content,
            )
            if card.action_button:
                card.action_button.clicked.connect(lambda checked=False, s=item.subject, n=item.name: self.delete_bank(s, n))
            card.mouseDoubleClickEvent = lambda event, s=item.subject, n=item.name: self.open_bank_requested.emit(s, n)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)
        self._update_page_info()

    def refresh_index(self):
        dialog = IndexRefreshDialog(self)
        if not dialog.exec():
            return
        tooltip = StateToolTip("正在检查题库...", "请稍后", self)
        tooltip.show()
        self.refresh_thread = IndexRefreshThread(self.question_index_manager)
        self.refresh_thread.completed.connect(lambda result: self._finish_refresh(tooltip, True, result))
        self.refresh_thread.failed.connect(lambda detail: self._finish_refresh(tooltip, False, detail))
        self.refresh_thread.start()

    def delete_bank(self, subject: str, bank_name: str):
        self.question_index_manager.remove_bank(subject, bank_name)
        self.reload()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.reload()

    def next_page(self):
        max_page = max((self.total_count - 1) // 50 + 1, 1)
        if self.current_page < max_page:
            self.current_page += 1
            self.reload()

    def _finish_refresh(self, tooltip: StateToolTip, success: bool, payload):
        tooltip.setContent("刷新成功" if success else str(payload))
        tooltip.setState(success)
        if success:
            self.current_page = 1
            self.reload()

    def _clear_cards(self):
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()

    def _update_page_info(self):
        max_page = max((self.total_count - 1) // 50 + 1, 1)
        self.page_info.setText(f"共 {self.total_count} 个题库，第 {self.current_page}/{max_page} 页")
