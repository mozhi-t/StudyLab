from __future__ import annotations

import json
from pathlib import Path

from config.settings import LAN_EXAM_DIR
from core.json_store import JsonStore


class LanExamStore:
    def exam_dir(self, exam_name: str) -> Path:
        path = LAN_EXAM_DIR / exam_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_paper(self, exam_name: str, paper: dict) -> Path:
        path = self.exam_dir(exam_name) / "paper.json"
        JsonStore(path, paper).save(paper)
        return path

    def save_inputs(self, exam_name: str, payload: dict) -> Path:
        path = self.exam_dir(exam_name) / f"{exam_name}_input.json"
        JsonStore(path, payload).save(payload)
        return path

    def save_result(self, exam_name: str, payload: dict) -> Path:
        path = self.exam_dir(exam_name) / "result.json"
        JsonStore(path, payload).save(payload)
        return path

    def load_inputs(self, exam_name: str) -> dict:
        path = self.exam_dir(exam_name) / f"{exam_name}_input.json"
        return JsonStore(path, {"subjects": {}}).load()
