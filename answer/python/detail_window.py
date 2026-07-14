from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, PrimaryPushButton, PushButton, SingleDirectionScrollArea, StrongBodyLabel

from core.python.workspace import PROGRAM_MARKER, fill_template
from models.python.grading import JudgeDetail, PythonJudgeResult
from models.python.question import ExecutionPoint, PythonQuestion, SYNTAX_CHECK_NAME, TemplateIntegrityPoint
from ui.widgets.base import StyledCardWidget


class PythonStandardAnswerDialog(QDialog):
    def __init__(self, question: PythonQuestion, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"第 {question.id} 题 - 标准答案")
        self.resize(760, 560)
        self.setMinimumSize(620, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)
        root.addWidget(StrongBodyLabel(f"第 {question.id} 题　标准答案", self))

        answer_card = StyledCardWidget(self, radius=14, light_border_alpha=34)
        answer_layout = QVBoxLayout(answer_card)
        answer_layout.setContentsMargins(14, 12, 14, 12)
        self.answer_view = QPlainTextEdit(answer_card)
        self.answer_view.setReadOnly(True)
        self.answer_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        source = fill_template(question.code, question.answer)
        self.answer_view.setPlainText(source)
        self.answer_view.setStyleSheet(
            "QPlainTextEdit{font-family: Consolas; font-size: 13px; background: transparent; border: none;}"
        )
        self._highlight_answer(source, question.answer.strip("\r\n"))
        answer_layout.addWidget(self.answer_view)
        root.addWidget(answer_card, 1)

    def _highlight_answer(self, source: str, answer: str) -> None:
        if not answer:
            return
        answer_start = source.index(PROGRAM_MARKER) + len(PROGRAM_MARKER) + 1
        cursor = QTextCursor(self.answer_view.document())
        cursor.setPosition(answer_start)
        cursor.setPosition(answer_start + len(answer), QTextCursor.MoveMode.KeepAnchor)
        answer_format = QTextCharFormat()
        answer_format.setForeground(QColor(18, 148, 78))
        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format = answer_format
        self.answer_view.setExtraSelections([selection])


class JudgePointRow(BodyLabel):
    COLORS = {
        "pending": "rgb(128, 128, 128)",
        "checking": "rgb(225, 145, 20)",
        "passed": "rgb(18, 148, 78)",
        "failed": "rgb(210, 55, 55)",
    }
    ICONS = {"pending": "○", "checking": "●", "passed": "✓", "failed": "✕"}

    def __init__(self, point_id: str, name: str, indent: int = 0, parent: QWidget | None = None):
        super().__init__(parent)
        self.point_id = point_id
        self.name = name
        self.indent = indent
        self.setWordWrap(True)
        self.set_status("pending")

    def set_status(self, status: str, detail: JudgeDetail | None = None, message: str = "") -> None:
        suffix = "未检查"
        if status == "checking":
            suffix = "正在检查..."
        elif detail is not None:
            suffix = f"{detail.earned:g}/{detail.possible:g}"
            if detail.message:
                suffix += f"　{detail.message}"
        elif message:
            suffix = message
        self.setText(f"{self.ICONS[status]}  {self.name}　{suffix}")
        self.setStyleSheet(
            f"color: {self.COLORS[status]}; font-weight: 600; padding-left: {self.indent}px;"
        )


class PythonJudgeDetailWindow(QWidget):
    window_closed = pyqtSignal()
    favorite_requested = pyqtSignal()

    def __init__(self, question: PythonQuestion, source: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.question = question
        self.result: PythonJudgeResult | None = None
        self.current_point = 0
        self.setWindowTitle(f"第 {question.id} 题 - 判分详情")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(920, 700)
        self.setMinimumSize(760, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)
        title_row = QHBoxLayout()
        self.favorite_button = PushButton("收藏题目", self)
        self.favorite_button.clicked.connect(self.favorite_requested)
        self.title = StrongBodyLabel(f"第 {question.id} 题　判分详情", self)
        title_row.addWidget(self.title, 1)
        title_row.addWidget(self.favorite_button)
        root.addLayout(title_row)

        result_row = QHBoxLayout()
        self.subtitle = BodyLabel("准备检查...", self)
        self.answer_button = PrimaryPushButton("查看答案", self)
        self.answer_button.clicked.connect(self.show_standard_answer)
        result_row.addWidget(self.subtitle, 1)
        result_row.addWidget(self.answer_button)
        root.addLayout(result_row)

        self.code_card = StyledCardWidget(self, radius=14, light_border_alpha=34)
        code_layout = QVBoxLayout(self.code_card)
        code_layout.setContentsMargins(14, 12, 14, 12)
        code_layout.addWidget(StrongBodyLabel("用户代码", self.code_card))
        self.code_view = QPlainTextEdit(self.code_card)
        self.code_view.setReadOnly(True)
        self.code_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code_view.setPlainText(source)
        self.code_view.setStyleSheet("QPlainTextEdit{font-family: Consolas; background: transparent; border: none;}")
        code_layout.addWidget(self.code_view, 1)
        root.addWidget(self.code_card, 3)

        self.points_card = StyledCardWidget(self, radius=14, light_border_alpha=34)
        points_layout = QVBoxLayout(self.points_card)
        points_layout.setContentsMargins(14, 12, 14, 12)
        points_layout.addWidget(StrongBodyLabel("判分点", self.points_card))
        scroll = SingleDirectionScrollArea(self.points_card, Qt.Orientation.Vertical)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.enableTransparentBackground()
        content = QWidget(scroll)
        content.setStyleSheet("background: transparent;")
        point_list = QVBoxLayout(content)
        point_list.setContentsMargins(0, 0, 0, 0)
        point_list.setSpacing(8)
        self.point_rows: list[JudgePointRow] = []
        self.syntax_group_row: JudgePointRow | None = None
        self.syntax_child_ids: list[str] = []
        for point in question.grading_points:
            is_syntax_child = isinstance(point, (TemplateIntegrityPoint, ExecutionPoint))
            if is_syntax_child and self.syntax_group_row is None:
                self.syntax_group_row = JudgePointRow("syntax_check", SYNTAX_CHECK_NAME, parent=content)
                point_list.addWidget(self.syntax_group_row)
            if is_syntax_child:
                self.syntax_child_ids.append(point.id)
            row = JudgePointRow(point.id, point.name, 20 if is_syntax_child else 0, content)
            point_list.addWidget(row)
            self.point_rows.append(row)
        point_list.addStretch(1)
        scroll.setWidget(content)
        points_layout.addWidget(scroll, 1)
        root.addWidget(self.points_card, 2)
        self.begin_checking()

    def set_favorite(self, favorite: bool) -> None:
        self.favorite_button.setText("已收藏" if favorite else "收藏题目")

    def show_standard_answer(self) -> None:
        PythonStandardAnswerDialog(self.question, self).exec()

    def begin_checking(self) -> None:
        self.current_point = 0
        if self.syntax_group_row is not None:
            self.syntax_group_row.set_status("checking")
        for row in self.point_rows:
            row.set_status("pending")
        if self.point_rows:
            self.point_rows[0].set_status("checking")
            self.subtitle.setText(f"正在检查：{self.point_rows[0].name}")

    def set_result(self, result: PythonJudgeResult) -> None:
        self.result = result
        QTimer.singleShot(250, self._show_next_result)

    def _show_next_result(self) -> None:
        if self.result is None or self.current_point >= len(self.point_rows):
            self._finish_display()
            return
        row = self.point_rows[self.current_point]
        detail = next((item for item in self.result.details if item.point_id == row.point_id), None)
        if detail is None:
            if self.current_point == 0 and self.result.message:
                row.set_status("failed", message=self.result.message)
            else:
                row.set_status("pending")
            self._finish_display()
            return
        row.set_status("passed" if detail.passed else "failed", detail=detail)
        self.current_point += 1
        if self.syntax_child_ids and row.point_id == self.syntax_child_ids[-1]:
            self._update_syntax_group()
        if self.current_point < len(self.point_rows):
            next_row = self.point_rows[self.current_point]
            if any(item.point_id == next_row.point_id for item in self.result.details):
                next_row.set_status("checking")
                self.subtitle.setText(f"正在检查：{next_row.name}")
                QTimer.singleShot(350, self._show_next_result)
                return
        self._finish_display()

    def _update_syntax_group(self) -> None:
        if self.result is None or self.syntax_group_row is None:
            return
        child_details = [
            detail for detail in self.result.details if detail.point_id in self.syntax_child_ids
        ]
        if len(child_details) != len(self.syntax_child_ids):
            return
        detail = JudgeDetail(
            self.syntax_group_row.point_id,
            self.syntax_group_row.name,
            sum(item.earned for item in child_details),
            sum(item.possible for item in child_details),
            all(item.passed for item in child_details),
            "",
        )
        self.syntax_group_row.set_status("passed" if detail.passed else "failed", detail=detail)

    def _finish_display(self) -> None:
        if self.result is not None:
            self._update_syntax_group()
            self.subtitle.setText(f"成绩：{self.result.earned:g}/{self.result.possible:g}")

    def closeEvent(self, event) -> None:
        self.window_closed.emit()
        super().closeEvent(event)
