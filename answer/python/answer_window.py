from __future__ import annotations

import ast
import sys
from dataclasses import asdict
from pathlib import Path

from PyQt6.QtCore import QFileSystemWatcher, QProcess, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import (
    FluentIcon, InfoBar, InfoBarPosition, MessageBox, PrimaryPushButton,
    PushButton, SegmentedWidget, StrongBodyLabel, isDarkTheme,
)

from answer.answer_window import AnswerWindow
from answer.python.detail_window import PythonJudgeDetailWindow
from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from core.json_store import JsonStore
from core.python.judge import PythonJudge
from core.python.pycharm_launcher import PyCharmLauncher
from core.python.runner import PythonRunner
from core.python.workspace import PythonWorkspace
from models.python.grading import PythonJudgeResult
from models.python.question import PythonQuestion, PythonQuestionBank
from models.favorite_question import FavoriteQuestion
from models.study import ScoreResult
from models.wrong_question import WrongQuestion
from ui.widgets.python import PythonAnswerCard, PythonCodeEditor, PythonQuestionView, PythonResultCard
from ui.widgets.styled_card import StyledCardWidget


class PythonTaskThread(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task

    def run(self) -> None:
        try:
            self.completed.emit(self.task())
        except Exception as exc:
            self.failed.emit(str(exc))


class PythonAnswerWindow(AnswerWindow):
    def __init__(
        self,
        question_bank: PythonQuestionBank,
        user_manager,
        wrong_manager,
        favorite_manager,
        initial_question_id: int | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.question_bank = question_bank
        self.user_manager = user_manager
        self.wrong_manager = wrong_manager
        self.favorite_manager = favorite_manager
        self.settings_store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.settings = APP_SETTINGS_TEMPLATE | self.settings_store.load()
        self.settings["python_answer"] = APP_SETTINGS_TEMPLATE["python_answer"] | self.settings.get("python_answer", {})
        self.workspace = PythonWorkspace()
        self.runner = PythonRunner()
        self.judge = PythonJudge(self.runner)
        self.launcher = PyCharmLauncher()
        self.current_index = next(
            (index for index, question in enumerate(question_bank.questions) if question.id == initial_question_id),
            0,
        )
        self.prepared: set[int] = set()
        self.states: dict[int, str] = {}
        self.scores: dict[int, tuple[float, float]] = {}
        self.recorded_questions: set[int] = set()
        self.judge_results: dict[int, PythonJudgeResult] = {}
        self.task_thread: PythonTaskThread | None = None
        self.detail_window: PythonJudgeDetailWindow | None = None
        self.run_stopped_by_user = False
        self.study_session_id: int | None = None
        self._loading_editor = False

        self.setWindowTitle(question_bank.name)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1280, 820)
        self.setMinimumSize(980, 650)
        self.setObjectName("pythonAnswerWindow")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.answer_page = QWidget(self)
        outer.addWidget(self.answer_page)

        root = QVBoxLayout(self.answer_page)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(12)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.back_button = PushButton("返回", self)
        self.back_button.clicked.connect(self.close)
        self.title_label = StrongBodyLabel(question_bank.name, self)
        self.mode_switch = SegmentedWidget(self)
        self.mode_switch.addItem("builtin", "内置编辑器", lambda: None)
        self.mode_switch.addItem("pycharm", "PyCharm", lambda: None)
        self.mode_switch.currentItemChanged.connect(self._switch_mode)
        self.favorite_button = PushButton(FluentIcon.HEART, "收藏题目", self)
        self.reset_button = PushButton(FluentIcon.SYNC, "重置本题", self)
        self.run_button = PrimaryPushButton(FluentIcon.PLAY, "运行", self)
        self.submit_button = PrimaryPushButton(FluentIcon.SEND, "提交该题", self)
        self.favorite_button.clicked.connect(self.toggle_current_favorite)
        self.reset_button.clicked.connect(self.reset_current_question)
        self.run_button.clicked.connect(self.run_current)
        self.submit_button.clicked.connect(self.submit_current)
        toolbar.addWidget(self.back_button)
        toolbar.addWidget(self.title_label, 1)
        toolbar.addWidget(self.mode_switch)
        toolbar.addWidget(self.favorite_button)
        toolbar.addWidget(self.reset_button)
        toolbar.addWidget(self.run_button)
        toolbar.addWidget(self.submit_button)
        root.addLayout(toolbar)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.answer_card = PythonAnswerCard(self)
        self.answer_card.setFixedWidth(150)
        self.answer_card.set_questions(
            len(question_bank.questions), sum(question.full_score for question in question_bank.questions)
        )
        self.answer_card.question_selected.connect(self.jump_to_question)
        body.addWidget(self.answer_card)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.page_stack = QStackedWidget(self)
        self.editor_card = StyledCardWidget(self, radius=14, light_border_alpha=34)
        editor_layout = QVBoxLayout(self.editor_card)
        editor_layout.setContentsMargins(8, 8, 8, 8)
        self.editor = PythonCodeEditor(self.editor_card)
        self.editor.setStyleSheet("QPlainTextEdit{background: transparent; border: none;}")
        self.editor.textChanged.connect(self._editor_changed)
        editor_layout.addWidget(self.editor)
        self.question_view = PythonQuestionView(self)
        self.question_view.answer_requested.connect(self.open_in_pycharm)
        self.page_stack.addWidget(self.editor_card)
        self.page_stack.addWidget(self.question_view)
        right.addWidget(self.page_stack, 1)
        self.result_card = PythonResultCard(self)
        self.result_card.setMaximumHeight(180)
        right.addWidget(self.result_card)
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(300)
        self.save_timer.timeout.connect(self._save_editor)
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self._external_file_changed)
        self.run_process = QProcess(self)
        self.run_process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.run_process.readyReadStandardOutput.connect(self._read_run_stdout)
        self.run_process.readyReadStandardError.connect(self._read_run_stderr)
        self.run_process.finished.connect(self._interactive_run_finished)
        self.result_card.console.input_submitted.connect(self._write_run_input)
        self.judge_overlay = QWidget(self)
        self.judge_overlay.setStyleSheet("background-color: rgba(80, 80, 80, 145);")
        self.judge_overlay.setGeometry(self.rect())
        self.judge_overlay.hide()

        default_mode = self.settings["python_answer"].get("default_mode", "builtin")
        if default_mode not in {"builtin", "pycharm"}:
            default_mode = "builtin"
        self.mode_switch.setCurrentItem(default_mode)
        self._switch_mode(default_mode)
        self.render_question()
        self._apply_style()
        self.study_session_id = self.user_manager.start_study_session(
            subject="python", source_type="question_bank",
            source_key=f"python_{question_bank.name}", source_name=question_bank.name,
        )

    @property
    def current_question(self) -> PythonQuestion:
        return self.question_bank.questions[self.current_index]

    def _apply_style(self) -> None:
        background = "#202020" if isDarkTheme() else "#f3f3f3"
        self.setStyleSheet(f"QWidget#pythonAnswerWindow{{background-color:{background};}}")

    def _switch_mode(self, route_key: str) -> None:
        if route_key == "pycharm":
            self._save_editor()
            self.page_stack.setCurrentWidget(self.question_view)
        else:
            self._reload_editor_from_disk()
            self.page_stack.setCurrentWidget(self.editor_card)

    def render_question(self) -> None:
        question = self.current_question
        if self.current_index not in self.prepared:
            self.workspace.prepare_question(self.question_bank.name, question.id, question.code, reset=True)
            self.prepared.add(self.current_index)
        self.question_view.set_question(question.id, question.code)
        self._reload_editor_from_disk()
        self._watch_current_file()
        self.answer_card.refresh(self.current_index, self.states, self.scores)
        self._sync_favorite_button()

    def jump_to_question(self, index: int) -> None:
        if index == self.current_index:
            return
        self._save_editor()
        self.current_index = index
        self.render_question()

    def _editor_changed(self) -> None:
        if self._loading_editor:
            return
        self._set_working_state("modified")
        self.answer_card.refresh(self.current_index, self.states, self.scores)
        self.save_timer.start()

    def _set_working_state(self, state: str) -> None:
        if self.states.get(self.current_index) != "full":
            self.states[self.current_index] = state

    def _save_editor(self) -> None:
        if self._loading_editor or self.current_index not in self.prepared:
            return
        self.workspace.save(self.question_bank.name, self.current_question.id, self.editor.toPlainText())

    def _reload_editor_from_disk(self) -> None:
        if self.current_index not in self.prepared:
            return
        path = self.workspace.question_file(self.question_bank.name, self.current_question.id)
        if not path.exists():
            return
        source = path.read_text(encoding="utf-8")
        if source == self.editor.toPlainText():
            return
        self._loading_editor = True
        self.editor.setPlainText(source)
        self._loading_editor = False

    def _watch_current_file(self) -> None:
        watched = self.file_watcher.files()
        if watched:
            self.file_watcher.removePaths(watched)
        path = str(self.workspace.question_file(self.question_bank.name, self.current_question.id))
        if Path(path).exists():
            self.file_watcher.addPath(path)

    def _external_file_changed(self, path: str) -> None:
        if Path(path).exists() and path not in self.file_watcher.files():
            self.file_watcher.addPath(path)
        self._set_working_state("modified")
        if self.page_stack.currentWidget() is self.editor_card and not self.editor.document().isModified():
            self._reload_editor_from_disk()
        self.answer_card.refresh(self.current_index, self.states, self.scores)

    def reset_current_question(self) -> None:
        dialog = MessageBox("重置本题", "当前代码将被清空并恢复为题目模板，是否继续？", self)
        dialog.yesButton.setText("重置")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return
        question = self.current_question
        self.workspace.prepare_question(self.question_bank.name, question.id, question.code, reset=True)
        if self.states.get(self.current_index) != "full":
            self.states.pop(self.current_index, None)
            self.scores.pop(self.current_index, None)
        self._reload_editor_from_disk()
        self._watch_current_file()
        self.answer_card.refresh(self.current_index, self.states, self.scores)

    def open_in_pycharm(self) -> None:
        path = self.workspace.question_file(self.question_bank.name, self.current_question.id)
        install_dir = self.settings["python_answer"].get("pycharm_install_dir", "")
        success, message = self.launcher.launch(install_dir, path)
        if success:
            self._show_info("已启动 PyCharm", str(path))
        else:
            self._show_error("无法启动 PyCharm", message)

    def _prepare_source(self) -> tuple[str, Path]:
        if self.page_stack.currentWidget() is self.editor_card:
            self._save_editor()
        path = self.workspace.question_file(self.question_bank.name, self.current_question.id)
        return path.read_text(encoding="utf-8"), path

    def run_current(self) -> None:
        if self.run_process.state() != QProcess.ProcessState.NotRunning:
            self.run_stopped_by_user = True
            self.run_process.kill()
            return
        if not self._confirm_external_saved():
            return
        _source, path = self._prepare_source()
        self.run_stopped_by_user = False
        self._set_working_state("modified")
        self.answer_card.refresh(self.current_index, self.states, self.scores)
        self.result_card.console.begin()
        self.run_process.setWorkingDirectory(str(path.parent))
        self.run_process.setProgram(sys.executable)
        self.run_process.setArguments(["-I", "-B", "-X", "utf8", path.name])
        self.run_button.setText("停止")
        self.submit_button.setEnabled(False)
        self.run_process.start()

    def submit_current(self) -> None:
        if self.task_thread and self.task_thread.isRunning():
            return
        if not self._confirm_external_saved():
            return
        source, path = self._prepare_source()
        question = self.current_question
        if self.detail_window is not None:
            self.detail_window.close()
        self.detail_window = PythonJudgeDetailWindow(question, source, self)
        self.detail_window.window_closed.connect(self._judge_window_closed)
        self.detail_window.favorite_requested.connect(self.toggle_current_favorite)
        self.detail_window.set_favorite(self._is_current_favorite())
        self.judge_overlay.setGeometry(self.rect())
        self.judge_overlay.show()
        self.judge_overlay.raise_()
        self.detail_window.show()
        self.detail_window.raise_()
        self.detail_window.activateWindow()
        self._start_task(lambda: self.judge.judge(question, source, path), self._judge_finished)

    def _confirm_external_saved(self) -> bool:
        if self.page_stack.currentWidget() is not self.question_view:
            return True
        if not self.settings["python_answer"].get("remind_save_before_run", True):
            return True
        dialog = MessageBox("确认保存", "请先在 PyCharm 中按 Ctrl+S 保存代码，StudyLab 将读取磁盘文件。", self)
        dialog.yesButton.setText("已保存，继续")
        dialog.cancelButton.setText("取消")
        return bool(dialog.exec())

    def _start_task(self, task, handler) -> None:
        self.run_button.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.task_thread = PythonTaskThread(task, self)
        self.task_thread.completed.connect(handler)
        self.task_thread.failed.connect(self._task_failed)
        self.task_thread.finished.connect(self._task_ended)
        self.task_thread.start()

    def _read_run_stdout(self) -> None:
        self.result_card.console.append_program_output(bytes(self.run_process.readAllStandardOutput()).decode("utf-8", "replace"))

    def _read_run_stderr(self) -> None:
        self.result_card.console.append_program_output(bytes(self.run_process.readAllStandardError()).decode("utf-8", "replace"))

    def _write_run_input(self, value: str) -> None:
        if self.run_process.state() != QProcess.ProcessState.NotRunning:
            self.run_process.write(value.encode("utf-8"))

    def _interactive_run_finished(self, exit_code: int, _exit_status) -> None:
        self._read_run_stdout()
        self._read_run_stderr()
        self.result_card.console.finish()
        self.run_button.setText("运行")
        self.submit_button.setEnabled(True)
        if self.run_stopped_by_user or exit_code == 0:
            self._set_working_state("modified")
        else:
            self._set_working_state("failed")
        self.run_stopped_by_user = False
        self.answer_card.refresh(self.current_index, self.states, self.scores)

    def _judge_finished(self, result: PythonJudgeResult) -> None:
        self.judge_results[self.current_index] = result
        self.scores[self.current_index] = (result.earned, result.possible)
        if result.earned >= result.possible:
            self.states[self.current_index] = "full"
        elif result.earned > 0:
            self.states[self.current_index] = "partial"
        else:
            self.states[self.current_index] = "failed"
        if self.current_index not in self.recorded_questions:
            self.user_manager.record_answer(
                ScoreResult(result.earned, result.possible), subject="python", session_id=self.study_session_id,
            )
            self.recorded_questions.add(self.current_index)
        self.answer_card.refresh(self.current_index, self.states, self.scores)
        if result.earned < result.possible:
            self.wrong_manager.add_wrong(self._build_wrong(result))
        else:
            self.wrong_manager.remove_wrong("python", self._build_question_id())
        if self.detail_window is not None:
            self.detail_window.set_result(result)

    def _judge_window_closed(self) -> None:
        self.judge_overlay.hide()
        self.detail_window = None

    def _task_failed(self, message: str) -> None:
        self.states[self.current_index] = "failed"
        if self.detail_window is not None:
            self.detail_window.set_result(
                PythonJudgeResult(0, self.current_question.full_score, message=message)
            )

    def _task_ended(self) -> None:
        self.run_button.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.task_thread = None

    def _show_info(self, title: str, content: str) -> None:
        InfoBar.success(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)

    def _show_error(self, title: str, content: str) -> None:
        InfoBar.error(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=3500, parent=self)

    def toggle_current_favorite(self) -> None:
        favorite = self.favorite_manager.toggle_favorite(self._build_favorite())
        self._sync_favorite_button()
        if self.detail_window is not None:
            self.detail_window.set_favorite(favorite)
        self._show_info("收藏成功" if favorite else "已取消收藏", "")

    def _sync_favorite_button(self) -> None:
        favorite = self._is_current_favorite()
        self.favorite_button.setText("已收藏" if favorite else "收藏题目")
        if self.detail_window is not None:
            self.detail_window.set_favorite(favorite)

    def _is_current_favorite(self) -> bool:
        return self.favorite_manager.get_question("python", self._build_question_id()) is not None

    def _build_question_id(self) -> str:
        return f"python_{self.question_bank.name}_{self.current_question.id}"

    def _question_title(self) -> str:
        try:
            description = ast.get_docstring(ast.parse(self.current_question.code), clean=False) or ""
        except SyntaxError:
            description = ""
        for line in description.splitlines():
            if line.strip().startswith(("题目:", "题目：")):
                return line.split(":", 1)[-1].split("：", 1)[-1].strip()
        return f"Python 编程题 {self.current_question.id}"

    def _build_favorite(self) -> FavoriteQuestion:
        return FavoriteQuestion(
            question_id=self._build_question_id(),
            bank_name=self.question_bank.name,
            bank_question_id=self.current_question.id,
            subject="python",
            question=self._question_title(),
            options={},
            answer=self.current_question.answer,
            explanation="",
            question_type="python_programming",
            payload={
                "code": self.current_question.code,
                "full_score": self.current_question.full_score,
                "grading_points": [asdict(point) for point in self.current_question.grading_points],
            },
        )

    def _build_wrong(self, result: PythonJudgeResult) -> WrongQuestion:
        path = self.workspace.question_file(self.question_bank.name, self.current_question.id)
        user_code = path.read_text(encoding="utf-8") if path.exists() else self.current_question.code
        return WrongQuestion(
            question_id=self._build_question_id(),
            question_num=self.current_question.id,
            bank_name=self.question_bank.name,
            bank_question_id=self.current_question.id,
            subject="python",
            question=self._question_title(),
            options={},
            answer=self.current_question.answer,
            explanation=result.message,
            question_type="python_programming",
            payload={
                "code": self.current_question.code,
                "user_code": user_code,
                "full_score": self.current_question.full_score,
                "grading_points": [asdict(point) for point in self.current_question.grading_points],
                "judge_result": asdict(result),
            },
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "judge_overlay"):
            self.judge_overlay.setGeometry(self.rect())

    def closeEvent(self, event) -> None:
        self._save_editor()
        if self.run_process.state() != QProcess.ProcessState.NotRunning:
            self.run_process.kill()
            self.run_process.waitForFinished(1000)
        if self.task_thread and self.task_thread.isRunning():
            self.task_thread.wait(1500)
        if self.study_session_id is not None:
            self.user_manager.finish_study_session(self.study_session_id)
            self.study_session_id = None
        super().closeEvent(event)
