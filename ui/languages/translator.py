from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QLocale


class LanguageManager:
    """Load UI translations from one JSON file per language."""

    SUPPORTED_LANGUAGES = ("zh_CN", "en_US")
    LANGUAGE_DIR = Path(__file__).resolve().parent

    def __init__(self, language: str = "system"):
        self.language = "zh_CN"
        self._texts: dict[str, str] = {}
        self.set_language(language)

    def set_language(self, language: str) -> None:
        resolved = self.resolve_language(language)
        path = self.LANGUAGE_DIR / f"{resolved}.json"
        with path.open("r", encoding="utf-8") as file:
            self._texts = json.load(file)
        self.language = resolved

    def text(self, key: str, default: str | None = None, **kwargs) -> str:
        value = self._texts.get(key, default if default is not None else key)
        return value.format(**kwargs) if kwargs else value

    @classmethod
    def resolve_language(cls, language: str) -> str:
        if language in cls.SUPPORTED_LANGUAGES:
            return language
        system_language = QLocale.system().language()
        return "en_US" if system_language == QLocale.Language.English else "zh_CN"
