from __future__ import annotations

import random

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    PrimaryPushButton,
    ProgressRing,
    PushButton,
    StrongBodyLabel,
    SwitchButton,
    isDarkTheme,
)

from answer.answer_window import AnswerWindow
from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from core.base.json_store import JsonStore
from core.choice import ChoiceJudge
from models.base import FavoriteQuestion, ScoreResult, WrongQuestion
from models.choice import QuestionBank, QuestionItem
from ui.widgets.base import StyledCardWidget, show_favorite_tip
from ui.widgets.choice import AnswerCard, OptionCard


class ChoiceAnswerWindow(AnswerWindow):
    def __init__(self, question_bank: QuestionBank, user_manager, wrong_manager, favorite_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.question_bank = question_bank
        self.user_manager = user_manager
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.settings_store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = self.settings_store.load()
        choice_settings = APP_SETTINGS_TEMPLATE["choice_answer"] | self.settings.get("choice_answer", {})
        self.shuffle_options = bool(choice_settings["shuffle_options"])
        self.auto_next = bool(choice_settings["auto_next"])
        self.study_mode = bool(choice_settings["study_mode"])
        try:
            font_size = max(12, min(24, int(choice_settings["question_font_size"])))
            self.question_font_size = 12 + ((font_size - 12 + 1) // 2) * 2
        except (TypeError, ValueError):
            self.question_font_size = APP_SETTINGS_TEMPLATE["choice_answer"]["question_font_size"]
        self.current_index = 0
        self.selected_answers: dict[int, str] = {}
        self.answer_results: dict[int, bool] = {}
        self.option_cards: dict[str, OptionCard] = {}
        self.option_orders: dict[int, list[str]] = {}
        self.displayed_options: dict[str, str] = {}
        self.study_session_id: int | None = None

        self.setWindowTitle(question_bank.name)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1320, 780)
        self.setMinimumSize(1120, 680)
        self.setObjectName("choiceAnswerWindow")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.back_button = PushButton("返回", self)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel(question_bank.name, self)
        self.reset_button = PushButton("重置答题", self)
        self.reset_button.clicked.connect(self.reset_session)
        top.addWidget(self.back_button)
        top.addWidget(self.title_label, 1)
        top.addWidget(self.reset_button)
        root.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(14)

        self.answer_card = AnswerCard(self)
        self.answer_card.setFixedWidth(232)
        self.answer_card.set_questions(len(question_bank.questions))
        self.answer_card.question_selected.connect(self.jump_to_question)
        body.addWidget(self.answer_card, 0, Qt.AlignmentFlag.AlignTop)

        self.divider = QWidget(self)
        self.divider.setFixedWidth(1)
        self.divider.setStyleSheet("background-color: rgba(128, 128, 128, 0.35);")
        body.addWidget(self.divider)

        self.content_card = StyledCardWidget(self, radius=16, light_border_alpha=34)
        right = QVBoxLayout(self.content_card)
        right.setContentsMargins(20, 18, 20, 18)
        right.setSpacing(10)

        self.question_label = StrongBodyLabel("", self)
        question_font = QFont(self.question_label.font())
        question_font.setPixelSize(self.question_font_size)
        question_font.setBold(False)
        self.question_label.setFont(question_font)
        self.question_label.setWordWrap(True)
        right.addWidget(self.question_label, 0, Qt.AlignmentFlag.AlignTop)

        self.option_group = QButtonGroup(self)
        self.option_group.setExclusive(True)
        for key in ["A", "B", "C", "D"]:
            option_card = OptionCard(key, self)
            option_card.button.clicked.connect(lambda checked=False, slot=key: self.submit_display_answer(slot))
            self.option_group.addButton(option_card.button)
            self.option_cards[key] = option_card
            right.addWidget(option_card)

        self.answer_label = StrongBodyLabel("", self)
        self.explanation_label = BodyLabel("", self)
        self.explanation_label.setWordWrap(True)
        self.answer_label.hide()
        self.explanation_label.hide()
        right.addWidget(self.answer_label)
        right.addWidget(self.explanation_label)
        right.addStretch(1)
        body.addWidget(self.content_card, 1)

        self.details_divider = QWidget(self)
        self.details_divider.setFixedWidth(1)
        self.details_divider.setStyleSheet("background-color: rgba(128, 128, 128, 0.35);")
        body.addWidget(self.details_divider)

        sidebar = QWidget(self)
        sidebar.setFixedWidth(276)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(12)

        self.details_card = StyledCardWidget(sidebar, radius=16, light_border_alpha=34)
        details_layout = QVBoxLayout(self.details_card)
        details_layout.setContentsMargins(18, 16, 18, 16)
        details_layout.setSpacing(8)
        details_layout.addWidget(StrongBodyLabel("答题详情", self.details_card))

        accuracy_title = BodyLabel("答题正确率", self.details_card)
        accuracy_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details_layout.addWidget(accuracy_title)

        self.accuracy_ring = ProgressRing(self.details_card)
        self.accuracy_ring.setRange(0, 100)
        self.accuracy_ring.setValue(0)
        self.accuracy_ring.setTextVisible(True)
        self.accuracy_ring.setFixedSize(106, 106)
        details_layout.addWidget(self.accuracy_ring, 0, Qt.AlignmentFlag.AlignCenter)

        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 4, 0, 0)
        stats_layout.setSpacing(4)
        correct_stat, self.correct_value_label = self._create_stat("答对", "0", self.details_card)
        wrong_stat, self.wrong_value_label = self._create_stat("答错", "0", self.details_card)
        score_stat, self.score_value_label = self._create_stat("本次得分", "0 分", self.details_card)
        stats_layout.addWidget(correct_stat, 1)
        stats_layout.addWidget(wrong_stat, 1)
        stats_layout.addWidget(score_stat, 1)
        details_layout.addLayout(stats_layout)
        sidebar_layout.addWidget(self.details_card)

        self.settings_card = StyledCardWidget(sidebar, radius=16, light_border_alpha=34)
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(18, 16, 18, 16)
        settings_layout.setSpacing(0)
        settings_layout.addWidget(StrongBodyLabel("答题设置", self.settings_card))
        settings_layout.addSpacing(8)

        shuffle_row, self.shuffle_switch = self._create_switch_row(
            "打乱选项顺序", self.shuffle_options, self.settings_card
        )
        auto_next_row, self.auto_next_switch = self._create_switch_row(
            "答对后自动切换下一题", self.auto_next, self.settings_card
        )
        study_row, self.study_mode_switch = self._create_switch_row(
            "背题模式", self.study_mode, self.settings_card
        )
        font_size_row, self.question_font_size_combo = self._create_font_size_row(self.settings_card)
        settings_layout.addWidget(shuffle_row)
        settings_layout.addWidget(self._create_horizontal_divider(self.settings_card))
        settings_layout.addWidget(auto_next_row)
        settings_layout.addWidget(self._create_horizontal_divider(self.settings_card))
        settings_layout.addWidget(study_row)
        settings_layout.addWidget(self._create_horizontal_divider(self.settings_card))
        settings_layout.addWidget(font_size_row)

        self.shuffle_switch.checkedChanged.connect(self._on_shuffle_options_changed)
        self.auto_next_switch.checkedChanged.connect(self._on_auto_next_changed)
        self.study_mode_switch.checkedChanged.connect(self._on_study_mode_changed)
        self.question_font_size_combo.currentIndexChanged.connect(self._on_question_font_size_changed)
        sidebar_layout.addWidget(self.settings_card)
        sidebar_layout.addStretch(1)
        body.addWidget(sidebar, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(body, 1)

        nav = QHBoxLayout()
        nav.setSpacing(10)
        self.prev_button = PrimaryPushButton("上一题", self)
        self.next_button = PrimaryPushButton("下一题", self)
        self.favorite_button = PushButton("收藏题目", self)
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        self.favorite_button.clicked.connect(self.favorite_current_question)
        nav.addSpacing(self.answer_card.width() + self.divider.width() + 28)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addWidget(self.favorite_button)
        nav.addStretch(1)
        root.addLayout(nav)

        self._init_shortcuts()
        self._apply_window_style()
        self.render_question()
        self.study_session_id = self.user_manager.start_study_session(
            subject=question_bank.subject,
            source_type="question_bank",
            source_key=f"{question_bank.subject}_{question_bank.name}",
            source_name=question_bank.name,
        )

    def closeEvent(self, event) -> None:
        if self.study_session_id is not None:
            self.user_manager.finish_study_session(self.study_session_id)
            self.study_session_id = None
        super().closeEvent(event)

    def _apply_window_style(self) -> None:
        background = "#202020" if isDarkTheme() else "#f3f3f3"
        self.setStyleSheet(f"QWidget#choiceAnswerWindow{{background-color: {background};}}")
        text_color = "white" if isDarkTheme() else ""
        secondary_color = "rgba(255, 255, 255, 0.88)" if isDarkTheme() else ""
        self.title_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.question_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.answer_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.explanation_label.setStyleSheet(f"color: {secondary_color};" if secondary_color else "")

    @property
    def current_question(self) -> QuestionItem:
        return self.question_bank.questions[self.current_index]

    def _create_stat(self, title: str, value: str, parent: QWidget) -> tuple[QWidget, StrongBodyLabel]:
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        value_label = StrongBodyLabel(value, widget)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = CaptionLabel(title, widget)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return widget, value_label

    def _create_switch_row(self, title: str, checked: bool, parent: QWidget) -> tuple[QWidget, SwitchButton]:
        row = QWidget(parent)
        row.setFixedHeight(48)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(BodyLabel(title, row), 1)
        switch = SwitchButton(row)
        switch.setOnText("")
        switch.setOffText("")
        switch.setChecked(checked)
        layout.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return row, switch

    def _create_font_size_row(self, parent: QWidget) -> tuple[QWidget, ComboBox]:
        row = QWidget(parent)
        row.setFixedHeight(48)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(BodyLabel("题目字号", row), 1)
        combo = ComboBox(row)
        for size in range(12, 25, 2):
            combo.addItem(f"{size} px", userData=size)
        combo.setCurrentIndex(combo.findData(self.question_font_size))
        combo.setFixedWidth(88)
        layout.addWidget(combo, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return row, combo

    def _create_horizontal_divider(self, parent: QWidget) -> QWidget:
        divider = QWidget(parent)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(128, 128, 128, 0.24);")
        return divider

    def render_question(self):
        question = self.current_question
        selected_option = self.selected_answers.get(self.current_index)
        answered = selected_option is not None
        option_order = self._current_option_order()
        self.displayed_options.clear()

        self.question_label.setText(f"{question.id}. {question.question}")

        self.option_group.setExclusive(False)
        for button in self.option_group.buttons():
            button.setChecked(False)
        self.option_group.setExclusive(True)

        for position, (slot, option_card) in enumerate(self.option_cards.items()):
            if position >= len(option_order):
                option_card.hide()
                continue
            actual_key = option_order[position]
            self.displayed_options[slot] = actual_key
            option_card.show()
            option_card.set_option_text(f"{slot}. {question.options.get(actual_key, '')}")
            option_card.set_checked(selected_option == actual_key)
            option_card.set_enabled(not answered and not self.study_mode)
            if self.study_mode and not answered:
                state = "correct" if actual_key == question.answer else "default"
            else:
                state = self._option_state(actual_key, selected_option, question.answer)
            option_card.set_state(state)

        if answered or self.study_mode:
            display_answer = next(
                (slot for slot, actual_key in self.displayed_options.items() if actual_key == question.answer),
                question.answer,
            )
            self.answer_label.setText(f"正确答案：{display_answer}")
            self.explanation_label.setText(f"解析：{question.explanation}")
            self.answer_label.show()
            self.explanation_label.show()
        else:
            self.answer_label.hide()
            self.explanation_label.hide()

        self.answer_card.update_status(self.answer_results, self.current_index)
        self._update_answer_details()
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.question_bank.questions) - 1)
        self._sync_favorite_button()

    def submit_display_answer(self, slot: str) -> None:
        selected = self.displayed_options.get(slot)
        if selected is not None:
            self.submit_answer(selected)

    def submit_answer(self, selected: str):
        if self.study_mode or self.current_index in self.selected_answers:
            return

        question = self.current_question
        answered_index = self.current_index
        self.selected_answers[self.current_index] = selected
        is_correct = ChoiceJudge.judge(selected, question.answer)
        self.answer_results[self.current_index] = is_correct
        self.user_manager.record_answer(
            ScoreResult(
                earned=1 if is_correct else 0,
                possible=1,
            ),
            subject=self._question_subject(question),
            session_id=self.study_session_id,
        )

        self.render_question()

        if is_correct and self.auto_next:
            QTimer.singleShot(1000, lambda index=answered_index: self._auto_next(index))
        else:
            if not is_correct:
                self.wrong_manager.add_wrong(self._build_wrong(question))

    def favorite_current_question(self):
        is_favorite = self.favorite_manager.toggle_favorite(self._build_favorite(self.current_question))
        self._sync_favorite_button()
        show_favorite_tip(self.favorite_button, is_favorite, self)

    def prev_question(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.render_question()

    def next_question(self):
        if self.current_index < len(self.question_bank.questions) - 1:
            self.current_index += 1
            self.render_question()

    def jump_to_question(self, index: int):
        self.current_index = index
        self.render_question()

    def reset_session(self):
        self.current_index = 0
        self.selected_answers.clear()
        self.answer_results.clear()
        self.option_orders.clear()
        self.render_question()

    def _init_shortcuts(self) -> None:
        shortcuts = APP_SETTINGS_TEMPLATE["answer_shortcuts"] | self.settings.get("answer_shortcuts", {})
        self.prev_shortcut = QShortcut(QKeySequence(shortcuts.get("prev_question", "1")), self)
        self.prev_shortcut.activated.connect(self.prev_question)
        self.next_shortcut = QShortcut(QKeySequence(shortcuts.get("next_question", "2")), self)
        self.next_shortcut.activated.connect(self.next_question)

    def _auto_next(self, answered_index: int):
        if not self.auto_next or self.current_index != answered_index:
            return
        if self.answer_results.get(answered_index) and answered_index < len(self.question_bank.questions) - 1:
            self.current_index += 1
            self.render_question()

    def _current_option_order(self) -> list[str]:
        option_keys = [key for key in ("A", "B", "C", "D") if key in self.current_question.options]
        if not self.shuffle_options:
            return option_keys
        if self.current_index not in self.option_orders:
            shuffled = option_keys.copy()
            random.shuffle(shuffled)
            if len(shuffled) > 1 and shuffled == option_keys:
                shuffled = shuffled[1:] + shuffled[:1]
            self.option_orders[self.current_index] = shuffled
        return self.option_orders[self.current_index]

    def _update_answer_details(self) -> None:
        correct_count = sum(1 for result in self.answer_results.values() if result)
        wrong_count = len(self.answer_results) - correct_count
        answered_count = len(self.answer_results)
        accuracy = round(correct_count / answered_count * 100) if answered_count else 0
        self.accuracy_ring.setValue(accuracy)
        self.correct_value_label.setText(str(correct_count))
        self.wrong_value_label.setText(str(wrong_count))
        self.score_value_label.setText(f"{correct_count} 分")

    def _save_choice_setting(self, key: str, value: bool | int) -> None:
        self.settings.setdefault("choice_answer", {})[key] = value
        self.settings_store.save(self.settings)

    def _on_shuffle_options_changed(self, checked: bool) -> None:
        self.shuffle_options = checked
        self._save_choice_setting("shuffle_options", checked)
        self.render_question()

    def _on_auto_next_changed(self, checked: bool) -> None:
        self.auto_next = checked
        self._save_choice_setting("auto_next", checked)

    def _on_study_mode_changed(self, checked: bool) -> None:
        self.study_mode = checked
        self._save_choice_setting("study_mode", checked)
        self.render_question()

    def _on_question_font_size_changed(self, index: int) -> None:
        value = self.question_font_size_combo.itemData(index)
        if value is None:
            return
        self.question_font_size = value
        question_font = QFont(self.question_label.font())
        question_font.setPixelSize(value)
        self.question_label.setFont(question_font)
        self._save_choice_setting("question_font_size", value)

    def _sync_favorite_button(self) -> None:
        self.favorite_button.setText("已收藏" if self._is_current_favorite() else "收藏题目")

    def _is_current_favorite(self) -> bool:
        question = self.current_question
        return self.favorite_manager.get_question(
            self._question_subject(question),
            self._build_question_id(question),
        ) is not None

    def _option_state(self, key: str, selected_option: str | None, answer: str) -> str:
        if selected_option is None:
            return "default"
        if key == answer:
            return "correct"
        if key == selected_option and selected_option != answer:
            return "wrong"
        return "default"

    def _build_question_id(self, question: QuestionItem) -> str:
        if question.source_question_id:
            return question.source_question_id
        return f"{self.question_bank.subject}_{self.question_bank.name}_{question.id}"

    def _question_subject(self, question: QuestionItem) -> str:
        return question.source_subject or self.question_bank.subject

    def _question_bank_name(self, question: QuestionItem) -> str:
        return question.source_bank_name or self.question_bank.name

    def _question_bank_id(self, question: QuestionItem) -> int:
        return (
            question.source_bank_question_id
            if question.source_bank_question_id is not None
            else question.id
        )

    def _build_wrong(self, question: QuestionItem) -> WrongQuestion:
        return WrongQuestion(
            question_id=self._build_question_id(question),
            question_num=self._question_bank_id(question),
            bank_name=self._question_bank_name(question),
            bank_question_id=self._question_bank_id(question),
            subject=self._question_subject(question),
            question=question.question,
            options=question.options,
            answer=question.answer,
            explanation=question.explanation,
        )

    def _build_favorite(self, question: QuestionItem) -> FavoriteQuestion:
        return FavoriteQuestion(
            question_id=self._build_question_id(question),
            bank_name=self._question_bank_name(question),
            bank_question_id=self._question_bank_id(question),
            subject=self._question_subject(question),
            question=question.question,
            options=question.options,
            answer=question.answer,
            explanation=question.explanation,
        )
