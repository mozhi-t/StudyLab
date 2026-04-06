from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, MessageBox, Pivot, PrimaryPushButton, PushButton, StrongBodyLabel, isDarkTheme

from answer.answer_window import AnswerWindow
from answer.choice_answer import OptionCard
from answer.lan_exam_review_window import LanExamReviewWindow
from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE, SUBJECTS
from core.datetime_utils import parse_datetime
from core.json_store import JsonStore
from core.lan_exam_store import LanExamStore
from models.wrong_question import WrongQuestion
from ui.widgets.answer_card import AnswerCard
from ui.widgets.styled_card import StyledCardWidget


class SubjectExamPage(QWidget):
    question_selected = pyqtSignal(int)
    option_selected = pyqtSignal(str)

    def __init__(self, questions: list[dict], parent: QWidget | None = None):
        super().__init__(parent)
        self.questions = questions
        self.option_cards: dict[str, OptionCard] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setSpacing(14)

        self.answer_card = AnswerCard(self)
        self.answer_card.setFixedWidth(232)
        self.answer_card.set_questions(len(questions))
        self.answer_card.question_selected.connect(self.question_selected.emit)
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
        font = QFont(self.question_label.font())
        font.setPointSize(12)
        font.setBold(False)
        self.question_label.setFont(font)
        self.question_label.setWordWrap(True)
        right.addWidget(self.question_label, 0, Qt.AlignmentFlag.AlignTop)

        self.option_group = QButtonGroup(self)
        self.option_group.setExclusive(True)
        for key in ["A", "B", "C", "D"]:
            option_card = OptionCard(key, self)
            option_card.button.clicked.connect(lambda checked=False, option=key: self.option_selected.emit(option))
            self.option_group.addButton(option_card.button)
            self.option_cards[key] = option_card
            right.addWidget(option_card)
        right.addStretch(1)
        body.addWidget(self.content_card, 1)
        root.addLayout(body, 1)
        self._apply_text_styles()

    def render_question(self, question_index: int, selected: str) -> None:
        question = self.questions[question_index]
        self.question_label.setText(f"{question['id']}. {question['question']}")
        self.option_group.setExclusive(False)
        for button in self.option_group.buttons():
            button.setChecked(False)
        self.option_group.setExclusive(True)
        for key, option_card in self.option_cards.items():
            option_card.set_option_text(f"{key}. {question['options'].get(key, '')}")
            option_card.set_checked(selected == key)
            option_card.set_enabled(True)
            option_card.set_state("default")

    def _apply_text_styles(self) -> None:
        self.question_label.setStyleSheet("color: white;" if isDarkTheme() else "")


class LanExamWindow(AnswerWindow):
    submit_requested = pyqtSignal(dict)
    favorite_changed = pyqtSignal()

    def __init__(self, paper: dict, wrong_manager, favorite_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.paper = paper
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.store = LanExamStore()
        self.settings = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE).load()
        self.answers = self.store.load_inputs(self.paper["exam_name"])
        self.subject_order = [
            name for name, subject in paper.get("subjects", {}).items()
            if subject.get("enabled") and subject.get("choice_questions")
        ]
        self.current_subject = self.subject_order[0] if self.subject_order else ""
        self.current_index = 0
        self.marked_questions: set[tuple[str, int]] = set()
        self.subject_pages: dict[str, SubjectExamPage] = {}
        self.review_window: LanExamReviewWindow | None = None
        self.started_at = datetime.now()
        self.result_payload: dict | None = None
        self.wrongs_recorded = False
        self.auto_submitted_due_time = False

        self.setWindowTitle(self.paper["exam_name"])
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1040, 660)
        self.setObjectName("lanExamWindow")
        self._apply_window_style()

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
        self.render_current()
        self._init_timer()
        self._apply_text_styles()

    def _init_exam_page(self) -> None:
        root = QVBoxLayout(self.exam_page)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.back_button = PushButton("返回", self.exam_page)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel(self.paper["exam_name"], self.exam_page)
        self.remaining_label = StrongBodyLabel("", self.exam_page)
        self.submit_button = PrimaryPushButton("交卷", self.exam_page)
        self.submit_button.clicked.connect(self.confirm_submit)
        top.addWidget(self.back_button)
        top.addWidget(self.title_label, 1)
        top.addWidget(self.remaining_label)
        top.addWidget(self.submit_button)
        root.addLayout(top)

        self.pivot = Pivot(self.exam_page)
        self.pivot.currentItemChanged.connect(self._switch_subject)
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        for subject_key in self.subject_order:
            self.pivot.addItem(routeKey=subject_key, text=SUBJECTS.get(subject_key, subject_key), onClick=lambda: None)
        root.addLayout(nav_layout)

        self.subject_stack = QStackedWidget(self.exam_page)
        for subject_key in self.subject_order:
            page = SubjectExamPage(self.paper["subjects"][subject_key]["choice_questions"], self.subject_stack)
            page.question_selected.connect(self.jump_to_question)
            page.option_selected.connect(self.select_option)
            self.subject_pages[subject_key] = page
            self.subject_stack.addWidget(page)
        root.addWidget(self.subject_stack, 1)

        nav = QHBoxLayout()
        nav.setSpacing(10)
        self.prev_button = PrimaryPushButton("上一题", self.exam_page)
        self.next_button = PrimaryPushButton("下一题", self.exam_page)
        self.mark_button = PushButton("标记题目", self.exam_page)
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        self.mark_button.clicked.connect(self.toggle_mark_current)
        nav.addSpacing(232 + 1 + 28)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addWidget(self.mark_button)
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
        status_font = QFont(self.submit_status_label.font())
        status_font.setPointSize(28)
        status_font.setWeight(QFont.Weight.DemiBold)
        self.submit_status_label.setFont(status_font)
        root.addWidget(self.submit_status_label)
        self.auto_submit_hint_label = BodyLabel("考试时间已到，已自动交卷", self.submit_page)
        self.auto_submit_hint_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.auto_submit_hint_label.hide()
        root.addWidget(self.auto_submit_hint_label)

        score_row = QHBoxLayout()
        score_row.setContentsMargins(0, 0, 0, 0)
        score_row.setSpacing(12)
        score_row.addStretch(1)
        self.score_label = StrongBodyLabel("", self.submit_page)
        score_font = QFont(self.score_label.font())
        score_font.setPointSize(16)
        score_font.setWeight(QFont.Weight.DemiBold)
        self.score_label.setFont(score_font)
        self.score_label.hide()
        score_row.addWidget(self.score_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.detail_button = PrimaryPushButton("题目详情", self.submit_page)
        self.detail_button.clicked.connect(self.show_review)
        self.detail_button.hide()
        score_row.addWidget(self.detail_button, 0, Qt.AlignmentFlag.AlignVCenter)
        score_row.addStretch(1)
        root.addLayout(score_row)
        root.addStretch(1)

    def _apply_window_style(self) -> None:
        background = "#202020" if isDarkTheme() else "#f3f3f3"
        self.setStyleSheet(f"QWidget#lanExamWindow{{background-color: {background};}}")

    def _apply_text_styles(self) -> None:
        text_color = "white" if isDarkTheme() else ""
        secondary_color = "rgba(255, 255, 255, 0.88)" if isDarkTheme() else ""
        self.title_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.remaining_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.submit_status_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.score_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.auto_submit_hint_label.setStyleSheet(f"color: {secondary_color};" if secondary_color else "")

    def _init_shortcuts(self) -> None:
        shortcuts = APP_SETTINGS_TEMPLATE["answer_shortcuts"] | self.settings.get("answer_shortcuts", {})
        self.prev_shortcut = QShortcut(QKeySequence(shortcuts.get("prev_question", "1")), self)
        self.prev_shortcut.activated.connect(self.prev_question)
        self.next_shortcut = QShortcut(QKeySequence(shortcuts.get("next_question", "2")), self)
        self.next_shortcut.activated.connect(self.next_question)
        self.mark_shortcut = QShortcut(QKeySequence(shortcuts.get("mark_question", "3")), self)
        self.mark_shortcut.activated.connect(self.toggle_mark_current)

    def _init_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_remaining)
        self.timer.start(1000)
        self._update_remaining()

    def _switch_subject(self, subject_key: str) -> None:
        if not subject_key:
            return
        self.current_subject = subject_key
        self.current_index = 0
        self.render_current()

    def current_question_id(self) -> int:
        return self.paper["subjects"][self.current_subject]["choice_questions"][self.current_index]["id"]

    def _selected_for(self, subject: str, local_index: int) -> str:
        question_id = self.paper["subjects"][subject]["choice_questions"][local_index]["id"]
        questions = self.answers.get("subjects", {}).get(subject, {}).get("choice_questions", [])
        for item in questions:
            if int(item["id"]) == int(question_id):
                return item.get("selected", "")
        return ""

    def render_current(self) -> None:
        if not self.current_subject:
            return
        page = self.subject_pages[self.current_subject]
        self.subject_stack.setCurrentWidget(page)
        page.render_question(self.current_index, self._selected_for(self.current_subject, self.current_index))
        self.prev_button.setEnabled(self._flat_index() > 0)
        self.next_button.setEnabled(self._flat_index() < len(self._flat_question_refs()) - 1)
        self.mark_button.setText("取消标记" if self._current_marked() else "标记题目")
        self._update_current_answer_card()

    def select_option(self, option: str) -> None:
        subjects = self.answers.setdefault("subjects", {})
        subject = subjects.setdefault(self.current_subject, {"choice_questions": []})
        questions = subject["choice_questions"]
        question_id = self.current_question_id()
        for item in questions:
            if int(item["id"]) == int(question_id):
                item["selected"] = option
                break
        else:
            questions.append({"id": question_id, "selected": option})
        self.store.save_inputs(self.paper["exam_name"], self.answers)
        self.render_current()

    def toggle_mark_current(self) -> None:
        key = (self.current_subject, self.current_index)
        if key in self.marked_questions:
            self.marked_questions.remove(key)
        else:
            self.marked_questions.add(key)
        self.render_current()

    def prev_question(self) -> None:
        flat_index = self._flat_index()
        if flat_index > 0:
            subject, local_index = self._flat_question_refs()[flat_index - 1]
            self._set_location(subject, local_index)

    def next_question(self) -> None:
        flat_index = self._flat_index()
        refs = self._flat_question_refs()
        if flat_index < len(refs) - 1:
            subject, local_index = refs[flat_index + 1]
            self._set_location(subject, local_index)

    def jump_to_question(self, index: int) -> None:
        self._set_location(self.current_subject, index)

    def _set_location(self, subject: str, local_index: int) -> None:
        self.current_subject = subject
        self.current_index = local_index
        self.pivot.blockSignals(True)
        self.pivot.setCurrentItem(subject)
        self.pivot.blockSignals(False)
        self.render_current()

    def _flat_question_refs(self) -> list[tuple[str, int]]:
        refs: list[tuple[str, int]] = []
        for subject_key in self.subject_order:
            for local_index, _item in enumerate(self.paper["subjects"][subject_key]["choice_questions"]):
                refs.append((subject_key, local_index))
        return refs

    def _flat_index(self) -> int:
        return self._flat_question_refs().index((self.current_subject, self.current_index))

    def _current_marked(self) -> bool:
        return (self.current_subject, self.current_index) in self.marked_questions

    def _answered_count(self, subject: str) -> int:
        return sum(
            1
            for local_index, _item in enumerate(self.paper["subjects"][subject]["choice_questions"])
            if self._selected_for(subject, local_index)
        )

    def _build_subject_card_states(self, subject: str) -> dict[int, dict]:
        states: dict[int, dict] = {}
        for local_index, _item in enumerate(self.paper["subjects"][subject]["choice_questions"]):
            answered = bool(self._selected_for(subject, local_index))
            marked = (subject, local_index) in self.marked_questions
            state = "default"
            if marked and not answered:
                state = "marked"
            elif answered:
                state = "pending"
            states[local_index] = {
                "state": state,
                "marked": marked,
                "answered": answered,
            }
        return states

    def _update_current_answer_card(self) -> None:
        page = self.subject_pages[self.current_subject]
        page.answer_card.update_exam_status(self._build_subject_card_states(self.current_subject), self.current_index)
        page.answer_card.summary_label.setText(
            f"已做题数：{self._answered_count(self.current_subject)}/{len(self.paper['subjects'][self.current_subject]['choice_questions'])}"
        )

    def _remaining_seconds(self) -> int:
        duration_limit = self.paper.get("duration_minutes", 60) * 60
        elapsed = int((datetime.now() - self.started_at).total_seconds())
        end_time = parse_datetime(self.paper.get("end_time"))
        end_seconds = int((end_time - datetime.now()).total_seconds()) if end_time else duration_limit
        return max(min(duration_limit - elapsed, end_seconds), 0)

    def _update_remaining(self) -> None:
        remaining = self._remaining_seconds()
        minutes, seconds = divmod(remaining, 60)
        self.remaining_label.setText(f"剩余时间：{minutes:02d}:{seconds:02d}")
        if remaining == 0:
            self.timer.stop()
            self.submit_exam(auto_submitted_due_time=True)

    def confirm_submit(self) -> None:
        if self.stack.currentWidget() is self.submit_page:
            return
        dialog = MessageBox("确认交卷", "确认现在交卷吗？交卷后将无法继续作答。", self)
        dialog.yesButton.setText("确认交卷")
        dialog.cancelButton.setText("取消")
        if dialog.exec():
            self.submit_exam()

    def submit_exam(self, auto_submitted_due_time: bool = False) -> None:
        if self.stack.currentWidget() is self.submit_page:
            return
        self.auto_submitted_due_time = auto_submitted_due_time
        self.timer.stop()
        self.stack.setCurrentWidget(self.submit_page)
        self.auto_submit_hint_label.setVisible(self.auto_submitted_due_time)
        self.score_label.hide()
        self.detail_button.hide()
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
        self.review_window.favorite_changed.connect(self.favorite_changed)
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

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.stack.currentWidget() is self.exam_page:
            dialog = MessageBox("确认退出", "当前正在考试，关闭窗口将自动交卷，是否继续退出？", self)
            dialog.yesButton.setText("确认退出")
            dialog.cancelButton.setText("继续考试")
            if dialog.exec():
                self.submit_exam()
            event.ignore()
            return
        super().closeEvent(event)
