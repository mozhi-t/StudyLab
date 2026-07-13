from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget
from qfluentwidgets import BodyLabel, RadioButton, isDarkTheme

from ui.widgets.base.styled_card import StyledCardWidget


class OptionCard(StyledCardWidget):
    def __init__(self, option_key: str, parent: QWidget | None = None):
        self._state = "default"
        super().__init__(parent, radius=12, light_border_alpha=34)
        self.option_key = option_key
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.button = RadioButton(self)
        self.button.setObjectName(f"choiceOption{option_key}")
        self.button.setText("")
        self.button.setFixedWidth(24)
        self.button.setMinimumHeight(24)
        self.button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.text_label = BodyLabel("", self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(12)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.text_label, 1, Qt.AlignmentFlag.AlignVCenter)

    def set_option_text(self, text: str) -> None:
        self.text_label.setText(text)

    def set_checked(self, checked: bool) -> None:
        self.button.setChecked(checked)

    def set_enabled(self, enabled: bool) -> None:
        self.button.setEnabled(enabled)

    def set_state(self, state: str) -> None:
        self._state = state
        self._apply_state_style()
        self.update()

    def _normalBackgroundColor(self):
        if self._state == "correct":
            return QColor(15, 163, 97, 42)
        if self._state == "wrong":
            return QColor(224, 72, 72, 38)
        return super()._normalBackgroundColor()

    def _apply_state_style(self) -> None:
        if self._state == "correct":
            self.text_label.setStyleSheet("color: rgb(19, 126, 67); font-weight: 600;")
        elif self._state == "wrong":
            self.text_label.setStyleSheet("color: rgb(198, 52, 52); font-weight: 600;")
        else:
            self.text_label.setStyleSheet("color: white;" if isDarkTheme() else "")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.button.isEnabled():
            self.button.click()
            event.accept()
            return
        super().mousePressEvent(event)
