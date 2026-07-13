from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, FluentIcon, Pivot, PrimaryPushButton, PushButton, StrongBodyLabel, TeachingTip, TeachingTipTailPosition, isDarkTheme

from answer.answer_window import AnswerWindow
from ui.widgets.choice import AnswerCard, OptionCard
from config.settings import SUBJECTS
from models.base import FavoriteQuestion
from ui.widgets.base import StyledCardWidget


class SubjectReviewPage(QWidget):
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
        body.addWidget(self.content_card, 1)
        root.addLayout(body, 1)
        self._apply_text_styles()

    def render_question(self, question_index: int) -> None:
        item = self.questions[question_index]
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

    def _apply_text_styles(self) -> None:
        text_color = "white" if isDarkTheme() else ""
        secondary_color = "rgba(255, 255, 255, 0.88)" if isDarkTheme() else ""
        self.question_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.answer_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.explanation_label.setStyleSheet(f"color: {secondary_color};" if secondary_color else "")


class LanExamReviewWindow(AnswerWindow):
    favorite_changed = pyqtSignal()

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
        self.subject_pages: dict[str, SubjectReviewPage] = {}

        self.setWindowTitle(f"{exam_name} - 题目详情")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1040, 660)
        self.setObjectName("lanExamReviewWindow")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.back_button = PushButton("返回", self)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel(exam_name, self)
        top.addWidget(self.back_button)
        top.addWidget(self.title_label, 1)
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

        self.page_holder = QStackedWidget(self)
        root.addWidget(self.page_holder, 1)

        for subject_key in self.subject_order:
            page = SubjectReviewPage(self.result_payload["details"][subject_key]["choice_questions"], self.page_holder)
            page.answer_card.question_selected.connect(self.jump_to_question)
            self.subject_pages[subject_key] = page
            self.page_holder.addWidget(page)

        nav = QHBoxLayout()
        nav.setSpacing(10)
        self.prev_button = PrimaryPushButton("上一题", self)
        self.next_button = PrimaryPushButton("下一题", self)
        self.favorite_button = PushButton("收藏题目", self)
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        nav.addSpacing(232 + 1 + 28)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addWidget(self.favorite_button)
        nav.addStretch(1)
        root.addLayout(nav)

        self._apply_window_style()
        if self.current_subject:
            self.pivot.setCurrentItem(self.current_subject)
        self.render_current()

    def _apply_window_style(self) -> None:
        background = "#202020" if isDarkTheme() else "#f3f3f3"
        self.setStyleSheet(f"QWidget#lanExamReviewWindow{{background-color: {background};}}")
        self.title_label.setStyleSheet("color: white;" if isDarkTheme() else "")

    def _switch_subject(self, subject_key: str) -> None:
        if not subject_key:
            return
        self.current_subject = subject_key
        self.current_index = 0
        self.render_current()

    def render_current(self) -> None:
        if not self.current_subject:
            return
        page = self.subject_pages[self.current_subject]
        self.page_holder.setCurrentWidget(page)
        page.render_question(self.current_index)
        self.prev_button.setEnabled(self._flat_index() > 0)
        self.next_button.setEnabled(self._flat_index() < len(self._flat_question_refs()) - 1)
        self._sync_favorite_text()
        self._update_current_answer_card()

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
            for local_index, _item in enumerate(self.result_payload["details"][subject_key]["choice_questions"]):
                refs.append((subject_key, local_index))
        return refs

    def _flat_index(self) -> int:
        return self._flat_question_refs().index((self.current_subject, self.current_index))

    def _build_subject_card_states(self, subject: str) -> dict[int, dict]:
        states: dict[int, dict] = {}
        for local_index, item in enumerate(self.result_payload["details"][subject]["choice_questions"]):
            states[local_index] = {
                "state": "correct" if item.get("is_correct") else "wrong",
                "marked": False,
                "answered": bool(item.get("selected")),
            }
        return states

    def _update_current_answer_card(self) -> None:
        page = self.subject_pages[self.current_subject]
        page.answer_card.update_exam_status(self._build_subject_card_states(self.current_subject), self.current_index)
        page.answer_card.summary_label.setText(
            f"已做题数：{sum(1 for item in self.result_payload['details'][self.current_subject]['choice_questions'] if item.get('selected'))}/{len(self.result_payload['details'][self.current_subject]['choice_questions'])}"
        )

    def _current_item(self) -> dict:
        return self.result_payload["details"][self.current_subject]["choice_questions"][self.current_index]

    def _build_question_id(self, item: dict) -> str:
        return f"lan_exam_{self.current_subject}_{self.exam_name}_{item['id']}"

    def _sync_favorite_text(self) -> None:
        item = self._current_item()
        exists = self.favorite_manager.get_question(self.current_subject, self._build_question_id(item)) is not None
        self.favorite_button.setText("已收藏" if exists else "收藏题目")

    def toggle_favorite(self) -> None:
        item = self._current_item()
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
        is_favorite = self.favorite_manager.toggle_favorite(payload)
        self.favorite_changed.emit()
        self._sync_favorite_text()
        if is_favorite:
            TeachingTip.create(
                self.favorite_button,
                "收藏成功",
                "题目已加入收藏夹",
                icon=FluentIcon.HEART,
                duration=1500,
                tailPosition=TeachingTipTailPosition.BOTTOM,
                parent=self,
            )
        else:
            TeachingTip.create(
                self.favorite_button,
                "已移出收藏",
                "题目已从收藏夹移除",
                icon=FluentIcon.DELETE,
                duration=1500,
                tailPosition=TeachingTipTailPosition.BOTTOM,
                parent=self,
            )
