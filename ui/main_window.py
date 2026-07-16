from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import QEvent, QRect, Qt
from PyQt6.QtWidgets import QApplication, QWidget
from qfluentwidgets import FluentIcon, MSFluentWindow

from answer.choice_answer import ChoiceAnswerWindow
from answer.python import PythonAnswerWindow
from answer.selected_practice_window import SelectedPracticeWindow
from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from core.base.datetime_utils import now_text
from core.base.json_store import JsonStore
from ui.controllers import EyeCareReminder
from models.choice import QuestionBank, QuestionItem
from models.python.question import PythonQuestion, PythonQuestionBank
from ui.pages.about_page import AboutPage
from ui.pages.exam_page import ExamPage
from ui.pages.favorite_page import FavoritePage
from ui.pages.home_page import HomePage
from ui.pages.local_bank_page import LocalBankPage
from ui.pages.question_bank_page import QuestionBankPage
from ui.pages.settings_page import SettingsPage
from ui.pages.wrong_book_page import WrongBookPage


class MainWindow(MSFluentWindow):
    def __init__(self, user_manager, question_index_manager, wrong_manager, favorite_manager):
        super().__init__()
        self.user_manager = user_manager
        self.question_index_manager = question_index_manager
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.answer_window = None
        self.settings_store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)

        self.setWindowTitle("StudyLab")
        self.resize(1040, 680)
        self._restore_window_geometry()

        self.home_page = HomePage(user_manager, self)
        self.home_page.setObjectName("home_page")
        self.local_bank_page = LocalBankPage(question_index_manager, self)
        self.local_bank_page.setObjectName("local_bank_page")
        self.question_bank_page = QuestionBankPage(self)
        self.question_bank_page.setObjectName("question_bank_page")
        self.exam_page = ExamPage(wrong_manager, favorite_manager, self)
        self.exam_page.setObjectName("exam_page")
        self.wrong_book_page = WrongBookPage(wrong_manager, favorite_manager, self)
        self.wrong_book_page.setObjectName("wrong_book_page")
        self.favorite_page = FavoritePage(favorite_manager, self)
        self.favorite_page.setObjectName("favorite_page")
        self.settings_page = SettingsPage(question_index_manager, wrong_manager, favorite_manager, self)
        self.settings_page.setObjectName("settings_page")
        self.about_page = AboutPage(self)
        self.about_page.setObjectName("about_page")
        self.pages = [
            self.home_page,
            self.local_bank_page,
            self.question_bank_page,
            self.exam_page,
            self.wrong_book_page,
            self.favorite_page,
            self.settings_page,
            self.about_page,
        ]
        self.page_lock_overlays: list[QWidget] = []
        self._init_page_lock_overlays()

        self.local_bank_page.open_bank_requested.connect(self.open_choice_answer)
        self.exam_page.favorite_changed.connect(self.favorite_page.reload)
        self.favorite_page.practice_python_requested.connect(self.open_python_favorite)
        self.wrong_book_page.practice_python_requested.connect(self.open_python_favorite)
        self.favorite_page.practice_selected_requested.connect(self.open_selected_practice)
        self.wrong_book_page.practice_selected_requested.connect(self.open_selected_practice)
        self.wrong_book_page.favorite_changed.connect(self.favorite_page.reload)

        self.eye_care_reminder = EyeCareReminder(
            self,
            JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE),
        )
        self.settings_page.eye_care_changed.connect(self.eye_care_reminder.reload_config)
        self.settings_page.learning_goal_changed.connect(self.home_page.reload)
        self.settings_page.home_page_style_changed.connect(self.home_page.reload)

        self._register_pages()

    def _register_pages(self):
        self.addSubInterface(self.home_page, FluentIcon.HOME, "主页")
        self.addSubInterface(self.local_bank_page, FluentIcon.LIBRARY, "刷题")
        self.addSubInterface(self.question_bank_page, FluentIcon.DICTIONARY, "题库")
        self.addSubInterface(self.exam_page, FluentIcon.EDUCATION, "考试")
        self.addSubInterface(self.wrong_book_page, FluentIcon.HISTORY, "错题本")
        self.addSubInterface(self.favorite_page, FluentIcon.HEART, "收藏夹")
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置")
        self.addSubInterface(self.about_page, FluentIcon.INFO, "关于")

    def _init_page_lock_overlays(self) -> None:
        for page in self.pages:
            overlay = QWidget(page)
            overlay.hide()
            overlay.setStyleSheet("background-color: rgba(0, 0, 0, 76); border-radius: 0px;")
            overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            page.installEventFilter(self)
            self.page_lock_overlays.append(overlay)

    def open_choice_answer(self, subject: str, bank_name: str, initial_question_id: int | None = None):
        bank = self.question_index_manager.load_bank(subject, bank_name)
        self._open_loaded_bank(bank, initial_question_id)

    def _open_loaded_bank(self, bank, initial_question_id: int | None = None) -> None:
        if isinstance(bank, PythonQuestionBank):
            answer_window = PythonAnswerWindow(
                question_bank=bank,
                user_manager=self.user_manager,
                wrong_manager=self.wrong_manager,
                favorite_manager=self.favorite_manager,
                initial_question_id=initial_question_id,
            )
        else:
            answer_window = ChoiceAnswerWindow(
                question_bank=bank,
                user_manager=self.user_manager,
                wrong_manager=self.wrong_manager,
                favorite_manager=self.favorite_manager,
            )
        self._show_answer_window(answer_window)

    def _show_answer_window(self, answer_window) -> None:
        self.answer_window = answer_window
        self.answer_window.window_closed.connect(self._restore_after_answer)
        self._set_locked(True)
        self.showMinimized()
        self.answer_window.show()
        self.answer_window.raise_()
        self.answer_window.activateWindow()

    def open_python_favorite(self, bank_name: str, question_id: int) -> None:
        bank = self.question_index_manager.load_bank("python", bank_name)
        if not isinstance(bank, PythonQuestionBank):
            return
        question = next((item for item in bank.questions if item.id == question_id), None)
        if question is None:
            return
        single_question_bank = replace(
            bank,
            total_questions=1,
            questions=[question],
        )
        self._open_loaded_bank(single_question_bank, question_id)

    def open_selected_practice(self, items: list) -> None:
        if not items:
            return

        choice_items = [item for item in items if item.question_type != "python_programming"]
        python_items = [item for item in items if item.question_type == "python_programming"]
        choice_bank = self._build_selected_choice_bank(choice_items)
        python_bank = self._build_selected_python_bank(python_items)

        if choice_bank is not None and python_bank is None:
            self._show_answer_window(
                ChoiceAnswerWindow(
                    question_bank=choice_bank,
                    user_manager=self.user_manager,
                    wrong_manager=self.wrong_manager,
                    favorite_manager=self.favorite_manager,
                )
            )
            return

        if python_bank is not None and choice_bank is None:
            self._show_answer_window(
                PythonAnswerWindow(
                    question_bank=python_bank,
                    user_manager=self.user_manager,
                    wrong_manager=self.wrong_manager,
                    favorite_manager=self.favorite_manager,
                    initial_question_id=python_bank.questions[0].id,
                )
            )
            return

        answer_window = SelectedPracticeWindow(
            choice_bank=choice_bank,
            python_bank=python_bank,
            user_manager=self.user_manager,
            wrong_manager=self.wrong_manager,
            favorite_manager=self.favorite_manager,
        )
        self._show_answer_window(answer_window)

    @staticmethod
    def _build_selected_choice_bank(items: list) -> QuestionBank | None:
        if not items:
            return None
        questions = [
            QuestionItem(
                id=index,
                question=item.question,
                options=item.options,
                answer=item.answer,
                explanation=item.explanation,
                source_question_id=item.question_id,
                source_bank_name=item.bank_name,
                source_bank_question_id=item.bank_question_id,
                source_subject=item.subject,
            )
            for index, item in enumerate(items, 1)
        ]
        return QuestionBank(
            name="选中选择题练习",
            subject=items[0].subject,
            create_time=now_text(),
            difficulty=1,
            total_questions=len(questions),
            questions=questions,
        )

    @staticmethod
    def _build_selected_python_bank(items: list) -> PythonQuestionBank | None:
        if not items:
            return None
        questions = [
            PythonQuestion(
                id=index,
                code=item.payload.get("code", ""),
                answer=item.answer,
                grading_points=MainWindow._normalize_python_grading_points(
                    item.payload.get("grading_points", [])
                ),
                full_score=item.payload.get("full_score", 20),
                source_question_id=item.question_id,
                source_bank_name=item.bank_name,
                source_bank_question_id=item.bank_question_id,
                source_question_title=item.question,
            )
            for index, item in enumerate(items, 1)
        ]
        return PythonQuestionBank(
            name="选中 Python 编程题练习",
            subject="python",
            create_time=now_text(),
            difficulty=1,
            total_questions=len(questions),
            questions=questions,
        )

    @staticmethod
    def _normalize_python_grading_points(points: list) -> list[dict]:
        """Upgrade historical three-point grading data for selected practice."""
        normalized = [dict(point) for point in points]
        point_types = {point.get("type") for point in normalized}

        if "template_integrity" not in point_types:
            execution = next(
                (point for point in normalized if point.get("type") == "execution"),
                None,
            )
            if execution is not None and float(execution.get("score", 0)) >= 2:
                execution["score"] = float(execution["score"]) - 1
                insert_at = normalized.index(execution)
                normalized.insert(
                    insert_at,
                    {
                        "id": "template_integrity",
                        "type": "template_integrity",
                        "score": 1,
                    },
                )

        return normalized

    def _restore_after_answer(self):
        if not self.isVisible():
            return
        self._set_locked(False)
        self.answer_window = None
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.wrong_book_page.reload()
        self.favorite_page.reload()
        self.home_page.reload()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_page_lock_overlays()

    def closeEvent(self, event):
        self._save_window_geometry()
        super().closeEvent(event)

    def _restore_window_geometry(self) -> None:
        settings = APP_SETTINGS_TEMPLATE | self.settings_store.load()
        mode = settings.get("window_memory_mode", "default")
        geometry = settings.get("window_geometry", {})
        if not isinstance(geometry, dict):
            return

        if mode in {"size", "size_position"}:
            width = max(int(geometry.get("width", 1040)), 800)
            height = max(int(geometry.get("height", 680)), 560)
            self.resize(width, height)

        restored_position = False
        if mode in {"position", "size_position"}:
            x = int(geometry.get("x", self.x()))
            y = int(geometry.get("y", self.y()))
            candidate = QRect(x, y, self.width(), self.height())
            if any(screen.availableGeometry().intersects(candidate) for screen in QApplication.screens()):
                self.move(x, y)
                restored_position = True
        if not restored_position:
            self._center_on_primary_screen()

    def _center_on_primary_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        x = available.x() + (available.width() - self.width()) // 2
        centered_y = available.y() + (available.height() - self.height()) // 2
        y = min(centered_y + 40, available.bottom() - self.height() + 1)
        self.move(x, y)

    def _save_window_geometry(self) -> None:
        settings = APP_SETTINGS_TEMPLATE | self.settings_store.load()
        mode = settings.get("window_memory_mode", "default")
        if mode == "default":
            return

        rect = self.normalGeometry() if self.isMaximized() else self.geometry()
        geometry = dict(settings.get("window_geometry", {}))
        if mode in {"size", "size_position"}:
            geometry.update(width=rect.width(), height=rect.height())
        if mode in {"position", "size_position"}:
            geometry.update(x=rect.x(), y=rect.y())
        settings["window_geometry"] = geometry
        self.settings_store.save(settings)

    def eventFilter(self, obj, event):
        if hasattr(self, "pages") and obj in self.pages and event.type() in {QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest}:
            self._update_overlay_for_page(obj)
        return super().eventFilter(obj, event)

    def _set_locked(self, locked: bool) -> None:
        self._update_page_lock_overlays()
        for overlay in self.page_lock_overlays:
            overlay.setVisible(locked)
            if locked:
                overlay.raise_()

    def _update_page_lock_overlays(self) -> None:
        for page in self.pages:
            self._update_overlay_for_page(page)

    def _update_overlay_for_page(self, page) -> None:
        try:
            index = self.pages.index(page)
        except ValueError:
            return
        overlay = self.page_lock_overlays[index]
        overlay.setGeometry(page.rect())
        if overlay.isVisible():
            overlay.raise_()
