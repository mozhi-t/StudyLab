from __future__ import annotations

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

    def run(self) -> None:
        try:
            config = uvicorn.Config(self.service.app, host=self.host, port=self.port, log_level="warning")
            self.server = uvicorn.Server(config)
            self.started_ok.emit()
            self.server.run()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.stopped.emit()

    def stop(self) -> None:
        if self.server:
            self.server.should_exit = True
