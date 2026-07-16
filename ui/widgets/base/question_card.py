from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, CheckBox, FluentIcon, PushButton, StrongBodyLabel

from config.settings import SUBJECTS


class QuestionSelectionCard(CardWidget):
    """Standalone square card used to select a question."""

    def __init__(self, size: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setBorderRadius(8)

        self.checkbox = CheckBox(self)
        self.checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkbox.setAccessibleName("Select question")
        self.checkbox.setStyleSheet(
            self.checkbox.styleSheet()
            + """
            QCheckBox {
                min-width: 22px;
                min-height: 22px;
                max-width: 22px;
                max-height: 22px;
                margin-left: 0;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.checkbox.toggle()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        event.accept()


class SelectableQuestionCard(QWidget):
    """A selection card followed by an unchanged question card."""

    double_clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        meta: str = "",
        right_meta: str = "",
        data=None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.data = data
        self.question_card = QuestionCard(
            title=title,
            subtitle=subtitle,
            meta=meta,
            right_meta=right_meta,
            parent=self,
        )
        self.selection_card = QuestionSelectionCard(self.question_card.sizeHint().height(), self)
        self.checkbox = self.selection_card.checkbox
        self.question_card.double_clicked.connect(self.double_clicked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.selection_card, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.question_card, 1)


class QuestionCard(CardWidget):
    double_clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        meta: str = "",
        action_text: str | None = None,
        action_icon=None,
        right_meta: str = "",
        checkable: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.checkbox = CheckBox(self) if checkable else None
        self.action_button = PushButton(action_text or "", self) if (action_text or action_icon) else None
        self.right_meta_label = CaptionLabel(right_meta, self) if right_meta else None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        if self.checkbox:
            layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        self.title_label = StrongBodyLabel(title, self)
        self.subtitle_label = BodyLabel(subtitle, self)
        self.meta_label = CaptionLabel(meta, self)
        self.subtitle_label.setWordWrap(True)
        self.meta_label.setWordWrap(True)
        text_layout.addWidget(self.title_label)
        if subtitle:
            text_layout.addWidget(self.subtitle_label)
        if meta:
            text_layout.addWidget(self.meta_label)
        layout.addLayout(text_layout, 1)

        if self.right_meta_label:
            layout.addWidget(self.right_meta_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        if self.action_button:
            if action_icon:
                self.action_button.setIcon(action_icon)
            if not action_text:
                self.action_button.setFixedWidth(36)
            layout.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignVCenter)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        event.accept()


def bank_card_title(subject: str, bank_name: str) -> str:
    return f"{SUBJECTS.get(subject, subject)} · {bank_name}"
