from __future__ import annotations

import ast
import builtins
import keyword
import re

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QPainter, QTextCharFormat, QTextCursor, QSyntaxHighlighter
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget
from qfluentwidgets import isDarkTheme


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules: list[tuple[re.Pattern, QTextCharFormat]] = []
        if isDarkTheme():
            colors = {
                "keyword": "#d58cff", "builtin": "#66b7ff", "number": "#7ee787",
                "comment": "#74b86a", "string": "#f2a57b", "definition": "#62d6d0",
            }
        else:
            colors = {
                "keyword": "#7a1fa2", "builtin": "#005fb8", "number": "#0645ad",
                "comment": "#2e7d32", "string": "#a31515", "definition": "#007c78",
            }
        self._add(r"\b(" + "|".join(keyword.kwlist) + r")\b", colors["keyword"], bold=True)
        builtins_pattern = r"\b(int|float|str|bool|list|dict|set|tuple|range|len|print|input|map|filter|sum|min|max|enumerate|zip)\b"
        self._add(builtins_pattern, colors["builtin"], bold=True)
        self._add(r"\b(?:0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+(?:\.\d+)?)\b", colors["number"], bold=True)
        self._add(r"#[^\n]*", colors["comment"])
        self._add(r"(?:\"[^\"\n]*\"|'[^'\n]*')", colors["string"])
        self._add(r"\b(def|class)\s+([A-Za-z_]\w*)", colors["definition"], bold=True)

    def _add(self, pattern: str, color: str, *, bold: bool = False) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.DemiBold)
        self.rules.append((re.compile(pattern), fmt))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class LineNumberArea(QWidget):
    def __init__(self, editor: "PythonCodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.paint_line_numbers(event)


class PythonCodeEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.line_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margin)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_margin()
        self._highlight_current_line()
        self.highlighter = PythonHighlighter(self.document())

        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self._insert_completion)

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin(self, _count: int = 0) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_area.scroll(0, dy)
        else:
            self.line_area.update(0, rect.y(), self.line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margin()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.line_area.setGeometry(QRect(rect.left(), rect.top(), self.line_number_area_width(), rect.height()))

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self.line_area)
        painter.fillRect(event.rect(), QColor("#252526" if isDarkTheme() else "#eef2f6"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#b8b8b8" if isDarkTheme() else "#56616f"))
                painter.drawText(0, top, self.line_area.width() - 6, self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    def _highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(70, 90, 120, 70) if isDarkTheme() else QColor("#e5f1fb"))
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def keyPressEvent(self, event: QKeyEvent) -> None:
        popup_visible = self.completer.popup().isVisible()
        if popup_visible and event.key() == Qt.Key.Key_Tab:
            self._insert_completion(self.completer.currentCompletion())
            return
        if popup_visible and event.key() == Qt.Key.Key_Escape:
            self.completer.popup().hide()
            return
        if event.key() == Qt.Key.Key_Backtab:
            self._change_indent(-1)
            return
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.completer.popup().hide()
            cursor = self.textCursor()
            line = cursor.block().text()
            indent = re.match(r"\s*", line).group(0)
            if line.rstrip().endswith(":"):
                indent += "    "
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return
        super().keyPressEvent(event)
        if event.text() and (event.text().isalnum() or event.text() == "_"):
            self._show_completions()

    def _change_indent(self, direction: int) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        if direction > 0:
            cursor.insertText("    ")
        else:
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 4)
            selected = cursor.selectedText()
            cursor.insertText(selected[4 - len(selected.lstrip(" ")):] if selected.strip() else "")
        cursor.endEditBlock()

    def _word_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()

    def _show_completions(self) -> None:
        prefix = self._word_under_cursor()
        if len(prefix) < 2:
            self.completer.popup().hide()
            return
        names = set(keyword.kwlist) | set(dir(builtins))
        source = self.toPlainText()
        try:
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Name):
                    names.add(node.id)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(node.name)
                    if hasattr(node, "args"):
                        names.update(arg.arg for arg in node.args.args)
        except SyntaxError:
            names.update(re.findall(r"\b[A-Za-z_]\w*\b", source))
        matches = sorted(name for name in names if name.lower().startswith(prefix.lower()) and name != prefix)
        if not matches:
            self.completer.popup().hide()
            return
        from PyQt6.QtCore import QStringListModel
        self.completer.setModel(QStringListModel(matches, self.completer))
        self.completer.setCompletionPrefix(prefix)
        rect = self.cursorRect()
        rect.setWidth(max(220, self.completer.popup().sizeHintForColumn(0) + 24))
        self.completer.complete(rect)

    def _insert_completion(self, completion: str) -> None:
        if not completion:
            return
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)
        self.completer.popup().hide()
