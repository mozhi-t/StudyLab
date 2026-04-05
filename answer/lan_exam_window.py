from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import Pivot, PrimaryPushButton, PushButton, StrongBodyLabel

from answer.answer_window import AnswerWindow
from answer.choice_answer import OptionCard
from answer.lan_exam_review_window import LanExamReviewWindow
from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE, SUBJECTS
from core.json_store import JsonStore
from ui.widgets.answer_card import AnswerCard
from core.lan_exam_store import LanExamStore
from models.wrong_question import WrongQuestion


class LanExamWindow(AnswerWindow):
    submit_requested = pyqtSignal(dict)

    def __init__(self, paper: dict, wrong_manager, favorite_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.paper = paper
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.store = LanExamStore()
        self.settings = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE).load()
        self.current_subject = next(
            (name for name, subject in paper.get("subjects", {}).items() if subject.get("enabled") and subject.get("choice_questions")),
            "",
        )
        self.current_index = 0
        self.answers = self.store.load_inputs(self.paper["exam_name"])
        self.option_cards: dict[str, OptionCard] = {}
        self.review_window: LanExamReviewWindow | None = None
        self.started_at = datetime.now()
        self.result_payload: dict | None = None
        self.wrongs_recorded = False
        self.subject_order = [
            name
            for name, subject in paper.get("subjects", {}).items()
            if subject.get("enabled") and subject.get("choice_questions")
        ]

        self.setWindowTitle(self.paper["exam_name"])
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1040, 660)

        self.stack = QStackedWidget(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack)

        self.exam_page = QWidget(self)
        self.submit_page = QWidget(self)
        self.stack.addWidget(self.exam_page)
        self.stack.addWidget(self.submit_page)

        self._init_exam_page()
        self._init_submit_page()
        self._init_shortcuts()
        self.render_question()
        self._init_timer()

    def _init_exam_page(self) -> None:
        root = QVBoxLayout(self.exam_page)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.back_button = PushButton("返回", self.exam_page)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel(self.paper["exam_name"], self.exam_page)
        self.remaining_label = StrongBodyLabel("", self.exam_page)
        self.submit_button = PrimaryPushButton("交卷", self.exam_page)
        self.submit_button.clicked.connect(self.submit_exam)
        top.addWidget(self.back_button)
        top.addWidget(self.title_label, 1)
        top.addWidget(self.remaining_label)
        top.addWidget(self.submit_button)
        root.addLayout(top)

        self.pivot = Pivot(self.exam_page)
        self.pivot.currentItemChanged.connect(self._switch_subject)
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        for subject_key in self.subject_order:
            self.pivot.addItem(routeKey=subject_key, text=SUBJECTS.get(subject_key, subject_key), onClick=lambda: None)
        root.addLayout(nav_layout)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.answer_card = AnswerCard(self.exam_page)
        self.answer_card.setFixedWidth(232)
        self.answer_card.question_selected.connect(self.jump_to_question)
        total_questions = sum(
            len(subject.get("choice_questions", []))
            for subject in self.paper.get("subjects", {}).values()
            if subject.get("enabled")
        )
        self.answer_card.set_questions(total_questions)
        body.addWidget(self.answer_card, 0, Qt.AlignmentFlag.AlignTop)

        self.divider = QWidget(self.exam_page)
        self.divider.setFixedWidth(1)
        self.divider.setStyleSheet("background-color: rgba(128, 128, 128, 0.35);")
        body.addWidget(self.divider)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.question_label = StrongBodyLabel("", self.exam_page)
        font = QFont(self.question_label.font())
        font.setPointSize(12)
        font.setBold(False)
        self.question_label.setFont(font)
        self.question_label.setWordWrap(True)
        right.addWidget(self.question_label, 0, Qt.AlignmentFlag.AlignTop)

        self.option_group = QButtonGroup(self.exam_page)
        self.option_group.setExclusive(True)
        for key in ["A", "B", "C", "D"]:
            option_card = OptionCard(key, self.exam_page)
            option_card.button.clicked.connect(lambda checked=False, option=key: self.select_option(option))
            self.option_group.addButton(option_card.button)
            self.option_cards[key] = option_card
            right.addWidget(option_card)
        right.addStretch(1)
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        nav = QHBoxLayout()
        self.prev_button = PushButton("上一题", self.exam_page)
        self.next_button = PushButton("下一题", self.exam_page)
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        nav.addSpacing(self.answer_card.width() + self.divider.width() + 28)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addStretch(1)
        root.addLayout(nav)
        if self.current_subject:
            self.pivot.setCurrentItem(self.current_subject)

    def _init_submit_page(self) -> None:
        root = QVBoxLayout(self.submit_page)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        root.addStretch(1)
        self.submit_status_label = StrongBodyLabel("正在交卷", self.submit_page)
        self.submit_status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(self.submit_status_label)
        self.score_label = StrongBodyLabel("", self.submit_page)
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.score_label.hide()
        root.addWidget(self.score_label)
        self.detail_button = PrimaryPushButton("题目详情", self.submit_page)
        self.detail_button.clicked.connect(self.show_review)
        self.detail_button.hide()
        root.addWidget(self.detail_button, 0, Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)
        self.submit_page.setStyleSheet("background-color: white;")

    def _init_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_remaining)
        self.timer.start(1000)
        self._update_remaining()

    def _subject_questions(self) -> list[dict]:
        return self.paper["subjects"][self.current_subject]["choice_questions"]

    def _current_question(self) -> dict:
        return self._subject_questions()[self.current_index]

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
        question = self._current_question()
        self.question_label.setText(f"{question['id']}. {question['question']}")
        selected = self._selected_for(question["id"])
        self.option_group.setExclusive(False)
        for button in self.option_group.buttons():
            button.setChecked(False)
        self.option_group.setExclusive(True)
        for key, option_card in self.option_cards.items():
            option_card.set_option_text(f"{key}. {question['options'].get(key, '')}")
            option_card.set_checked(selected == key)
            option_card.set_enabled(True)
            option_card.set_state("default")
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self._subject_questions()) - 1)
        self._update_answer_card()

    def _selected_for(self, question_id: int) -> str:
        questions = self.answers.get("subjects", {}).get(self.current_subject, {}).get("choice_questions", [])
        for item in questions:
            if int(item["id"]) == int(question_id):
                return item.get("selected", "")
        return ""

    def select_option(self, option: str) -> None:
        subjects = self.answers.setdefault("subjects", {})
        subject = subjects.setdefault(self.current_subject, {"choice_questions": []})
        questions = subject["choice_questions"]
        question_id = self._current_question()["id"]
        for item in questions:
            if int(item["id"]) == int(question_id):
                item["selected"] = option
                break
        else:
            questions.append({"id": question_id, "selected": option})
        self.store.save_inputs(self.paper["exam_name"], self.answers)
        self.render_question()

    def prev_question(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.render_question()
            return
        current_subject_idx = self.subject_order.index(self.current_subject)
        if current_subject_idx > 0:
            next_subject = self.subject_order[current_subject_idx - 1]
            next_index = len(self.paper["subjects"][next_subject]["choice_questions"]) - 1
            self._set_location(next_subject, next_index)

    def next_question(self) -> None:
        if self.current_index < len(self._subject_questions()) - 1:
            self.current_index += 1
            self.render_question()
            return
        current_subject_idx = self.subject_order.index(self.current_subject)
        if current_subject_idx < len(self.subject_order) - 1:
            self._set_location(self.subject_order[current_subject_idx + 1], 0)

    def jump_to_question(self, index: int) -> None:
        flat = self._flat_question_refs()
        if index < 0 or index >= len(flat):
            return
        subject, question_index = flat[index]
        self._set_location(subject, question_index)

    def _remaining_seconds(self) -> int:
        duration_limit = self.paper.get("duration_minutes", 60) * 60
        elapsed = int((datetime.now() - self.started_at).total_seconds())
        end_seconds = int((datetime.fromisoformat(self.paper["end_time"]) - datetime.now()).total_seconds())
        return max(min(duration_limit - elapsed, end_seconds), 0)

    def _update_remaining(self) -> None:
        remaining = self._remaining_seconds()
        minutes, seconds = divmod(remaining, 60)
        self.remaining_label.setText(f"剩余时间：{minutes:02d}:{seconds:02d}")
        if remaining <= 0:
            self.timer.stop()
            self.submit_exam()

    def submit_exam(self) -> None:
        if self.stack.currentWidget() is self.submit_page:
            return
        self.timer.stop()
        self.stack.setCurrentWidget(self.submit_page)
        self.submit_requested.emit(
            {
                "exam_id": self.paper["exam_id"],
                "exam_name": self.paper["exam_name"],
                "subjects": self.answers.get("subjects", {}),
            }
        )

    def handle_submit_result(self, payload: dict) -> None:
        self.result_payload = payload
        if payload.get("show_score_immediately"):
            self.submit_status_label.setText("交卷成功")
            self.score_label.setText(f"分数：{payload.get('score', 0)}")
            self.score_label.show()
        else:
            self.submit_status_label.setText("交卷成功，等待公布")
        if payload.get("show_correct_answer"):
            self.detail_button.show()
            self._record_wrongs_once(payload)
        self.store.save_result(self.paper["exam_name"], payload)

    def show_review(self) -> None:
        if not self.result_payload or not self.result_payload.get("show_correct_answer"):
            return
        self.review_window = LanExamReviewWindow(
            exam_name=self.paper["exam_name"],
            result_payload=self.result_payload,
            wrong_manager=self.wrong_manager,
            favorite_manager=self.favorite_manager,
        )
        self.review_window.show()
        self.review_window.raise_()
        self.review_window.activateWindow()

    def _record_wrongs_once(self, payload: dict) -> None:
        if self.wrongs_recorded:
            return
        for subject, value in payload.get("details", {}).items():
            for item in value.get("choice_questions", []):
                if item.get("is_correct"):
                    continue
                self.wrong_manager.add_wrong(
                    WrongQuestion(
                        question_id=f"lan_exam_{subject}_{self.paper['exam_name']}_{item['id']}",
                        question_num=item["id"],
                        bank_name=self.paper["exam_name"],
                        bank_question_id=item["id"],
                        subject=subject,
                        question=item["question"],
                        options=item["options"],
                        answer=item["correct_answer"],
                        explanation=item["explanation"],
                    )
                )
        self.wrongs_recorded = True

    def _flat_question_refs(self) -> list[tuple[str, int]]:
        refs: list[tuple[str, int]] = []
        for subject_key, subject in self.paper.get("subjects", {}).items():
            if not subject.get("enabled"):
                continue
            for index, _item in enumerate(subject.get("choice_questions", [])):
                refs.append((subject_key, index))
        return refs

    def _answered_count(self) -> int:
        count = 0
        for subject in self.answers.get("subjects", {}).values():
            for item in subject.get("choice_questions", []):
                if item.get("selected"):
                    count += 1
        return count

    def _update_answer_card(self) -> None:
        if not hasattr(self, "answer_card"):
            return
        flat = self._flat_question_refs()
        current_flat_index = 0
        for idx, ref in enumerate(flat):
            if ref == (self.current_subject, self.current_index):
                current_flat_index = idx
                break
        self.answer_card.update_status({}, current_flat_index)
        self.answer_card.summary_label.setText(f"已做题数：{self._answered_count()}/{len(flat)}")

    def _set_location(self, subject: str, index: int) -> None:
        self.current_subject = subject
        self.current_index = index
        self.pivot.blockSignals(True)
        self.pivot.setCurrentItem(subject)
        self.pivot.blockSignals(False)
        self.render_question()

    def _init_shortcuts(self) -> None:
        shortcuts = APP_SETTINGS_TEMPLATE["answer_shortcuts"] | self.settings.get("answer_shortcuts", {})
        self.prev_shortcut = QShortcut(QKeySequence(shortcuts.get("prev_question", "1")), self)
        self.prev_shortcut.activated.connect(self.prev_question)
        self.next_shortcut = QShortcut(QKeySequence(shortcuts.get("next_question", "2")), self)
        self.next_shortcut.activated.connect(self.next_question)
