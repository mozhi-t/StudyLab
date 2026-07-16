from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QStackedWidget, QVBoxLayout
from qfluentwidgets import Pivot, PushButton, StrongBodyLabel, isDarkTheme

from answer.answer_window import AnswerWindow
from answer.choice_answer import ChoiceAnswerWindow
from answer.python import PythonAnswerWindow


class SelectedPracticeWindow(AnswerWindow):
    """Practice selected records with navigation between question types."""

    def __init__(
        self,
        choice_bank,
        python_bank,
        user_manager,
        wrong_manager,
        favorite_manager,
        parent=None,
    ):
        super().__init__(parent)
        self.practice_pages = []
        self.route_to_index: dict[str, int] = {}

        self.setWindowTitle("选题练习")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1320, 820)
        self.setMinimumSize(1120, 680)
        self.setObjectName("selectedPracticeWindow")
        background = "#202020" if isDarkTheme() else "#f3f3f3"
        self.setStyleSheet(f"QWidget#selectedPracticeWindow{{background-color:{background};}}")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.back_button = PushButton("返回", self)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel("选题练习", self)
        self.reset_button = PushButton("重置答题", self)
        self.reset_button.clicked.connect(self._reset_current_page)
        top.addWidget(self.back_button)
        top.addWidget(self.title_label, 1)
        top.addWidget(self.reset_button)
        root.addLayout(top)

        self.pivot = Pivot(self)
        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        nav.addWidget(self.pivot)
        nav.addStretch(1)
        root.addLayout(nav)

        self.stack = QStackedWidget(self)
        root.addWidget(self.stack, 1)

        if choice_bank is not None:
            page = ChoiceAnswerWindow(
                question_bank=choice_bank,
                user_manager=user_manager,
                wrong_manager=wrong_manager,
                favorite_manager=favorite_manager,
                parent=self.stack,
            )
            self._add_page("choice", "选择题", page)

        if python_bank is not None:
            page = PythonAnswerWindow(
                question_bank=python_bank,
                user_manager=user_manager,
                wrong_manager=wrong_manager,
                favorite_manager=favorite_manager,
                parent=self.stack,
            )
            self._add_page("python", "Python 编程题", page)

        self.pivot.currentItemChanged.connect(self._switch_page)
        if self.route_to_index:
            first_route = next(iter(self.route_to_index))
            self.pivot.setCurrentItem(first_route)
            self._switch_page(first_route)
        self.pivot.setVisible(len(self.route_to_index) > 1)

    def _add_page(self, route_key: str, title: str, page) -> None:
        page.setWindowFlag(Qt.WindowType.Window, False)
        page.setParent(self.stack)
        page.back_button.hide()
        page.title_label.hide()
        if hasattr(page, "reset_button"):
            page.reset_button.hide()
        if isinstance(page, PythonAnswerWindow):
            page.toolbar.setStretch(0, 0)
            page.toolbar.setStretch(1, 0)
            page.mode_switch.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
            page.mode_switch.setFixedWidth(page.mode_switch.sizeHint().width())
            page.toolbar.removeWidget(page.mode_switch)
            page.toolbar.insertStretch(2, 1)
            page.toolbar.insertWidget(3, page.mode_switch)
        self.practice_pages.append(page)
        self.stack.addWidget(page)
        self.route_to_index[route_key] = self.stack.indexOf(page)
        self.pivot.addItem(routeKey=route_key, text=title, onClick=lambda: None)

    def _switch_page(self, route_key: str) -> None:
        self.stack.setCurrentIndex(self.route_to_index.get(route_key, 0))
        self.reset_button.setText("重置本题" if route_key == "python" else "重置答题")

    def _reset_current_page(self) -> None:
        page = self.stack.currentWidget()
        if isinstance(page, ChoiceAnswerWindow):
            page.reset_session()
        elif isinstance(page, PythonAnswerWindow):
            page.reset_current_question()

    def closeEvent(self, event) -> None:
        for page in self.practice_pages:
            page.close()
        super().closeEvent(event)
