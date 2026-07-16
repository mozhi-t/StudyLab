from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import Action, BodyLabel, CommandBar, FluentIcon


class SelectionCommandBar(CommandBar):
    practice_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count_label = BodyLabel("已选择 0 题", self)
        self.addWidget(self.count_label)
        self.addSeparator()

        self.practice_action = Action(
            FluentIcon.PLAY,
            "一键练习",
            triggered=lambda: self.practice_requested.emit(),
        )
        self.delete_action = Action(
            FluentIcon.DELETE,
            "删除",
            triggered=lambda: self.delete_requested.emit(),
        )
        self.addActions([self.practice_action, self.delete_action])
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def set_selected_count(self, count: int) -> None:
        self.count_label.setText(f"已选择 {count} 题")
