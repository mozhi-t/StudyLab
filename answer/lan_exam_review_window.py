from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, Pivot, PrimaryPushButton, PushButton, StrongBodyLabel

from answer.answer_window import AnswerWindow
from answer.choice_answer import OptionCard
from config.settings import SUBJECTS
from models.favorite_question import FavoriteQuestion
from ui.widgets.answer_card import AnswerCard


class LanExamReviewWindow(AnswerWindow):
    def __init__(self, exam_name: str, result_payload: dict, wrong_manager, favorite_manager, parent=None):
        super().__init__(parent)
        self.exam_name = exam_name
        self.result_payload = result_payload
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.subject_order = [
            name for name, subject in result_payload.get("details", {}).items() if subject.get("choice_questions")
        ]
        self.current_subject = self.subject_order[0] if self.subject_order else ""
        self.current_index = 0
        self.option_cards: dict[str, OptionCard] = {}

        self.setWindowTitle(f"{exam_name} - 题目详情")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1040, 660)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.back_button = PushButton("返回", self)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel(exam_name, self)
        self.detail_title_button = PushButton("题目详情", self)
        self.detail_title_button.setEnabled(False)
        top.addWidget(self.back_button)
        top.addWidget(self.title_label, 1)
        top.addWidget(self.detail_title_button)
        root.addLayout(top)

        self.pivot = Pivot(self)
        self.pivot.currentItemChanged.connect(self._switch_subject)
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        for subject_key in self.subject_order:
            self.pivot.addItem(routeKey=subject_key, text=SUBJECTS.get(subject_key, subject_key), onClick=lambda: None)
        root.addLayout(nav_layout)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.answer_card = AnswerCard(self)
        self.answer_card.setFixedWidth(232)
        self.answer_card.question_selected.connect(self.jump_to_question)
        total_questions = sum(len(subject.get("choice_questions", [])) for subject in result_payload.get("details", {}).values())
        self.answer_card.set_questions(total_questions)
        body.addWidget(self.answer_card, 0, Qt.AlignmentFlag.AlignTop)

        self.divider = QWidget(self)
        self.divider.setFixedWidth(1)
        self.divider.setStyleSheet("background-color: rgba(128, 128, 128, 0.35); border: none;")
        body.addWidget(self.divider)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.question_label = StrongBodyLabel("", self)
        question_font = QFont(self.question_label.font())
        question_font.setPointSize(12)
        question_font.setBold(False)
        self.question_label.setFont(question_font)
        self.question_label.setWordWrap(True)
        right.addWidget(self.question_label, 0, Qt.AlignmentFlag.AlignTop)

        self.option_group = QButtonGroup(self)
        self.option_group.setExclusive(False)
        for key in ["A", "B", "C", "D"]:
            option_card = OptionCard(key, self)
            option_card.set_enabled(False)
            self.option_group.addButton(option_card.button)
            self.option_cards[key] = option_card
            right.addWidget(option_card)

        self.answer_label = StrongBodyLabel("", self)
        self.explanation_label = BodyLabel("", self)
        self.explanation_label.setWordWrap(True)
        right.addWidget(self.answer_label)
        right.addWidget(self.explanation_label)
        right.addStretch(1)
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        nav = QHBoxLayout()
        nav.setSpacing(10)
        self.prev_button = PrimaryPushButton("上一题", self)
        self.next_button = PrimaryPushButton("下一题", self)
        self.favorite_button = PushButton("收藏题目", self)
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        nav.addSpacing(self.answer_card.width() + self.divider.width() + 28)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addWidget(self.favorite_button)
        nav.addStretch(1)
        root.addLayout(nav)

        if self.current_subject:
            self.pivot.setCurrentItem(self.current_subject)
        self.render_question()

    def _current_questions(self) -> list[dict]:
        return self.result_payload.get("details", {}).get(self.current_subject, {}).get("choice_questions", [])

    def _current_question(self) -> dict:
        return self._current_questions()[self.current_index]

    def _switch_subject(self, subject_key: str) -> None:
        if subject_key == self.current_subject:
            self.render_question()
            return
        self.current_subject = subject_key
        self.current_index = 0
        self.render_question()

    def render_question(self) -> None:
        if not self.current_subject:
            return
        item = self._current_question()
        self.question_label.setText(f"{item['id']}. {item['question']}")
        for key, option_card in self.option_cards.items():
            option_card.set_option_text(f"{key}. {item['options'].get(key, '')}")
            option_card.set_checked(item.get("selected") == key)
            if key == item["correct_answer"]:
                option_card.set_state("correct")
            elif key == item.get("selected") and not item.get("is_correct"):
                option_card.set_state("wrong")
            else:
                option_card.set_state("default")
        self.answer_label.setText(f"正确答案：{item['correct_answer']}    你的答案：{item.get('selected') or '未作答'}")
        self.explanation_label.setText(f"解析：{item['explanation']}")
        self.prev_button.setEnabled(self.current_index > 0 or self.subject_order.index(self.current_subject) > 0)
        self.next_button.setEnabled(
            self.current_index < len(self._current_questions()) - 1
            or self.subject_order.index(self.current_subject) < len(self.subject_order) - 1
        )
        self._sync_favorite_text()
        self._update_answer_card()

    def prev_question(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.render_question()
            return
        subject_idx = self.subject_order.index(self.current_subject)
        if subject_idx > 0:
            prev_subject = self.subject_order[subject_idx - 1]
            self._set_location(prev_subject, len(self.result_payload["details"][prev_subject]["choice_questions"]) - 1)

    def next_question(self) -> None:
        if self.current_index < len(self._current_questions()) - 1:
            self.current_index += 1
            self.render_question()
            return
        subject_idx = self.subject_order.index(self.current_subject)
        if subject_idx < len(self.subject_order) - 1:
            self._set_location(self.subject_order[subject_idx + 1], 0)

    def jump_to_question(self, index: int) -> None:
        flat = self._flat_question_refs()
        if index < 0 or index >= len(flat):
            return
        subject, question_index = flat[index]
        self._set_location(subject, question_index)

    def _set_location(self, subject: str, index: int) -> None:
        self.current_subject = subject
        self.current_index = index
        self.pivot.blockSignals(True)
        self.pivot.setCurrentItem(subject)
        self.pivot.blockSignals(False)
        self.render_question()

    def _flat_question_refs(self) -> list[tuple[str, int]]:
        refs: list[tuple[str, int]] = []
        for subject_key in self.subject_order:
            for index, _item in enumerate(self.result_payload["details"][subject_key]["choice_questions"]):
                refs.append((subject_key, index))
        return refs

    def _update_answer_card(self) -> None:
        flat = self._flat_question_refs()
        current_flat_index = next((idx for idx, ref in enumerate(flat) if ref == (self.current_subject, self.current_index)), 0)
        results = {idx: flat_item[0] in self.result_payload["details"] and True for idx, flat_item in enumerate(flat)}
        self.answer_card.update_status(results, current_flat_index)

    def _build_question_id(self, item: dict) -> str:
        return f"lan_exam_{self.current_subject}_{self.exam_name}_{item['id']}"

    def _sync_favorite_text(self) -> None:
        item = self._current_question()
        exists = self.favorite_manager.get_question(self.current_subject, self._build_question_id(item)) is not None
        self.favorite_button.setText("已收藏" if exists else "收藏题目")

    def toggle_favorite(self) -> None:
        item = self._current_question()
        payload = FavoriteQuestion(
            question_id=self._build_question_id(item),
            bank_name=self.exam_name,
            bank_question_id=item["id"],
            subject=self.current_subject,
            question=item["question"],
            options=item["options"],
            answer=item["correct_answer"],
            explanation=item["explanation"],
        )
        self.favorite_manager.toggle_favorite(payload)
        self._sync_favorite_text()
