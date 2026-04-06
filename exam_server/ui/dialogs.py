from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CheckBox, LineEdit, MessageBoxBase, PasswordLineEdit, SingleDirectionScrollArea, SubtitleLabel

from .common import StyledCardWidget


class ExamMetadataDialog(MessageBoxBase):
    def __init__(self, exam: dict, parent=None):
        super().__init__(parent)
        self.widget.setMinimumWidth(380)
        self.titleLabel = SubtitleLabel("考试基础信息", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.scroll_area = SingleDirectionScrollArea(self, Qt.Orientation.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(380)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = QWidget(self.scroll_area)
        self.content_widget.setObjectName("examMetadataContent")
        content = QVBoxLayout(self.content_widget)
        content.setContentsMargins(0, 0, 4, 0)
        content.setSpacing(10)

        self.exam_id_edit = LineEdit(self)
        self.exam_name_edit = LineEdit(self)
        self.start_time_edit = LineEdit(self)
        self.end_time_edit = LineEdit(self)
        self.duration_edit = LineEdit(self)
        self.password_edit = PasswordLineEdit(self)
        self.score_checkbox = CheckBox("交卷后立即显示分数", self)
        self.answer_checkbox = CheckBox("交卷后显示正确答案和解析", self)
        self.reentry_checkbox = CheckBox("交卷后禁止重复进入考试", self)
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
        content.addWidget(self.reentry_checkbox)
        content.addStretch(1)

        self.scroll_area.setWidget(self.content_widget)
        self.scroll_area.enableTransparentBackground()
        self.content_widget.setStyleSheet("QWidget#examMetadataContent{background: transparent; border: none;}")
        self.viewLayout.addWidget(self.scroll_area)
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
        self.reentry_checkbox.setChecked(bool(exam.get("disallow_reentry_after_submit", 1)))

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
            "disallow_reentry_after_submit": 1 if self.reentry_checkbox.isChecked() else 0,
        }


class ExamScoresDialog(MessageBoxBase):
    def __init__(self, exam_name: str, records: list[dict], parent=None):
        super().__init__(parent)
        self.widget.setMinimumWidth(560)
        self.titleLabel = SubtitleLabel(f"{exam_name} - 已交卷分数", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.scroll_area = SingleDirectionScrollArea(self, Qt.Orientation.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(420)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = QWidget(self.scroll_area)
        self.content_widget.setObjectName("examScoresContent")
        content = QVBoxLayout(self.content_widget)
        content.setContentsMargins(0, 0, 4, 0)
        content.setSpacing(10)

        if records:
            for item in records:
                card = StyledCardWidget(self.content_widget)
                layout = QVBoxLayout(card)
                layout.setContentsMargins(14, 12, 14, 12)
                layout.setSpacing(4)
                layout.addWidget(BodyLabel(f"用户：{item.get('username') or '未命名用户'}", card))
                layout.addWidget(BodyLabel(f"分数：{item.get('score', 0)}", card))
                layout.addWidget(BodyLabel(f"设备：{item.get('device_name') or '未知设备'}", card))
                layout.addWidget(BodyLabel(f"识别ID：{item.get('client_id', '')}", card))
                layout.addWidget(BodyLabel(f"交卷时间：{item.get('submitted_at') or '未知'}", card))
                content.addWidget(card)
        else:
            content.addWidget(BodyLabel("当前还没有用户交卷。", self.content_widget))
        content.addStretch(1)

        self.scroll_area.setWidget(self.content_widget)
        self.scroll_area.enableTransparentBackground()
        self.content_widget.setStyleSheet("QWidget#examScoresContent{background: transparent; border: none;}")
        self.viewLayout.addWidget(self.scroll_area)
        self.yesButton.setText("关闭")
        self.cancelButton.hide()
