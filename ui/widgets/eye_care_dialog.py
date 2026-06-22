from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout
from qfluentwidgets import BodyLabel, CaptionLabel, MessageBoxBase, SpinBox, SubtitleLabel, isDarkTheme


class EyeCareDialog(MessageBoxBase):
    """到点弹出的休息提醒框。

    yesButton = 稍后再提醒（5 分钟）→ exec() 返回 True
    cancelButton = 知道了，关闭     → exec() 返回 False
    """

    def __init__(self, show_hint: bool, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("刷题很久了", self)
        self.viewLayout.addWidget(self.titleLabel)

        body = BodyLabel("该看看远方，让眼睛休息一下啦～", self)
        body.setWordWrap(True)
        self.viewLayout.addWidget(body)

        if show_hint:
            hint_layout = QVBoxLayout()
            hint_layout.setContentsMargins(0, 6, 0, 0)
            hint = CaptionLabel("如不需要休息提醒请前往设置项更改", self)
            hint.setWordWrap(True)
            hint.setStyleSheet(f"color: {'rgba(255, 255, 255, 0.62)' if isDarkTheme() else '#7a7a7a'};")
            hint_layout.addWidget(hint)
            self.viewLayout.addLayout(hint_layout)

        self.yesButton.setText("稍后再提醒（5 分钟）")
        self.cancelButton.setText("知道了，关闭")
        self.widget.setMinimumWidth(360)


class CustomIntervalDialog(MessageBoxBase):
    """自定义提醒间隔输入框，1–240 分钟。exec() 返回 True 时用 .value 取值。"""

    def __init__(self, current: int = 20, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("自定义提醒间隔", self)
        self.viewLayout.addWidget(self.titleLabel)

        hint = BodyLabel("请输入提醒间隔（1–240 分钟）：", self)
        hint.setWordWrap(True)
        self.viewLayout.addWidget(hint)

        self.spin = SpinBox(self)
        self.spin.setRange(1, 240)
        self.spin.setValue(current)
        self.spin.setFixedWidth(160)
        self.viewLayout.addWidget(self.spin)

        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(320)

    @property
    def value(self) -> int:
        return self.spin.value()
