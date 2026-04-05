from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout
from qfluentwidgets import BodyLabel, CheckBox, LineEdit, MessageBoxBase, PasswordLineEdit, SubtitleLabel


class ExamMetadataDialog(MessageBoxBase):
    def __init__(self, exam: dict, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("考试基础信息", self)
        self.viewLayout.addWidget(self.titleLabel)

        content = QVBoxLayout()
        self.exam_id_edit = LineEdit(self)
        self.exam_name_edit = LineEdit(self)
        self.start_time_edit = LineEdit(self)
        self.end_time_edit = LineEdit(self)
        self.duration_edit = LineEdit(self)
        self.password_edit = PasswordLineEdit(self)
        self.score_checkbox = CheckBox("交卷后立即显示分数", self)
        self.answer_checkbox = CheckBox("交卷后显示正确答案和解析", self)
        for label, control in [
            ("考试 ID", self.exam_id_edit),
            ("考试名称", self.exam_name_edit),
            ("开始时间", self.start_time_edit),
            ("结束时间", self.end_time_edit),
            ("考试时长（分钟）", self.duration_edit),
            ("考试密码", self.password_edit),
        ]:
            content.addWidget(BodyLabel(label, self))
            content.addWidget(control)
        content.addWidget(self.score_checkbox)
        content.addWidget(self.answer_checkbox)
        self.viewLayout.addLayout(content)
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

        self.exam_id_edit.setText(str(exam.get("exam_id", "")))
        self.exam_name_edit.setText(str(exam.get("exam_name", "")))
        self.start_time_edit.setText(str(exam.get("start_time", "")))
        self.end_time_edit.setText(str(exam.get("end_time", "")))
        self.duration_edit.setText(str(exam.get("duration_minutes", "")))
        self.password_edit.setText(str(exam.get("exam_password", "")))
        self.score_checkbox.setChecked(bool(exam.get("show_score_immediately", 0)))
        self.answer_checkbox.setChecked(bool(exam.get("show_correct_answer", 0)))

    def metadata(self) -> dict:
        return {
            "exam_id": self.exam_id_edit.text().strip(),
            "exam_name": self.exam_name_edit.text().strip(),
            "start_time": self.start_time_edit.text().strip(),
            "end_time": self.end_time_edit.text().strip(),
            "duration_minutes": int(self.duration_edit.text().strip() or 60),
            "exam_password": self.password_edit.text().strip(),
            "show_score_immediately": 1 if self.score_checkbox.isChecked() else 0,
            "show_correct_answer": 1 if self.answer_checkbox.isChecked() else 0,
        }
