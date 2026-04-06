from __future__ import annotations

import threading
import time

import uvicorn
from PyQt6.QtCore import QThread, pyqtSignal

try:
    from .service import ExamRealtimeService
except ImportError:
    from network.service import ExamRealtimeService


class ServerThread(QThread):
    started_ok = pyqtSignal()
    failed = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self, service: ExamRealtimeService, host: str, port: int):
        super().__init__()
        self.service = service
        self.host = host
        self.port = port
        self.server: uvicorn.Server | None = None
        self._started_emitted = False

    def run(self) -> None:
        try:
            config = uvicorn.Config(self.service.app, host=self.host, port=self.port, log_level="warning", log_config=None)
            self.server = uvicorn.Server(config)
            threading.Thread(target=self._watch_started, daemon=True).start()
            self.server.run()
            if not self._started_emitted and not self.server.should_exit:
                self.failed.emit("服务启动失败，请检查端口是否被占用或权限是否受限")
        except BaseException as exc:
            if isinstance(exc, SystemExit):
                message = "服务启动失败，请检查端口是否被占用或权限是否受限"
            else:
                message = str(exc) or "服务启动失败"
            self.failed.emit(message)
        finally:
            self.stopped.emit()

    def stop(self) -> None:
        if self.server:
            self.server.should_exit = True

    def _watch_started(self) -> None:
        while self.server and not self.server.should_exit:
            if getattr(self.server, "started", False):
                if not self._started_emitted:
                    self._started_emitted = True
                    self.started_ok.emit()
                return
            time.sleep(0.05)
