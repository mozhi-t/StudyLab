from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import StrongBodyLabel, isDarkTheme

from ui.widgets.base import StyledCardWidget


class TerminalConsole(QPlainTextEdit):
    input_submitted = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.input_start = 0
        self.setUndoRedoEnabled(False)
        self.setStyleSheet(
            "QPlainTextEdit{font-family: Consolas; font-size: 14px; background: transparent; border: none;}"
        )

    def begin(self) -> None:
        self.clear()
        self.input_start = 0
        self.setReadOnly(False)
        self.setCurrentCharFormat(self._input_text_format())
        self.setFocus()

    def append_program_output(self, text: str) -> None:
        self._append_program_text(text, is_error=False)

    def append_program_error(self, text: str) -> None:
        self._append_program_text(text, is_error=True)

    def _append_program_text(self, text: str, is_error: bool) -> None:
        if not text:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text, self._error_text_format() if is_error else self._output_text_format())
        self.setTextCursor(cursor)
        self.input_start = cursor.position()
        if not self.isReadOnly():
            self.setCurrentCharFormat(self._input_text_format())
        self.ensureCursorVisible()

    def _input_text_format(self) -> QTextCharFormat:
        return self._text_format("#65c98b" if isDarkTheme() else "#006b3c")

    def _error_text_format(self) -> QTextCharFormat:
        return self._text_format("#ff6b6b" if isDarkTheme() else "#c42b1c")

    def _output_text_format(self) -> QTextCharFormat:
        return self._text_format("#f0f0f0" if isDarkTheme() else "#202020")

    def _text_format(self, color: str) -> QTextCharFormat:
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        return text_format

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
        self.setCurrentCharFormat(self._input_text_format())
        super().keyPressEvent(event)
        self.setCurrentCharFormat(self._input_text_format())


class PythonResultCard(StyledCardWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, radius=14, light_border_alpha=34)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        self.title = StrongBodyLabel("运行结果", self)
        title_font = self.title.font()
        title_font.setPixelSize(title_font.pixelSize() + 1)
        self.title.setFont(title_font)
        self.console = TerminalConsole(self)
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("点击“运行”后，程序输出和输入将在这里显示")
        self.console.setMaximumBlockCount(2000)
        layout.addWidget(self.title)
        layout.addWidget(self.console, 1)
