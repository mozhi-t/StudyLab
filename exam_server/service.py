from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from exam_server.store import ExamServerStore
from exam_server.utils import now_iso, random_client_id


class ExamRealtimeService:
    def __init__(self, store: ExamServerStore):
        self.store = store
        self.app = FastAPI()
        self.app.add_api_websocket_route("/ws", self.websocket_endpoint)
        self.app.on_event("startup")(self.on_startup)
        self.app.on_event("shutdown")(self.on_shutdown)
        self.active_clients: dict[str, WebSocket] = {}
        self.client_state: dict[str, dict] = {}
        self.enabled_exams: set[str] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.heartbeat_task: asyncio.Task | None = None

    async def on_startup(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def on_shutdown(self) -> None:
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.heartbeat_task

    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        client_id = ""
        try:
            while True:
                payload = await websocket.receive_json()
                message_type = payload.get("type")
                if message_type == "hello":
                    client_id = await self.handle_hello(websocket, payload)
                elif message_type == "auth_submit":
                    await self.handle_auth_submit(websocket, payload)
                elif message_type == "heartbeat_ack":
                    await self.handle_heartbeat_ack(payload)
                elif message_type == "disconnect":
                    await self.handle_disconnect(websocket, payload)
                    break
                elif message_type == "request_exam":
                    await self.handle_request_exam(websocket, payload)
                elif message_type == "submit_exam":
                    await self.handle_submit_exam(websocket, payload)
        except WebSocketDisconnect:
            await self.unregister_client(client_id)
        except Exception:
            await self.unregister_client(client_id)

    async def handle_hello(self, websocket: WebSocket, payload: dict) -> str:
        config = self.store.load_config()
        current_connections = self.store.load_connections().get("connections", [])
        if len(current_connections) >= int(config.get("max_clients", 30)):
            await websocket.send_json({"type": "hello_ack", "success": False, "message": "已达到最大连接数"})
            return ""
        client_id = random_client_id()
        auth_mode = int(config.get("auth_mode", 0))
        state = {
            "client_id": client_id,
            "device_name": payload.get("device_name", ""),
            "ip_address": payload.get("ip_address", ""),
            "username": "",
            "auth_state": "authenticated" if auth_mode == 0 else "pending",
            "connected_at": now_iso(),
            "last_heartbeat_at": now_iso(),
            "websocket_session_id": id(websocket),
        }
        self.active_clients[client_id] = websocket
        self.client_state[client_id] = state
        self.store.upsert_connection(state)
        response = {
            "type": "hello_ack",
            "success": True,
            "client_id": client_id,
            "auth_mode": auth_mode,
            "message": "连接成功",
        }
        if auth_mode == 0:
            response["enabled_exams"] = self.get_enabled_exam_summaries()
        await websocket.send_json(response)
        return client_id

    async def handle_auth_submit(self, websocket: WebSocket, payload: dict) -> None:
        client_id = payload.get("client_id", "")
        if client_id not in self.client_state:
            await websocket.send_json({"type": "auth_result", "success": False, "message": "连接已失效"})
            return
        config = self.store.load_config()
        auth_mode = int(config.get("auth_mode", 0))
        username = payload.get("username", "").strip()
        password = payload.get("password", "").strip()
        if auth_mode == 1:
            success = bool(username)
            message = "连接成功" if success else "用户名不能为空"
        elif auth_mode == 2:
            accounts = self.store.load_accounts().get("accounts", [])
            success = any(item.get("username") == username and item.get("password") == password for item in accounts)
            message = "连接成功" if success else "密码错误"
        else:
            success = True
            message = "连接成功"
        if success:
            self.client_state[client_id]["username"] = username
            self.client_state[client_id]["auth_state"] = "authenticated"
            self.client_state[client_id]["last_heartbeat_at"] = now_iso()
            self.store.upsert_connection(self.client_state[client_id])
        await websocket.send_json(
            {
                "type": "auth_result",
                "success": success,
                "message": message,
                "enabled_exams": self.get_enabled_exam_summaries() if success else [],
            }
        )

    async def handle_heartbeat_ack(self, payload: dict) -> None:
        client_id = payload.get("client_id", "")
        if client_id in self.client_state:
            self.client_state[client_id]["last_heartbeat_at"] = now_iso()
            self.store.upsert_connection(self.client_state[client_id])

    async def handle_disconnect(self, websocket: WebSocket, payload: dict) -> None:
        await websocket.send_json({"type": "disconnect_result", "success": True, "message": "断开成功"})
        await self.unregister_client(payload.get("client_id", ""))

    async def handle_request_exam(self, websocket: WebSocket, payload: dict) -> None:
        client_id = payload.get("client_id", "")
        exam_name = payload.get("exam_name", "")
        if client_id not in self.client_state:
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "连接已失效"})
            return
        if self.client_state[client_id].get("auth_state") != "authenticated":
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "尚未完成认证"})
            return
        if exam_name not in self.enabled_exams:
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "考试未启用"})
            return
        paper = self.store.load_exam_paper(exam_name)
        if int(paper.get("disallow_reentry_after_submit", 1)):
            records = self.store.exam_user_store(exam_name).load().get("records", [])
            submitted = next(
                (
                    item for item in records
                    if item.get("client_id") == client_id and item.get("submission_state") == "submitted"
                ),
                None,
            )
            if submitted:
                await websocket.send_json({"type": "exam_request_result", "success": False, "message": "该考试已交卷，禁止重复进入"})
                return
        if datetime.now() > datetime.fromisoformat(paper["end_time"]):
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "考试已结束"})
            return
        if paper.get("exam_password", "") and payload.get("exam_password", "") != paper.get("exam_password", ""):
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "考试密码错误"})
            return
        connection = self.client_state[client_id]
        self.store.upsert_exam_record(
            exam_name,
            {
                "client_id": client_id,
                "device_name": connection.get("device_name", ""),
                "ip_address": connection.get("ip_address", ""),
                "username": connection.get("username", ""),
                "joined_at": now_iso(),
                "submitted_at": None,
                "submission_state": "in_progress",
                "score": None,
                "score_visible": False,
                "answer_visible": False,
            },
        )
        serialized = json.dumps(paper, ensure_ascii=False)
        chunk_size = 8192
        for index in range(0, len(serialized), chunk_size):
            await websocket.send_json({"type": "exam_paper_chunk", "exam_name": exam_name, "chunk": serialized[index:index + chunk_size]})
        await websocket.send_json({"type": "exam_paper_done", "exam_name": exam_name})

    async def handle_submit_exam(self, websocket: WebSocket, payload: dict) -> None:
        client_id = payload.get("client_id", "")
        exam_name = payload.get("exam_name", "")
        result = self.store.score_exam(exam_name, payload)
        self.store.upsert_exam_record(
            exam_name,
            {
                "client_id": client_id,
                "submitted_at": result["submitted_at"],
                "submission_state": "submitted",
                "score": result["score"],
                "score_visible": bool(result["show_score_immediately"]),
                "answer_visible": bool(result["show_correct_answer"]),
            },
        )
        response = {
            "type": "submit_result",
            "success": True,
            "exam_name": exam_name,
            "message": "交卷成功",
            "show_score_immediately": result["show_score_immediately"],
            "show_correct_answer": result["show_correct_answer"],
        }
        if result["show_score_immediately"]:
            response["score"] = result["score"]
            response["total_score"] = result["total_score"]
        if result["show_correct_answer"]:
            response["details"] = result["details"]
        await websocket.send_json(response)

    async def unregister_client(self, client_id: str) -> None:
        if not client_id:
            return
        self.active_clients.pop(client_id, None)
        self.client_state.pop(client_id, None)
        self.store.remove_connection(client_id)

    def get_enabled_exam_summaries(self) -> list[dict]:
        exams = []
        for item in self.store.list_exams():
            if item["exam_name"] in self.enabled_exams:
                exams.append(
                    {
                        "exam_id": item["exam_id"],
                        "exam_name": item["exam_name"],
                        "start_time": item["start_time"],
                        "duration_minutes": item["duration_minutes"],
                        "has_password": 1 if item["exam_password"] else 0,
                        "show_score_immediately": item["show_score_immediately"],
                        "show_correct_answer": item["show_correct_answer"],
                    }
                )
        return exams

    def enable_exam(self, exam_name: str) -> tuple[bool, str]:
        try:
            paper = self.store.load_exam_paper(exam_name)
        except Exception:
            return False, "考试文件不存在"
        if datetime.now() > datetime.fromisoformat(paper["end_time"]):
            return False, "考试时间已过期"
        self.enabled_exams.add(exam_name)
        self.schedule(self.broadcast_enabled_exams())
        return True, "考试已启用"

    def toggle_exam(self, exam_name: str) -> tuple[bool, str, bool]:
        if exam_name in self.enabled_exams:
            self.disable_exam(exam_name)
            return True, "考试已结束", False
        success, message = self.enable_exam(exam_name)
        return success, message, success

    def disable_exam(self, exam_name: str) -> None:
        if exam_name in self.enabled_exams:
            self.enabled_exams.remove(exam_name)
            self.schedule(self.broadcast_enabled_exams())

    async def broadcast_enabled_exams(self) -> None:
        await self.broadcast({"type": "exam_enabled_update", "enabled_exams": self.get_enabled_exam_summaries()})

    async def broadcast(self, payload: dict) -> None:
        stale_clients = []
        for client_id, websocket in list(self.active_clients.items()):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale_clients.append(client_id)
        for client_id in stale_clients:
            await self.unregister_client(client_id)

    def schedule(self, awaitable: Awaitable | None) -> None:
        if awaitable and self.loop:
            asyncio.run_coroutine_threadsafe(awaitable, self.loop)

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(300)
            current = datetime.now()
            stale_clients = []
            for client_id, websocket in list(self.active_clients.items()):
                try:
                    await websocket.send_json({"type": "heartbeat", "message": "ping"})
                except Exception:
                    stale_clients.append(client_id)
                    continue
                state = self.client_state.get(client_id)
                if not state:
                    continue
                last = datetime.fromisoformat(state.get("last_heartbeat_at", now_iso()))
                if (current - last).total_seconds() > 30:
                    stale_clients.append(client_id)
            for client_id in stale_clients:
                await self.unregister_client(client_id)
