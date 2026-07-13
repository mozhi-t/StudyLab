from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout
from qfluentwidgets import BodyLabel, MessageBoxBase, SubtitleLabel

from config.settings import SUBJECTS


class InvalidBankTimeDialog(MessageBoxBase):
    def __init__(self, invalid_times: list[dict[str, str]], parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("发现题库时间格式非法", self)
        self.viewLayout.addWidget(self.titleLabel)

        message = BodyLabel("以下题库的 create_time 不在时间格式处理器支持的范围内，请手动修改后再重新检查：", self)
        message.setWordWrap(True)
        self.viewLayout.addWidget(message)

        content = QVBoxLayout()
        content.setSpacing(6)
        for item in invalid_times:
            subject_text = SUBJECTS.get(item["subject"], item["subject"])
            label = BodyLabel(f"{subject_text} / {item['name']}", self)
            label.setWordWrap(True)
            content.addWidget(label)
        self.viewLayout.addLayout(content)
        self.yesButton.setText("确定")
        self.cancelButton.hide()
