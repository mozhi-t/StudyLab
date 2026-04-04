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
    "E001": "用户数据文件加载失败",
    "E002": "用户数据文件格式错误",
    "E003": "题库索引文件加载失败",
    "E004": "题库索引文件格式错误",
    "E005": "题库索引刷新失败",
    "E006": "题库文件读取失败",
    "E007": "题库文件格式错误",
    "E008": "题库文件删除失败",
    "E009": "题库文件写入失败",
    "E010": "错题文件加载失败",
    "E011": "错题文件格式错误",
    "E012": "错题写入失败",
    "E013": "收藏文件加载失败",
    "E014": "收藏文件格式错误",
    "E015": "收藏写入失败",
    "E016": "取消收藏失败",
    "E017": "网络连接失败",
    "E018": "题库下载失败",
    "E019": "题库下载链接无效",
    "E020": "答题窗口创建失败",
    "E021": "题库数据加载失败",
    "E022": "答题状态保存失败",
    "E023": "页面跳转失败",
    "E024": "目标题库不存在",
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
