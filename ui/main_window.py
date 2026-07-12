from __future__ import annotations

from PyQt6.QtCore import QEvent, QRect, Qt
from PyQt6.QtWidgets import QApplication, QWidget
from qfluentwidgets import FluentIcon, MSFluentWindow

from answer.choice_answer import ChoiceAnswerWindow
from answer.python import PythonAnswerWindow
from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from core.eye_care import EyeCareReminder
from core.json_store import JsonStore
from models.python.question import PythonQuestionBank
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
        self.wrong_book_page = WrongBookPage(wrong_manager, self)
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

    def open_choice_answer(self, subject: str, bank_name: str):
        bank = self.question_index_manager.load_bank(subject, bank_name)
        if isinstance(bank, PythonQuestionBank):
            self.answer_window = PythonAnswerWindow(
                question_bank=bank,
                user_manager=self.user_manager,
            )
        else:
            self.answer_window = ChoiceAnswerWindow(
                question_bank=bank,
                user_manager=self.user_manager,
                wrong_manager=self.wrong_manager,
                favorite_manager=self.favorite_manager,
            )
        self.answer_window.window_closed.connect(self._restore_after_answer)
        self._set_locked(True)
        self.showMinimized()
        self.answer_window.show()
        self.answer_window.raise_()
        self.answer_window.activateWindow()

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
