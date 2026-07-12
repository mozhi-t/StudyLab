from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ComboBox, LineEdit, PipsPager, PipsScrollButtonDisplayMode, PrimaryPushButton, SingleDirectionScrollArea, SubtitleLabel

from config.settings import SUBJECTS
from ui.styles.title_style import apply_page_title_style
from ui.widgets.question_card import QuestionCard
from ui.widgets.question_detail_dialog import QuestionDetailDialog
from ui.widgets.python.record_detail_dialog import PythonWrongDetailDialog
from models.favorite_question import FavoriteQuestion
from ui.widgets.styled_card import StyledCardWidget


class WrongBookPage(QWidget):
    practice_python_requested = pyqtSignal(str, int)
    favorite_changed = pyqtSignal()

    def __init__(self, wrong_manager, favorite_manager=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.current_page = 1
        self.total_count = 0
        self.cards: list[QuestionCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        self.page_title = SubtitleLabel("错题本", self)
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
        self.search_edit.setPlaceholderText("搜索错题")
        self.search_edit.textChanged.connect(self._reset_then_reload)
        self.refresh_button = PrimaryPushButton("刷新", self)
        self.refresh_button.clicked.connect(self.reload)
        top.addWidget(self.subject_combo)
        top.addWidget(self.search_edit, 1)
        top.addWidget(self.refresh_button)
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
        self.content.setObjectName("wrongListContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch(1)
        self.scroll.setWidget(self.content)
        self.scroll.enableTransparentBackground()
        self.content.setStyleSheet("QWidget#wrongListContent{background: transparent; border: none;}")
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
        items, total = self.wrong_manager.list_wrongs(subject=subject or None, keyword=self.search_edit.text(), page=self.current_page)
        self.total_count = total
        self._clear_cards()
        for item in items:
            card = QuestionCard(
                title=item.question,
                right_meta=f"错误次数：{item.error_count}",
                checkable=True,
                parent=self.content,
            )
            card.mouseDoubleClickEvent = lambda event, payload=item: self.show_detail(payload)
            self.content_layout.insertWidget(self.content_layout.count() - 1, card)
            self.cards.append(card)
        max_page = max((self.total_count - 1) // 50 + 1, 1)
        self._sync_pager(max_page)

    def show_detail(self, item):
        if item.question_type == "python_programming":
            dialog = PythonWrongDetailDialog(item, self)
            dialog.set_favorite(self._is_python_favorite(item))
            dialog.practice_requested.connect(
                lambda: self.practice_python_requested.emit(item.bank_name, item.bank_question_id)
            )
            dialog.favorite_requested.connect(lambda: self._favorite_python_item(item, dialog))
            dialog.exec()
            return
        QuestionDetailDialog(item.bank_name, item.question, item.options, item.answer, item.explanation, self).exec()

    def _is_python_favorite(self, item) -> bool:
        return bool(
            self.favorite_manager
            and self.favorite_manager.get_question(item.subject, item.question_id) is not None
        )

    def _favorite_python_item(self, item, dialog: PythonWrongDetailDialog) -> None:
        if self.favorite_manager is None or self._is_python_favorite(item):
            dialog.set_favorite(True)
            return
        self.favorite_manager.toggle_favorite(
            FavoriteQuestion(
                question_id=item.question_id,
                bank_name=item.bank_name,
                bank_question_id=item.bank_question_id,
                subject=item.subject,
                question=item.question,
                options={},
                answer=item.answer,
                explanation="",
                question_type="python_programming",
                payload={
                    "code": item.payload.get("code", ""),
                    "full_score": item.payload.get("full_score", 20),
                    "grading_points": item.payload.get("grading_points", []),
                },
            )
        )
        dialog.set_favorite(True)
        self.favorite_changed.emit()

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
