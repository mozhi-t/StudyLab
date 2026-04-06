from __future__ import annotations

import sys
import traceback

from PyQt6.QtWidgets import QMessageBox


class AppError(Exception):
    def __init__(self, code: str, message: str, detail: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or ""


ERROR_MESSAGES = {
    "E025": "未知错误",
}


def raise_app_error(code: str, detail: str | None = None) -> None:
    raise AppError(code, ERROR_MESSAGES.get(code, "未知错误"), detail)


def install_exception_hook() -> None:
    def exception_handler(exc_type, exc_value, exc_tb):
        if isinstance(exc_value, AppError):
            detail = exc_value.detail or str(exc_value)
            text = f"错误码: {exc_value.code}\n说明: {exc_value.message}\n详情: {detail}"
        else:
            trace = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            text = f"错误码: E025\n说明: 未知错误\n详情: {trace}"
        QMessageBox.critical(None, "程序错误", text)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = exception_handler
