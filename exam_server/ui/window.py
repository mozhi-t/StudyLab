from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, InfoBar, InfoBarPosition, MSFluentWindow

try:
    from .dialogs import ExamMetadataDialog, ExamScoresDialog
    from .pages import ServerExamListPage, ServerHomePage, ServerLogPage, ServerSettingsPage
    from ..core.logger import get_exam_logger, log_event
    from ..core.paths import LOG_DIR
    from ..core.utils import get_local_ip
    from ..network.server_runtime import ServerThread
    from ..network.service import ExamRealtimeService
    from ..network.store import ExamServerStore
except ImportError:
    from ui.dialogs import ExamMetadataDialog, ExamScoresDialog
    from ui.pages import ServerExamListPage, ServerHomePage, ServerLogPage, ServerSettingsPage
    from core.logger import get_exam_logger, log_event
    from core.paths import LOG_DIR
    from core.utils import get_local_ip
    from network.server_runtime import ServerThread
    from network.service import ExamRealtimeService
    from network.store import ExamServerStore


class ExamServerWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        self.logger = get_exam_logger()
        self.store = ExamServerStore()
        self.service = ExamRealtimeService(self.store)
        self.server_thread: ServerThread | None = None
        self.host_ip = get_local_ip()

        self.setWindowTitle("Study Lab - 考试服务端")
        self.resize(1100, 720)

        self.home_page = ServerHomePage(self)
        self.exam_list_page = ServerExamListPage(self)
        self.settings_page = ServerSettingsPage(self.host_ip, self)
        self.log_page = ServerLogPage(self)
        self.home_page.setObjectName("server_home_page")
        self.exam_list_page.setObjectName("server_exam_list_page")
        self.settings_page.setObjectName("server_settings_page")
        self.log_page.setObjectName("server_log_page")

        self.addSubInterface(self.home_page, FluentIcon.HOME, "主页")
        self.addSubInterface(self.exam_list_page, FluentIcon.LIBRARY, "考试列表")
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置")
        self.addSubInterface(self.log_page, FluentIcon.DOCUMENT, "日志")

        self.home_page.service_toggle_requested.connect(self.toggle_server)
        self.exam_list_page.enable_exam_requested.connect(self.enable_exam)
        self.exam_list_page.view_scores_requested.connect(self.view_scores)
        self.exam_list_page.edit_exam_requested.connect(self.edit_exam)
        self.exam_list_page.delete_exam_requested.connect(self.delete_exam)
        self.settings_page.settings_changed.connect(self.save_settings)
        self.log_page.refresh_requested.connect(self.refresh_logs)
        self.log_page.file_changed.connect(self.load_log_file)

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
        self.refresh_logs()

    def refresh_connections(self) -> None:
        self.home_page.update_connections(self.store.load_connections().get("connections", []))

    def save_settings(self, payload: dict) -> None:
        self.store.save_config(payload)
        log_event(
            self.logger,
            20,
            "设置已更新",
            服务端名称=payload.get("server_name", ""),
            最大连接数=payload.get("max_clients", ""),
            认证模式=payload.get("auth_mode", ""),
            监听端口=payload.get("listen_port", ""),
        )
        self.refresh_pages()

    def toggle_server(self) -> None:
        if self._is_server_running():
            self.stop_server()
            return
        port = int(self.store.load_config().get("listen_port", 8765))
        self.start_server(port)

    def start_server(self, port: int) -> None:
        log_event(self.logger, 20, "请求启动服务", 主机地址=self.host_ip, 端口=port)
        self.server_thread = ServerThread(self.service, "0.0.0.0", port)
        self.server_thread.started_ok.connect(lambda: self._on_server_started(port))
        self.server_thread.failed.connect(self._on_server_failed)
        self.server_thread.stopped.connect(self._on_server_stopped)
        self.server_thread.start()

    def stop_server(self) -> None:
        if self.server_thread:
            log_event(self.logger, 20, "请求停止服务")
            self.server_thread.stop()

    def _on_server_started(self, port: int) -> None:
        self.home_page.set_service_state(f"{self.host_ip}:{port}", True)
        log_event(self.logger, 20, "服务已启动", 主机地址=self.host_ip, 端口=port)
        self.refresh_logs()
        self.show_message("服务启动中", f"监听地址：{self.host_ip}:{port}", self.home_page)

    def _on_server_failed(self, text: str) -> None:
        log_event(self.logger, 40, "服务启动失败", 详情=text)
        self.refresh_logs()
        self.show_message("服务启动失败", text, self.home_page, error=True)

    def _on_server_stopped(self) -> None:
        self.server_thread = None
        config = self.store.load_config()
        self.home_page.set_service_state(f"{self.host_ip}:{config.get('listen_port', 8765)}", False)
        log_event(self.logger, 20, "服务已停止")
        self.refresh_logs()
        self.show_message("服务已停止", "已停止对外提供考试服务", self.home_page)

    def _is_server_running(self) -> bool:
        return bool(self.server_thread and self.server_thread.isRunning())

    def enable_exam(self, exam_name: str) -> None:
        success, message, enabled = self.service.toggle_exam(exam_name)
        log_event(self.logger, 20, "考试状态切换", 考试名称=exam_name, 已启用=enabled, 是否成功=success, 消息=message)
        self.refresh_logs()
        self.refresh_pages()
        self.show_message("启用考试" if enabled else "结束考试", message, self.exam_list_page, error=not success)

    def edit_exam(self, exam_name: str) -> None:
        exam = next((item for item in self.store.list_exams() if item["exam_name"] == exam_name), None)
        if not exam:
            self.show_message("未找到考试", exam_name, self.exam_list_page, error=True)
            return
        dialog = ExamMetadataDialog(exam, self)
        if dialog.exec():
            metadata = dialog.metadata()
            self.store.save_exam_metadata(exam_name, metadata)
            log_event(self.logger, 20, "考试设置已更新", 原考试名称=exam_name, 新考试名称=metadata.get("exam_name", ""))
            self.refresh_logs()
            self.refresh_pages()
            self.show_message("考试已更新", metadata["exam_name"], self.exam_list_page)

    def view_scores(self, exam_name: str) -> None:
        records = self.store.list_submitted_scores(exam_name)
        dialog = ExamScoresDialog(exam_name, records, self)
        dialog.exec()

    def delete_exam(self, exam_name: str) -> None:
        self.service.disable_exam(exam_name)
        self.store.delete_exam(exam_name)
        log_event(self.logger, 20, "考试已删除", 考试名称=exam_name)
        self.refresh_logs()
        self.refresh_pages()
        self.show_message("考试已删除", exam_name, self.exam_list_page)

    def refresh_logs(self) -> None:
        files = sorted((item.name for item in LOG_DIR.glob("exam_server_*.log")), reverse=True)
        current = self.log_page.current_file() if files else ""
        self.log_page.set_log_files(files, current=current)
        if files:
            target = current if current in files else files[0]
            self.load_log_file(target)
        else:
            self.log_page.set_log_content("暂无日志文件")

    def load_log_file(self, filename: str) -> None:
        path = LOG_DIR / filename
        if not path.exists():
            self.log_page.set_log_content("日志文件不存在")
            return
        self.log_page.set_log_content(path.read_text(encoding="utf-8"))

    def show_message(self, title: str, content: str, parent: QWidget, error: bool = False) -> None:
        if error:
            InfoBar.error(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=parent)
        else:
            InfoBar.success(title=title, content=content, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=parent)
