from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, InfoBar, InfoBarPosition, MSFluentWindow

from exam_server.dialogs import ExamMetadataDialog
from exam_server.server_runtime import ServerThread
from exam_server.service import ExamRealtimeService
from exam_server.store import ExamServerStore
from exam_server.ui_pages import ServerExamListPage, ServerHomePage, ServerSettingsPage
from exam_server.utils import get_local_ip


class ExamServerWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        self.store = ExamServerStore()
        self.service = ExamRealtimeService(self.store)
        self.server_thread: ServerThread | None = None
        self.host_ip = get_local_ip()

        self.setWindowTitle("Study Lab - 考试服务端")
        self.resize(1100, 720)

        self.home_page = ServerHomePage(self)
        self.exam_list_page = ServerExamListPage(self)
        self.settings_page = ServerSettingsPage(self.host_ip, self)
        self.home_page.setObjectName("server_home_page")
        self.exam_list_page.setObjectName("server_exam_list_page")
        self.settings_page.setObjectName("server_settings_page")

        self.addSubInterface(self.home_page, FluentIcon.HOME, "主页")
        self.addSubInterface(self.exam_list_page, FluentIcon.LIBRARY, "考试列表")
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置")

        self.home_page.service_toggle_requested.connect(self.toggle_server)
        self.exam_list_page.enable_exam_requested.connect(self.enable_exam)
        self.exam_list_page.edit_exam_requested.connect(self.edit_exam)
        self.exam_list_page.delete_exam_requested.connect(self.delete_exam)
        self.settings_page.settings_changed.connect(self.save_settings)

        self.refresh_pages()
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.refresh_connections)
        self.connection_timer.start(3000)

    def refresh_pages(self) -> None:
        config = self.store.load_config()
        self.settings_page.set_settings(config)
        self.home_page.set_service_state(f"{self.host_ip}:{config.get('listen_port', 8765)}", self._is_server_running())
        exams = []
        for item in self.store.list_exams():
            exams.append(item | {"enabled": item["exam_name"] in self.service.enabled_exams})
        self.exam_list_page.set_exams(exams)
        self.refresh_connections()

    def refresh_connections(self) -> None:
        self.home_page.update_connections(self.store.load_connections().get("connections", []))

    def save_settings(self, payload: dict) -> None:
        self.store.save_config(payload)
        self.refresh_pages()

    def toggle_server(self) -> None:
        if self._is_server_running():
            self.stop_server()
            return
        port = int(self.store.load_config().get("listen_port", 8765))
        self.start_server(port)

    def start_server(self, port: int) -> None:
        self.server_thread = ServerThread(self.service, "0.0.0.0", port)
        self.server_thread.started_ok.connect(lambda: self._on_server_started(port))
        self.server_thread.failed.connect(lambda text: self.show_message("服务启动失败", text, self.home_page, error=True))
        self.server_thread.stopped.connect(self._on_server_stopped)
        self.server_thread.start()

    def stop_server(self) -> None:
        if self.server_thread:
            self.server_thread.stop()

    def _on_server_started(self, port: int) -> None:
        self.home_page.set_service_state(f"{self.host_ip}:{port}", True)
        self.show_message("服务启动中", f"监听地址：{self.host_ip}:{port}", self.home_page)

    def _on_server_stopped(self) -> None:
        self.server_thread = None
        config = self.store.load_config()
        self.home_page.set_service_state(f"{self.host_ip}:{config.get('listen_port', 8765)}", False)
        self.show_message("服务已停止", "已停止对外提供考试服务", self.home_page)

    def _is_server_running(self) -> bool:
        return bool(self.server_thread and self.server_thread.isRunning())

    def enable_exam(self, exam_name: str) -> None:
        success, message, enabled = self.service.toggle_exam(exam_name)
        self.refresh_pages()
        self.show_message("启用考试" if enabled else "结束考试", message, self.exam_list_page, error=not success)

    def edit_exam(self, exam_name: str) -> None:
        exam = next((item for item in self.store.list_exams() if item["exam_name"] == exam_name), None)
        if not exam:
            self.show_message("未找到考试", exam_name, self.exam_list_page, error=True)
            return
        dialog = ExamMetadataDialog(exam, self)
        if dialog.exec():
            self.store.save_exam_metadata(exam_name, dialog.metadata())
            self.refresh_pages()
            self.show_message("考试已更新", dialog.metadata()["exam_name"], self.exam_list_page)

    def delete_exam(self, exam_name: str) -> None:
        self.service.disable_exam(exam_name)
        self.store.delete_exam(exam_name)
        self.refresh_pages()
        self.show_message("考试已删除", exam_name, self.exam_list_page)

    def show_message(self, title: str, content: str, parent: QWidget, error: bool = False) -> None:
        if error:
            InfoBar.error(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=parent)
        else:
            InfoBar.success(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=parent)
