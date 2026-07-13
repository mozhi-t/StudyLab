from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, PrimaryPushButton, PushButton, StrongBodyLabel

from models.base import FavoriteQuestion, WrongQuestion
from ui.widgets.base import StyledCardWidget


class _PythonRecordDialog(QDialog):
    def __init__(self, title: str, source: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(920, 700)
        self.setMinimumSize(720, 520)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)
        self.title_label = StrongBodyLabel(title, self)
        root.addWidget(self.title_label)
        self.code_card = StyledCardWidget(self, radius=14, light_border_alpha=34)
        code_layout = QVBoxLayout(self.code_card)
        code_layout.setContentsMargins(14, 12, 14, 12)
        self.code_view = QPlainTextEdit(self.code_card)
        self.code_view.setReadOnly(True)
        self.code_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code_view.setPlainText(source)
        self.code_view.setStyleSheet("QPlainTextEdit{font-family: Consolas; background: transparent; border: none;}")
        code_layout.addWidget(self.code_view)
        root.addWidget(self.code_card, 1)
        self.button_row = QHBoxLayout()
        self.button_row.addStretch(1)
        root.addLayout(self.button_row)


class PythonFavoriteDetailDialog(_PythonRecordDialog):
    practice_requested = pyqtSignal()
    favorite_requested = pyqtSignal()

    def __init__(self, item: FavoriteQuestion, parent: QWidget | None = None):
        source = str(item.payload.get("code", ""))
        super().__init__(f"{item.bank_name} · 第 {item.bank_question_id} 题", source, parent)
        self.practice_button = PrimaryPushButton("练习该题", self)
        self.favorite_button = PushButton("已收藏", self)
        self.practice_button.clicked.connect(self._practice)
        self.favorite_button.clicked.connect(self.favorite_requested)
        self.button_row.addWidget(self.practice_button)
        self.button_row.addWidget(self.favorite_button)

    def set_favorite(self, favorite: bool) -> None:
        self.favorite_button.setText("已收藏" if favorite else "收藏题目")

    def _practice(self) -> None:
        self.accept()
        self.practice_requested.emit()

class PythonWrongDetailDialog(_PythonRecordDialog):
    practice_requested = pyqtSignal()
    favorite_requested = pyqtSignal()

    def __init__(self, item: WrongQuestion, parent: QWidget | None = None):
        payload = item.payload
        source = str(payload.get("user_code") or payload.get("code", ""))
        super().__init__(f"{item.bank_name} · 第 {item.bank_question_id} 题", source, parent)
        result = payload.get("judge_result", {})
        score = BodyLabel(
            f"最近成绩：{result.get('earned', 0):g}/{result.get('possible', payload.get('full_score', 20)):g}",
            self,
        )
        self.layout().insertWidget(self.layout().count() - 1, score)
        self.points_card = StyledCardWidget(self, radius=14, light_border_alpha=34)
        points_layout = QVBoxLayout(self.points_card)
        points_layout.setContentsMargins(14, 12, 14, 12)
        points_layout.addWidget(StrongBodyLabel("判分点", self.points_card))
        details = result.get("details", []) if isinstance(result, dict) else []
        if details:
            for detail in details:
                passed = bool(detail.get("passed"))
                label = BodyLabel(
                    f"{'✓' if passed else '✕'}  {detail.get('name', '')}　"
                    f"{detail.get('earned', 0):g}/{detail.get('possible', 0):g}　{detail.get('message', '')}",
                    self.points_card,
                )
                label.setWordWrap(True)
                label.setStyleSheet(
                    "color: rgb(18, 148, 78); font-weight: 600;" if passed
                    else "color: rgb(210, 55, 55); font-weight: 600;"
                )
                points_layout.addWidget(label)
        else:
            label = BodyLabel(str(result.get("message", item.explanation) if isinstance(result, dict) else item.explanation), self.points_card)
            label.setWordWrap(True)
            label.setStyleSheet("color: rgb(210, 55, 55); font-weight: 600;")
            points_layout.addWidget(label)
        self.layout().insertWidget(self.layout().count() - 1, self.points_card)
        self.practice_button = PrimaryPushButton("练习该题", self)
        self.favorite_button = PushButton("收藏题目", self)
        self.practice_button.clicked.connect(self._practice)
        self.favorite_button.clicked.connect(self.favorite_requested)
        self.button_row.addWidget(self.practice_button)
        self.button_row.addWidget(self.favorite_button)

    def set_favorite(self, favorite: bool) -> None:
        self.favorite_button.setText("已收藏" if favorite else "收藏题目")

    def _practice(self) -> None:
        self.accept()
        self.practice_requested.emit()
