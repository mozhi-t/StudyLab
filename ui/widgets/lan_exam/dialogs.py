from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout
from qfluentwidgets import BodyLabel, IndeterminateProgressRing, LineEdit, MessageBoxBase, PasswordLineEdit, SubtitleLabel


class LanExamAuthDialog(MessageBoxBase):
    def __init__(self, auth_mode: int, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("请输入用户名", self)
        self.viewLayout.addWidget(self.titleLabel)

        content = QVBoxLayout()
        self.username_edit = LineEdit(self)
        self.username_edit.setPlaceholderText("用户名")
        content.addWidget(self.username_edit)
        self.password_edit = None
        if auth_mode == 2:
            self.password_edit = PasswordLineEdit(self)
            self.password_edit.setPlaceholderText("密码")
            content.addWidget(self.password_edit)
        self.viewLayout.addLayout(content)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")

    def credentials(self) -> tuple[str, str]:
        return self.username_edit.text().strip(), self.password_edit.text().strip() if self.password_edit else ""


class ExamPasswordDialog(MessageBoxBase):
    def __init__(self, exam_name: str, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(f"{exam_name} 需要考试密码", self)
        self.viewLayout.addWidget(self.titleLabel)
        self.password_edit = PasswordLineEdit(self)
        self.password_edit.setPlaceholderText("请输入考试密码")
        self.viewLayout.addWidget(self.password_edit)
        self.yesButton.setText("进入考试")
        self.cancelButton.setText("取消")

    def password(self) -> str:
        return self.password_edit.text().strip()


class LoadingMessageDialog(MessageBoxBase):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)
        ring_layout = QVBoxLayout()
        ring_layout.addWidget(IndeterminateProgressRing(self), 0)
        ring_layout.addWidget(BodyLabel("请稍候...", self), 0)
        self.viewLayout.addLayout(ring_layout)
        self.yesButton.hide()
        self.cancelButton.hide()
