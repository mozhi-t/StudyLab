from __future__ import annotations

from qfluentwidgets import BodyLabel, MessageBoxBase, SpinBox, SubtitleLabel


class CustomLearningGoalDialog(MessageBoxBase):
    """自定义每日刷题目标输入框。"""

    def __init__(self, current: int = 50, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("自定义学习目标", self)
        self.viewLayout.addWidget(self.titleLabel)

        hint = BodyLabel("请输入每日计划完成的题目数量（1–10000 题）：", self)
        hint.setWordWrap(True)
        self.viewLayout.addWidget(hint)

        self.spin = SpinBox(self)
        self.spin.setRange(1, 10000)
        self.spin.setValue(current)
        self.spin.setSuffix(" 题")
        self.spin.setFixedWidth(160)
        self.viewLayout.addWidget(self.spin)

        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(340)

    @property
    def value(self) -> int:
        return self.spin.value()
