from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    PrimaryPushButton,
    PushButton,
    RadioButton,
    StrongBodyLabel,
    TeachingTip,
    TeachingTipTailPosition,
)

from answer.answer_window import AnswerWindow
from models.favorite_question import FavoriteQuestion
from models.question_bank import QuestionBank, QuestionItem
from models.wrong_question import WrongQuestion
from ui.widgets.answer_card import AnswerCard
from ui.widgets.styled_card import StyledCardWidget


class OptionCard(StyledCardWidget):
    def __init__(self, option_key: str, parent: QWidget | None = None):
        super().__init__(parent, radius=12, light_border_alpha=34)
        self.option_key = option_key
        self._state = "default"

        self.button = RadioButton(self)
        self.button.setObjectName(f"choiceOption{option_key}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.button)

    def set_option_text(self, text: str) -> None:
        self.button.setText(text)

    def set_checked(self, checked: bool) -> None:
        self.button.setChecked(checked)

    def set_enabled(self, enabled: bool) -> None:
        self.button.setEnabled(enabled)

    def set_state(self, state: str) -> None:
        self._state = state
        self._apply_state_style()
        self.update()

    def _normalBackgroundColor(self):
        if self._state == "correct":
            return QColor(15, 163, 97, 42)
        if self._state == "wrong":
            return QColor(224, 72, 72, 38)
        return super()._normalBackgroundColor()

    def _apply_state_style(self) -> None:
        if self._state == "correct":
            self.button.setStyleSheet("color: rgb(19, 126, 67); font-weight: 600;")
        elif self._state == "wrong":
            self.button.setStyleSheet("color: rgb(198, 52, 52); font-weight: 600;")
        else:
            self.button.setStyleSheet("")


class ChoiceAnswerWindow(AnswerWindow):
    def __init__(self, question_bank: QuestionBank, user_manager, wrong_manager, favorite_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.question_bank = question_bank
        self.user_manager = user_manager
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.current_index = 0
        self.selected_answers: dict[int, str] = {}
        self.answer_results: dict[int, bool] = {}
        self.option_cards: dict[str, OptionCard] = {}

        self.setWindowTitle(question_bank.name)
        self.resize(1280, 800)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(18)

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
        body.setSpacing(18)

        self.answer_card = AnswerCard(self)
        self.answer_card.set_questions(len(question_bank.questions))
        self.answer_card.question_selected.connect(self.jump_to_question)
        body.addWidget(self.answer_card, 0, Qt.AlignmentFlag.AlignTop)

        right = QVBoxLayout()
        right.setSpacing(14)

        self.question_label = StrongBodyLabel("", self)
        question_font = QFont(self.question_label.font())
        question_font.setPointSize(question_font.pointSize() + 1)
        self.question_label.setFont(question_font)
        self.question_label.setWordWrap(True)
        right.addWidget(self.question_label, 0, Qt.AlignmentFlag.AlignTop)

        self.option_group = QButtonGroup(self)
        self.option_group.setExclusive(True)
        for key in ["A", "B", "C", "D"]:
            option_card = OptionCard(key, self)
            option_card.button.clicked.connect(lambda checked=False, option=key: self.submit_answer(option))
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

        nav = QHBoxLayout()
        nav.setSpacing(10)
        self.prev_button = PrimaryPushButton("上一题", self)
        self.next_button = PrimaryPushButton("下一题", self)
        self.favorite_button = PushButton("收藏题目", self)
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        self.favorite_button.clicked.connect(self.favorite_current_question)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addStretch(1)
        nav.addWidget(self.favorite_button)
        right.addLayout(nav)
        right.addStretch(1)

        body.addLayout(right, 1)
        root.addLayout(body, 1)
        self.render_question()

    @property
    def current_question(self) -> QuestionItem:
        return self.question_bank.questions[self.current_index]

    def render_question(self):
        question = self.current_question
        selected_option = self.selected_answers.get(self.current_index)
        answered = selected_option is not None

        self.question_label.setText(f"{question.id}. {question.question}")

        self.option_group.setExclusive(False)
        for button in self.option_group.buttons():
            button.setChecked(False)
        self.option_group.setExclusive(True)

        for key, option_card in self.option_cards.items():
            option_card.set_option_text(f"{key}. {question.options.get(key, '')}")
            option_card.set_checked(selected_option == key)
            option_card.set_enabled(not answered)
            option_card.set_state(self._option_state(key, selected_option, question.answer))

        if answered:
            self.answer_label.setText(f"正确答案：{question.answer}")
            self.explanation_label.setText(f"解析：{question.explanation}")
            self.answer_label.show()
            self.explanation_label.show()
        else:
            self.answer_label.hide()
            self.explanation_label.hide()

        self.answer_card.update_status(self.answer_results, self.current_index)
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.question_bank.questions) - 1)
        self._sync_favorite_button()

    def submit_answer(self, selected: str):
        if self.current_index in self.selected_answers:
            return

        question = self.current_question
        self.selected_answers[self.current_index] = selected
        is_correct = selected == question.answer
        self.answer_results[self.current_index] = is_correct
        self.user_manager.record_study_session(1)

        self.render_question()

        if is_correct:
            QTimer.singleShot(1000, self._auto_next)
        else:
            self.wrong_manager.add_wrong(self._build_wrong(question))

    def favorite_current_question(self):
        if self._is_current_favorite():
            return

        is_favorite = self.favorite_manager.toggle_favorite(self._build_favorite(self.current_question))
        if is_favorite:
            self.favorite_button.setText("已收藏")
            TeachingTip.create(
                self.favorite_button,
                "收藏成功",
                "题目已加入收藏夹",
                icon=FluentIcon.HEART,
                duration=1500,
                tailPosition=TeachingTipTailPosition.BOTTOM,
                parent=self,
            )

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
        self.render_question()

    def _auto_next(self):
        if self.current_index in self.answer_results and self.answer_results[self.current_index]:
            if self.current_index < len(self.question_bank.questions) - 1:
                self.current_index += 1
                self.render_question()

    def _sync_favorite_button(self) -> None:
        self.favorite_button.setText("已收藏" if self._is_current_favorite() else "收藏题目")

    def _is_current_favorite(self) -> bool:
        return self.favorite_manager.get_question(self.question_bank.subject, self._build_question_id(self.current_question)) is not None

    def _option_state(self, key: str, selected_option: str | None, answer: str) -> str:
        if selected_option is None:
            return "default"
        if key == answer:
            return "correct"
        if key == selected_option and selected_option != answer:
            return "wrong"
        return "default"

    def _build_question_id(self, question: QuestionItem) -> str:
        return f"{self.question_bank.subject}_{self.question_bank.name}_{question.id}"

    def _build_wrong(self, question: QuestionItem) -> WrongQuestion:
        return WrongQuestion(
            question_id=self._build_question_id(question),
            question_num=question.id,
            bank_name=self.question_bank.name,
            bank_question_id=question.id,
            subject=self.question_bank.subject,
            question=question.question,
            options=question.options,
            answer=question.answer,
            explanation=question.explanation,
        )

    def _build_favorite(self, question: QuestionItem) -> FavoriteQuestion:
        return FavoriteQuestion(
            question_id=self._build_question_id(question),
            bank_name=self.question_bank.name,
            bank_question_id=question.id,
            subject=self.question_bank.subject,
            question=question.question,
            options=question.options,
            answer=question.answer,
            explanation=question.explanation,
        )
