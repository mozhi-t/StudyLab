from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, FluentIcon, IconWidget, IndeterminateProgressRing, PrimaryPushButton, SubtitleLabel
from qfluentwidgets.common.style_sheet import FluentStyleSheet
from qfluentwidgets.components.dialog_box.mask_dialog_base import MaskDialogBase


class IndexCheckDialog(MaskDialogBase):
    check_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "confirm"

        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignmentFlag.AlignCenter)

        self.button_group = QFrame(self.widget)
        self.yes_button = PrimaryPushButton("确定", self.button_group)
        self.cancel_button = QPushButton("取消", self.button_group)

        self.v_box_layout = QVBoxLayout(self.widget)
        self.view_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout(self.button_group)

        self.stack = QStackedWidget(self.widget)
        self.stack.setMinimumWidth(420)

        self.confirm_page = QWidget(self.stack)
        self.confirm_layout = QVBoxLayout(self.confirm_page)
        self.confirm_layout.setContentsMargins(0, 0, 0, 0)
        self.confirm_layout.setSpacing(0)

        self.confirm_title_label = SubtitleLabel("是否要进行索引检查", self.confirm_page)
        self.confirm_message_label = BodyLabel("该功能会检查并尝试修复所有索引文件的内容缺失或格式缺失问题，您可能等待较长时间", self.confirm_page)
        self.confirm_message_label.setWordWrap(True)

        self.confirm_layout.addWidget(self.confirm_title_label)
        self.confirm_layout.addWidget(self.confirm_message_label)

        self.status_page = QWidget(self.stack)
        self.status_layout = QVBoxLayout(self.status_page)
        self.status_layout.setContentsMargins(0, 12, 0, 12)
        self.status_layout.setSpacing(14)
        self.status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_title_label = SubtitleLabel("正在检查索引", self.status_page)
        self.status_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.indicator_container = QWidget(self.status_page)
        self.indicator_container.setFixedSize(80, 80)
        self.indicator_layout = QVBoxLayout(self.indicator_container)
        self.indicator_layout.setContentsMargins(0, 0, 0, 0)
        self.indicator_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_ring = IndeterminateProgressRing(self.indicator_container, start=False)
        self.progress_ring.setFixedSize(64, 64)
        self.indicator_layout.addWidget(self.progress_ring, 0, Qt.AlignmentFlag.AlignCenter)

        self.complete_icon = IconWidget(FluentIcon.COMPLETED, self.indicator_container)
        self.complete_icon.setFixedSize(64, 64)
        self.indicator_layout.addWidget(self.complete_icon, 0, Qt.AlignmentFlag.AlignCenter)
        self.complete_icon.hide()

        self.status_label = BodyLabel("请稍候...", self.status_page)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumWidth(320)
        self.status_label.setMinimumHeight(48)
        status_font = QFont(self.status_label.font())
        status_font.setPointSize(11)
        self.status_label.setFont(status_font)

        self.status_layout.addWidget(self.status_title_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.status_layout.addWidget(self.indicator_container, 0, Qt.AlignmentFlag.AlignCenter)
        self.status_layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)

        self.stack.addWidget(self.confirm_page)
        self.stack.addWidget(self.status_page)

        self._init_style()
        self._init_layout()

        self.yes_button.clicked.connect(self._on_yes_clicked)
        self.cancel_button.clicked.connect(self.reject)

    def _init_style(self) -> None:
        self.button_group.setObjectName("buttonGroup")
        self.cancel_button.setObjectName("cancelButton")
        FluentStyleSheet.DIALOG.apply(self)
        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))
        self.button_group.setStyleSheet("QFrame#buttonGroup{border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;}")
        self.yes_button.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect)
        self.cancel_button.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect)
        self.yes_button.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.yes_button.setFocus()

    def _init_layout(self) -> None:
        self.v_box_layout.setSpacing(0)
        self.v_box_layout.setContentsMargins(0, 0, 0, 0)
        self.v_box_layout.addLayout(self.view_layout, 1)
        self.v_box_layout.addWidget(self.button_group, 0, Qt.AlignmentFlag.AlignBottom)

        self.view_layout.setSpacing(12)
        self.view_layout.setContentsMargins(24, 24, 24, 24)
        self.view_layout.addWidget(self.stack)

        self.button_group.setFixedHeight(81)
        self.button_layout.setSpacing(12)
        self.button_layout.setContentsMargins(24, 24, 24, 24)
        self.button_layout.addWidget(self.yes_button, 1, Qt.AlignmentFlag.AlignVCenter)
        self.button_layout.addWidget(self.cancel_button, 1, Qt.AlignmentFlag.AlignVCenter)

    def _on_yes_clicked(self) -> None:
        if self._mode == "confirm":
            self.start_checking()
            self.check_requested.emit()
            return
        self.accept()

    def start_checking(self) -> None:
        self._mode = "checking"
        self.stack.setCurrentWidget(self.status_page)
        self.status_title_label.setText("正在检查索引")
        self.progress_ring.show()
        self.complete_icon.hide()
        self.status_label.setText("请稍候...")
        self.button_group.hide()
        self.widget.adjustSize()
        self._center_widget()
        QTimer.singleShot(0, self.progress_ring.start)

    def finish_checking(self, issue_count: int) -> None:
        self._mode = "done"
        self.stack.setCurrentWidget(self.status_page)
        self.status_title_label.setText("检查完成")
        self.progress_ring.stop()
        self.progress_ring.hide()
        self.complete_icon.show()
        self.status_label.setText(f"检查完成，{'未发现问题' if issue_count == 0 else f'发现 {issue_count} 个问题'}")
        self.button_group.show()
        self.yes_button.show()
        self.yes_button.setText("完成")
        self.cancel_button.hide()
        self.widget.adjustSize()
        self._center_widget()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._center_widget()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._center_widget()

    def _center_widget(self) -> None:
        self.widget.adjustSize()
        x = max((self.width() - self.widget.width()) // 2, 0)
        y = max((self.height() - self.widget.height()) // 2, 0)
        self.widget.move(x, y)
