from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCloseEvent, QFont, QPainter
from PyQt6.QtWidgets import QButtonGroup, QGridLayout, QHBoxLayout, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, Pivot, PrimaryPushButton, PushButton, RadioButton, StrongBodyLabel, isDarkTheme

try:
    from .common import StyledCardWidget
except ImportError:
    from ui.common import StyledCardWidget


SUBJECTS = {
    "chinese": "语文",
    "math": "数学",
    "english": "英语",
    "computer_basic": "计算机基础",
    "python": "Python",
    "mysql": "MySQL",
}


class AnswerWindow(QWidget):
    window_closed = pyqtSignal()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.window_closed.emit()
        super().closeEvent(event)


class OptionCard(StyledCardWidget):
    def __init__(self, option_key: str, parent: QWidget | None = None):
        self._state = "default"
        super().__init__(parent, radius=12, light_border_alpha=34)
        self.option_key = option_key
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.button = RadioButton(self)
        self.button.setText("")
        self.button.setFixedWidth(24)
        self.button.setMinimumHeight(24)
        self.button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.text_label = BodyLabel("", self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(12)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.text_label, 1, Qt.AlignmentFlag.AlignVCenter)

    def set_option_text(self, text: str) -> None:
        self.text_label.setText(text)

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
            self.text_label.setStyleSheet("color: rgb(19, 126, 67); font-weight: 600;")
        elif self._state == "wrong":
            self.text_label.setStyleSheet("color: rgb(198, 52, 52); font-weight: 600;")
        else:
            self.text_label.setStyleSheet("color: white;" if isDarkTheme() else "")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.button.isEnabled():
            self.button.click()
            event.accept()
            return
        super().mousePressEvent(event)


class QuestionStatusCard(StyledCardWidget):
    clicked = pyqtSignal()

    def __init__(self, text: str, parent: QWidget | None = None):
        self._state = "default"
        self._is_current = False
        self._display_text = text
        super().__init__(parent, radius=10, light_border_alpha=34)
        self.setFixedSize(36, 36)

        self.label = BodyLabel(text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self.label.font())
        font.setPointSize(9)
        font.setBold(True)
        self.label.setFont(font)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

    def set_state(self, state: str, is_current: bool = False, display_text: str | None = None) -> None:
        self._state = state
        self._is_current = is_current
        if display_text is not None:
            self._display_text = display_text
            self.label.setText(display_text)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _normalBackgroundColor(self):
        if self._state == "correct":
            return QColor(15, 163, 97, 235)
        if self._state == "wrong":
            return QColor(224, 72, 72, 235)
        return super()._normalBackgroundColor()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._is_current:
            self._apply_text_color()
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        pen = painter.pen()
        pen.setColor(QColor(255, 255, 255, 140) if self._state in {"correct", "wrong"} else QColor(0, 120, 212, 170))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)
        self._apply_text_color()

    def _apply_text_color(self) -> None:
        if self._state in {"correct", "wrong"}:
            self.label.setStyleSheet("color: white;")
        elif isDarkTheme():
            self.label.setStyleSheet("color: white;")
        else:
            self.label.setStyleSheet("")


class AnswerCard(QWidget):
    question_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.buttons: list[QuestionStatusCard] = []
        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(4)
        self.grid.setVerticalSpacing(4)

        self.summary_card = StyledCardWidget(self, radius=12, light_border_alpha=34)
        self.summary_label = BodyLabel("已做题数：0/0", self.summary_card)
        if isDarkTheme():
            self.summary_label.setStyleSheet("color: white;")
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        summary_layout.addWidget(self.summary_label, 0, Qt.AlignmentFlag.AlignLeft)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        root.addLayout(self.grid)
        root.addWidget(self.summary_card)

    def set_questions(self, count: int) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.buttons.clear()

        columns = 6
        for idx in range(count):
            button = QuestionStatusCard(str(idx + 1), self)
            button.clicked.connect(lambda i=idx: self.question_selected.emit(i))
            self.grid.addWidget(button, idx // columns, idx % columns)
            self.buttons.append(button)

        self.update_exam_status({}, 0)

    def update_exam_status(self, states: dict[int, dict], current_index: int) -> None:
        answered = 0
        for idx, button in enumerate(self.buttons):
            payload = states.get(idx, {})
            state = payload.get("state", "default")
            answered_flag = payload.get("answered", False)
            if answered_flag:
                answered += 1
            button.set_state(state, is_current=idx == current_index, display_text=str(idx + 1))
        total = len(self.buttons)
        self.summary_label.setText(f"已做题数：{answered}/{total}")


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
        self.answer_label.setText(f"正确答案：{item['correct_answer']}    他的答案：{item.get('selected') or '未作答'}")
        self.explanation_label.setText(f"解析：{item['explanation']}")

    def _apply_text_styles(self) -> None:
        text_color = "white" if isDarkTheme() else ""
        secondary_color = "rgba(255, 255, 255, 0.88)" if isDarkTheme() else ""
        self.question_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.answer_label.setStyleSheet(f"color: {text_color};" if text_color else "")
        self.explanation_label.setStyleSheet(f"color: {secondary_color};" if secondary_color else "")


class ServerExamReviewWindow(AnswerWindow):
    def __init__(self, exam_name: str, username: str, result_payload: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.exam_name = exam_name
        self.username = username or "未命名用户"
        self.result_payload = result_payload
        self.subject_order = [
            name for name, subject in result_payload.get("details", {}).items() if subject.get("choice_questions")
        ]
        self.current_subject = self.subject_order[0] if self.subject_order else ""
        self.current_index = 0
        self.subject_pages: dict[str, SubjectReviewPage] = {}

        self.setWindowTitle(f"{exam_name}-{self.username}的做题详情")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1040, 660)
        self.setObjectName("serverExamReviewWindow")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.back_button = PushButton("返回", self)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel(f"{exam_name}-{self.username}的做题详情", self)
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
        self.prev_button.clicked.connect(self.prev_question)
        self.next_button.clicked.connect(self.next_question)
        nav.addSpacing(232 + 1 + 28)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.next_button)
        nav.addStretch(1)
        root.addLayout(nav)

        self._apply_window_style()
        if self.current_subject:
            self.pivot.setCurrentItem(self.current_subject)
        self.render_current()

    def _apply_window_style(self) -> None:
        background = "#202020" if isDarkTheme() else "#f3f3f3"
        self.setStyleSheet(f"QWidget#serverExamReviewWindow{{background-color: {background};}}")
        self.title_label.setStyleSheet("color: white;" if isDarkTheme() else "")

    def _switch_subject(self, subject_key: str) -> None:
        if not subject_key:
            return
        self.current_subject = subject_key
        self.current_index = 0
        self.render_current()

    def render_current(self) -> None:
        if not self.current_subject:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return
        page = self.subject_pages[self.current_subject]
        self.page_holder.setCurrentWidget(page)
        page.render_question(self.current_index)
        refs = self._flat_question_refs()
        self.prev_button.setEnabled(self._flat_index() > 0)
        self.next_button.setEnabled(self._flat_index() < len(refs) - 1)
        self._update_current_answer_card()

    def prev_question(self) -> None:
        flat_index = self._flat_index()
        if flat_index > 0:
            subject, local_index = self._flat_question_refs()[flat_index - 1]
            self._set_location(subject, local_index)

    def next_question(self) -> None:
        refs = self._flat_question_refs()
        flat_index = self._flat_index()
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
        answered = sum(
            1 for item in self.result_payload["details"][self.current_subject]["choice_questions"] if item.get("selected")
        )
        total = len(self.result_payload["details"][self.current_subject]["choice_questions"])
        page.answer_card.summary_label.setText(f"已做题数：{answered}/{total}")
