from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import InfoBar, InfoBarPosition

from config.settings import APP_SETTINGS_TEMPLATE
from core.json_store import JsonStore
from ui.widgets.eye_care_dialog import EyeCareDialog


class EyeCareReminder(QObject):
    """休息提醒控制器：拥有 QTimer，读取配置，到点触发提醒。

    生命周期由传入的 parent_window 托管（作为 QObject 子对象）。
    SettingsPage 修改配置后通过 eye_care_changed 信号触发 reload_config()。
    """

    REMINDER_TITLE = "刷题很久了"
    REMINDER_TEXT = "该看看远方，让眼睛休息一下啦～"
    HINT_TEXT = "如不需要休息提醒请前往设置项更改"
    SNOOZE_MINUTES = 5
    INFOBAR_DURATION_MS = 5000

    def __init__(self, parent_window, store: JsonStore):
        super().__init__(parent_window)
        self._window = parent_window
        self._store = store
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._enabled = True
        self._interval_minutes = 20
        self._mode = "dialog"
        self._reload()

    def reload_config(self) -> None:
        """配置变更后调用：重新读取并应用（立即生效，不等当前周期结束）。"""
        self._reload()

    def _reload(self) -> None:
        data = self._store.load()
        cfg = APP_SETTINGS_TEMPLATE["eye_care"] | data.get("eye_care", {})
        self._enabled = bool(cfg.get("enabled", True))
        self._interval_minutes = self._clamp_minutes(cfg.get("interval_minutes", 20))
        self._mode = cfg.get("reminder_mode", "dialog")
        self._timer.stop()
        if self._enabled:
            self._timer.start(self._interval_minutes * 60 * 1000)

    def _on_timeout(self) -> None:
        first_shown = self._read_first_shown()
        next_delay = self._interval_minutes
        parent = self._reminder_parent()

        if self._mode == "dialog":
            dialog = EyeCareDialog(show_hint=not first_shown, parent=parent)
            if dialog.exec():  # yesButton = 稍后再提醒
                next_delay = self.SNOOZE_MINUTES
        else:
            content = self.REMINDER_TEXT
            if not first_shown:
                content = f"{self.REMINDER_TEXT}\n{self.HINT_TEXT}"
            InfoBar.info(
                title=self.REMINDER_TITLE,
                content=content,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=self.INFOBAR_DURATION_MS,
                parent=parent,
            )

        if not first_shown:
            self._mark_first_shown()

        if self._enabled:  # 用户可能在弹窗期间关掉了开关
            self._timer.start(next_delay * 60 * 1000)

    def _reminder_parent(self) -> QWidget:
        answer_window = getattr(self._window, "answer_window", None)
        if answer_window and answer_window.isVisible():
            return answer_window
        stacked_widget = getattr(self._window, "stackedWidget", None)
        if stacked_widget:
            current_page = stacked_widget.currentWidget()
            if current_page:
                return current_page
        return self._window

    def _read_first_shown(self) -> bool:
        data = self._store.load()
        cfg = APP_SETTINGS_TEMPLATE["eye_care"] | data.get("eye_care", {})
        return bool(cfg.get("first_shown", False))

    def _mark_first_shown(self) -> None:
        data = self._store.load()
        data.setdefault("eye_care", {})
        data["eye_care"]["first_shown"] = True
        self._store.save(data)

    @staticmethod
    def _clamp_minutes(value) -> int:
        try:
            n = int(value)
        except (TypeError, ValueError):
            n = 20
        return max(1, min(n, 240))
