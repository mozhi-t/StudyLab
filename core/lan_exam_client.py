from __future__ import annotations

import asyncio
import json
from queue import Queue

import websockets
from PyQt6.QtCore import QThread, pyqtSignal


class LanExamClientThread(QThread):
    connected = pyqtSignal()
    message_received = pyqtSignal(dict)
    connection_failed = pyqtSignal(str)
    disconnected = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.loop: asyncio.AbstractEventLoop | None = None
        self.websocket = None
        self._send_queue: Queue[dict] = Queue()
        self._running = True

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main())
        except Exception as exc:
            self.connection_failed.emit(str(exc))
        finally:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    async def _main(self) -> None:
        async with websockets.connect(self.url, max_size=None) as websocket:
            self.websocket = websocket
            self.connected.emit()
            sender = asyncio.create_task(self._sender())
            try:
                async for message in websocket:
                    payload = json.loads(message)
                    self.message_received.emit(payload)
            finally:
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)
                self.disconnected.emit("连接已断开")

    async def _sender(self) -> None:
        while self._running:
            if self._send_queue.empty():
                await asyncio.sleep(0.05)
                continue
            payload = self._send_queue.get()
            if self.websocket:
                await self.websocket.send(json.dumps(payload, ensure_ascii=False))

    def send_message(self, payload: dict) -> None:
        self._send_queue.put(payload)

    def close_connection(self) -> None:
        self._running = False
        self.send_message({"type": "disconnect"})
        if self.loop and self.websocket:
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
