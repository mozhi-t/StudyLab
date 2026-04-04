from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CardWidget, PrimaryPushButton, PushButton, RadioButton, StrongBodyLabel

from answer.answer_window import AnswerWindow
from models.favorite_question import FavoriteQuestion
from models.question_bank import QuestionBank, QuestionItem
from models.wrong_question import WrongQuestion
from ui.widgets.answer_card import AnswerCard


class ChoiceAnswerWindow(AnswerWindow):
    def __init__(self, question_bank: QuestionBank, user_manager, wrong_manager, favorite_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.question_bank = question_bank
        self.user_manager = user_manager
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.current_index = 0
        self.answered_indices: set[int] = set()
        self.answer_buttons: dict[str, RadioButton] = {}

        self.setWindowTitle(question_bank.name)
        self.resize(1280, 800)

        root = QVBoxLayout(self)
        top = QHBoxLayout()
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
        self.answer_card = AnswerCard(self)
        self.answer_card.set_questions(len(question_bank.questions))
        self.answer_card.question_selected.connect(self.jump_to_question)
        body.addWidget(self.answer_card, 1)

        center = QVBoxLayout()
        self.question_label = BodyLabel("", self)
        self.question_label.setWordWrap(True)
        center.addWidget(self.question_label)

        self.option_group = QButtonGroup(self)
        for key in ["A", "B", "C", "D"]:
            button = RadioButton(self)
            button.clicked.connect(lambda checked=False, option=key: self.submit_answer(option))
            self.option_group.addButton(button)
            self.answer_buttons[key] = button
            center.addWidget(button)

        self.feedback_card = CardWidget(self)
        feedback_layout = QVBoxLayout(self.feedback_card)
        self.answer_label = StrongBodyLabel("答案：", self.feedback_card)
        self.explanation_label = BodyLabel("解析：", self.feedback_card)
        self.explanation_label.setWordWrap(True)
        feedback_layout.addWidget(self.answer_label)
        feedback_layout.addWidget(self.explanation_label)
        center.addWidget(self.feedback_card)

        nav = QHBoxLayout()
        self.prev_button = PrimaryPushButton("上一题", self)
        self.next_button = PrimaryPushButton("下一题", self)
        self.favorite_button = PushButton("收藏题目", self)
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addWidget(self.favorite_button)
        center.addLayout(nav)
        body.addLayout(center, 3)

        root.addLayout(body, 1)
        self.render_question()

    @property
    def current_question(self) -> QuestionItem:
        return self.question_bank.questions[self.current_index]

    def render_question(self):
        question = self.current_question
        self.question_label.setText(f"{question.id}. {question.question}")
        for key, button in self.answer_buttons.items():
            button.blockSignals(True)
            button.setChecked(False)
            button.setText(f"{key}. {question.options.get(key, '')}")
            button.blockSignals(False)
        self.answer_label.setText("答案：")
        self.explanation_label.setText("解析：")
        self.answer_card.update_status(self.answered_indices, self.current_index)

    def submit_answer(self, selected: str):
        question = self.current_question
        self.answered_indices.add(self.current_index)
        self.user_manager.record_study_session(1)
        self.answer_label.setText(f"答案：{question.answer}")
        self.explanation_label.setText(f"解析：{question.explanation}")
        self.answer_card.update_status(self.answered_indices, self.current_index)
        if selected == question.answer:
            QTimer.singleShot(1000, self._auto_next)
        else:
            self.wrong_manager.add_wrong(self._build_wrong(question))

    def toggle_favorite(self):
        self.favorite_manager.toggle_favorite(self._build_favorite(self.current_question))

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
        self.answered_indices.clear()
        self.render_question()

    def _auto_next(self):
        if self.current_index < len(self.question_bank.questions) - 1:
            self.current_index += 1
            self.render_question()

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
