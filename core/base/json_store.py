from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from core.base.errors import raise_app_error


class JsonStore:
    def __init__(self, path: Path, default_data, load_error: str = "E025", format_error: str = "E025", write_error: str = "E025"):
        self.path = path
        self.default_data = default_data
        self.load_error = load_error
        self.format_error = format_error
        self.write_error = write_error

    def ensure(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(self._default())

    def load(self):
        self.ensure()
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError as exc:
            raise_app_error(self.format_error, str(exc))
        except OSError as exc:
            raise_app_error(self.load_error, str(exc))

    def save(self, data) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise_app_error(self.write_error, str(exc))

    def _default(self):
        return deepcopy(self.default_data)
