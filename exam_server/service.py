from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from exam_server.logger import get_exam_logger, log_event
from exam_server.store import ExamServerStore
from exam_server.utils import now_iso, random_client_id


class ExamRealtimeService:
    def __init__(self, store: ExamServerStore):
        self.store = store
        self.logger = get_exam_logger()
        self.app = FastAPI()
        self.app.add_api_websocket_route("/ws", self.websocket_endpoint)
        self.app.on_event("startup")(self.on_startup)
        self.app.on_event("shutdown")(self.on_shutdown)
        self.active_clients: dict[str, WebSocket] = {}
        self.client_state: dict[str, dict] = {}
        self.enabled_exams: set[str] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.heartbeat_task: asyncio.Task | None = None
        self.record_writer_task: asyncio.Task | None = None
        self.exam_locks: dict[str, asyncio.Lock] = {}
        self.record_write_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.submitted_clients: dict[str, set[str]] = {}

    async def on_startup(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.record_writer_task = asyncio.create_task(self._record_writer_loop())
        log_event(self.logger, 20, "实时服务已启动")

    async def on_shutdown(self) -> None:
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.heartbeat_task
        if self.record_writer_task:
            self.record_writer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.record_writer_task
        log_event(self.logger, 20, "实时服务已停止")

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
            log_event(self.logger, 20, "客户端连接断开", 客户端ID=client_id or "未知")
            await self.unregister_client(client_id)
        except Exception:
            self.logger.exception("事件=WebSocket处理异常 客户端ID=%s", client_id or "未知")
            await self.unregister_client(client_id)

    async def handle_hello(self, websocket: WebSocket, payload: dict) -> str:
        config = self.store.load_config()
        current_connections = self.store.load_connections().get("connections", [])
        if len(current_connections) >= int(config.get("max_clients", 30)):
            log_event(
                self.logger,
                30,
                "客户端连接被拒绝",
                设备名称=payload.get("device_name", ""),
                IP地址=payload.get("ip_address", ""),
                原因="已达到最大连接数",
            )
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
        log_event(
            self.logger,
            20,
            "客户端已连接",
            客户端ID=client_id,
            设备名称=state["device_name"],
            IP地址=state["ip_address"],
            认证模式=auth_mode,
        )
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
            log_event(self.logger, 20, "认证成功", 客户端ID=client_id, 用户名=username, 认证模式=auth_mode)
        else:
            log_event(self.logger, 30, "认证失败", 客户端ID=client_id, 用户名=username, 认证模式=auth_mode, 原因=message)
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
        log_event(self.logger, 20, "收到断开请求", 客户端ID=payload.get("client_id", ""), 用户名=payload.get("username", ""))
        await websocket.send_json({"type": "disconnect_result", "success": True, "message": "断开成功"})
        await self.unregister_client(payload.get("client_id", ""))

    async def handle_request_exam(self, websocket: WebSocket, payload: dict) -> None:
        client_id = payload.get("client_id", "")
        exam_name = payload.get("exam_name", "")
        if client_id not in self.client_state:
            log_event(self.logger, 30, "获取试卷失败", 客户端ID=client_id, 考试名称=exam_name, 原因="连接已失效")
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "连接已失效"})
            return
        if self.client_state[client_id].get("auth_state") != "authenticated":
            log_event(self.logger, 30, "获取试卷失败", 客户端ID=client_id, 考试名称=exam_name, 原因="尚未完成认证")
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "尚未完成认证"})
            return
        if exam_name not in self.enabled_exams:
            log_event(self.logger, 30, "获取试卷失败", 客户端ID=client_id, 考试名称=exam_name, 原因="考试未启用")
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "考试未启用"})
            return
        paper = self.store.load_exam_paper(exam_name)
        if int(paper.get("disallow_reentry_after_submit", 1)):
            if client_id in self.submitted_clients.get(exam_name, set()):
                log_event(self.logger, 30, "获取试卷失败", 客户端ID=client_id, 考试名称=exam_name, 原因="已交卷且禁止重复进入")
                await websocket.send_json({"type": "exam_request_result", "success": False, "message": "该考试已交卷，禁止重复进入"})
                return
            records = self.store.exam_user_store(exam_name).load().get("records", [])
            submitted = next(
                (
                    item for item in records
                    if item.get("client_id") == client_id and item.get("submission_state") == "submitted"
                ),
                None,
            )
            if submitted:
                log_event(self.logger, 30, "获取试卷失败", 客户端ID=client_id, 考试名称=exam_name, 原因="已交卷且禁止重复进入")
                await websocket.send_json({"type": "exam_request_result", "success": False, "message": "该考试已交卷，禁止重复进入"})
                return
        if datetime.now() > datetime.fromisoformat(paper["end_time"]):
            log_event(self.logger, 30, "获取试卷失败", 客户端ID=client_id, 考试名称=exam_name, 原因="考试已结束")
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "考试已结束"})
            return
        if paper.get("exam_password", "") and payload.get("exam_password", "") != paper.get("exam_password", ""):
            log_event(self.logger, 30, "获取试卷失败", 客户端ID=client_id, 考试名称=exam_name, 原因="考试密码错误")
            await websocket.send_json({"type": "exam_request_result", "success": False, "message": "考试密码错误"})
            return
        connection = self.client_state[client_id]
        await self._write_exam_record(
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
        log_event(self.logger, 20, "开始下发试卷", 客户端ID=client_id, 考试名称=exam_name, 数据大小=len(serialized))
        for index in range(0, len(serialized), chunk_size):
            await websocket.send_json({"type": "exam_paper_chunk", "exam_name": exam_name, "chunk": serialized[index:index + chunk_size]})
        await websocket.send_json({"type": "exam_paper_done", "exam_name": exam_name})
        log_event(self.logger, 20, "试卷下发完成", 客户端ID=client_id, 考试名称=exam_name)

    async def handle_submit_exam(self, websocket: WebSocket, payload: dict) -> None:
        client_id = payload.get("client_id", "")
        exam_name = payload.get("exam_name", "")
        log_event(self.logger, 20, "收到交卷请求", 客户端ID=client_id, 考试名称=exam_name)
        result = await asyncio.to_thread(self.store.score_exam, exam_name, payload)
        self.submitted_clients.setdefault(exam_name, set()).add(client_id)
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
        log_event(
            self.logger,
            20,
            "交卷结果已返回",
            客户端ID=client_id,
            考试名称=exam_name,
            分数=result["score"],
            显示分数=result["show_score_immediately"],
            显示答案=result["show_correct_answer"],
        )
        connection = self.client_state.get(client_id, {})
        await self.record_write_queue.put(
            {
                "exam_name": exam_name,
                "record": {
                    "client_id": client_id,
                    "device_name": connection.get("device_name", payload.get("device_name", "")),
                    "ip_address": connection.get("ip_address", payload.get("ip_address", "")),
                    "username": connection.get("username", payload.get("username", "")),
                    "submitted_at": result["submitted_at"],
                    "submission_state": "submitted",
                    "score": result["score"],
                    "score_visible": bool(result["show_score_immediately"]),
                    "answer_visible": bool(result["show_correct_answer"]),
                },
                "submission_payload": payload,
                "username": connection.get("username", payload.get("username", "")),
                "client_id": client_id,
                "device_name": connection.get("device_name", payload.get("device_name", "")),
            }
        )
        log_event(self.logger, 20, "交卷写盘任务已入队", 客户端ID=client_id, 考试名称=exam_name, 队列长度=self.record_write_queue.qsize())

    async def unregister_client(self, client_id: str) -> None:
        if not client_id:
            return
        self.active_clients.pop(client_id, None)
        self.client_state.pop(client_id, None)
        self.store.remove_connection(client_id)
        log_event(self.logger, 20, "客户端已移除", 客户端ID=client_id)

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
            self.logger.exception("事件=启用考试失败 考试名称=%s 原因=考试文件读取失败", exam_name)
            return False, "考试文件不存在"
        if datetime.now() > datetime.fromisoformat(paper["end_time"]):
            log_event(self.logger, 30, "启用考试失败", 考试名称=exam_name, 原因="考试时间已过期")
            return False, "考试时间已过期"
        self.enabled_exams.add(exam_name)
        self.schedule(self.broadcast_enabled_exams())
        log_event(self.logger, 20, "考试已启用", 考试名称=exam_name)
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
            log_event(self.logger, 20, "考试已结束", 考试名称=exam_name)

    async def broadcast_enabled_exams(self) -> None:
        log_event(self.logger, 20, "已启用考试列表已广播", 已启用数量=len(self.enabled_exams))
        await self.broadcast({"type": "exam_enabled_update", "enabled_exams": self.get_enabled_exam_summaries()})

    async def broadcast(self, payload: dict) -> None:
        stale_clients = []
        for client_id, websocket in list(self.active_clients.items()):
            try:
                await websocket.send_json(payload)
            except Exception:
                log_event(self.logger, 30, "广播失败", 客户端ID=client_id)
                stale_clients.append(client_id)
        for client_id in stale_clients:
            await self.unregister_client(client_id)

    def schedule(self, awaitable: Awaitable | None) -> None:
        if awaitable and self.loop:
            asyncio.run_coroutine_threadsafe(awaitable, self.loop)

    def _exam_lock(self, exam_name: str) -> asyncio.Lock:
        if exam_name not in self.exam_locks:
            self.exam_locks[exam_name] = asyncio.Lock()
        return self.exam_locks[exam_name]

    async def _write_exam_record(self, exam_name: str, record: dict) -> None:
        async with self._exam_lock(exam_name):
            await asyncio.to_thread(self.store.upsert_exam_record, exam_name, record)
            log_event(self.logger, 20, "考试记录已写入", 考试名称=exam_name, 客户端ID=record.get("client_id", ""), 状态=record.get("submission_state", ""))

    async def _persist_submission(self, item: dict) -> None:
        exam_name = item["exam_name"]
        async with self._exam_lock(exam_name):
            await asyncio.to_thread(self.store.upsert_exam_record, exam_name, item["record"])
            submission_path = await asyncio.to_thread(
                self.store.save_submission_payload,
                exam_name,
                item["submission_payload"],
                item["username"],
                item["client_id"],
                item["device_name"],
            )
            log_event(self.logger, 20, "交卷数据已落盘", 考试名称=exam_name, 客户端ID=item["client_id"], 路径=submission_path)

    async def _record_writer_loop(self) -> None:
        while True:
            item = await self.record_write_queue.get()
            try:
                await self._persist_submission(item)
            except Exception:
                self.logger.exception("事件=后台交卷写盘失败 考试名称=%s 客户端ID=%s", item.get("exam_name", ""), item.get("client_id", ""))
            finally:
                self.record_write_queue.task_done()

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(300)
            current = datetime.now()
            stale_clients = []
            for client_id, websocket in list(self.active_clients.items()):
                try:
                    await websocket.send_json({"type": "heartbeat", "message": "ping"})
                except Exception:
                    log_event(self.logger, 30, "心跳发送失败", 客户端ID=client_id)
                    stale_clients.append(client_id)
                    continue
                state = self.client_state.get(client_id)
                if not state:
                    continue
                last = datetime.fromisoformat(state.get("last_heartbeat_at", now_iso()))
                if (current - last).total_seconds() > 30:
                    log_event(self.logger, 30, "心跳超时", 客户端ID=client_id)
                    stale_clients.append(client_id)
            for client_id in stale_clients:
                await self.unregister_client(client_id)
