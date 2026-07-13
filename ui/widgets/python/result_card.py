from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import StrongBodyLabel

from ui.widgets.styled_card import StyledCardWidget


class TerminalConsole(QPlainTextEdit):
    input_submitted = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.input_start = 0
        self.setUndoRedoEnabled(False)
        self.setStyleSheet(
            "QPlainTextEdit{font-family: Consolas; font-size: 13px; background: transparent; border: none;}"
        )

    def begin(self) -> None:
        self.clear()
        self.input_start = 0
        self.setReadOnly(False)
        self.setFocus()

    def append_program_output(self, text: str) -> None:
        if not text:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self.input_start = cursor.position()
        self.ensureCursorVisible()

    def finish(self) -> None:
        self.setReadOnly(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.isReadOnly():
            return super().keyPressEvent(event)
        cursor = self.textCursor()
        if cursor.position() < self.input_start:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Left) and self.textCursor().position() <= self.input_start:
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.setPosition(self.input_start, QTextCursor.MoveMode.KeepAnchor)
            value = cursor.selectedText().replace("\u2029", "\n")
            end_cursor = self.textCursor()
            end_cursor.movePosition(QTextCursor.MoveOperation.End)
            end_cursor.insertText("\n")
            self.setTextCursor(end_cursor)
            self.input_start = end_cursor.position()
            self.input_submitted.emit(value + "\n")
            return
        super().keyPressEvent(event)


class PythonResultCard(StyledCardWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, radius=14, light_border_alpha=34)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        self.title = StrongBodyLabel("运行结果", self)
        self.console = TerminalConsole(self)
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("点击“运行”后，程序输出和输入将在这里显示")
        self.console.setMaximumBlockCount(2000)
        layout.addWidget(self.title)
        layout.addWidget(self.console, 1)
