from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ExpandGroupSettingCard, FluentIcon, MessageBox, Pivot, PushButton, SingleDirectionScrollArea, SubtitleLabel
from qfluentwidgets.components.settings.expand_setting_card import GroupWidget

from ui.styles.title_style import apply_page_title_style


class WheelTransparentGroupWidget(GroupWidget):
    def wheelEvent(self, event) -> None:
        event.ignore()


class SubjectManageCard(ExpandGroupSettingCard):
    def __init__(self, icon, title: str, count: int = 0, parent: QWidget | None = None):
        super().__init__(icon, title, "单击以查看详情", parent)
        self.subject_title = title
        self.question_count = count
        self.count_label = BodyLabel(f"{count}题", self)
        self.addWidget(self.count_label)
        self._init_groups()

    def wheelEvent(self, event) -> None:
        event.ignore()

    def setExpand(self, isExpand: bool):
        super().setExpand(isExpand)
        self.count_label.setVisible(not self.isExpand)

    def _init_groups(self) -> None:
        manage_button = PushButton("管理", self.view)
        manage_button.setFixedWidth(96)
        self.addGroupWidget(
            WheelTransparentGroupWidget(
                FluentIcon.INFO,
                "总题数",
                f"{self.question_count}题",
                manage_button,
            )
        )

        update_button = PushButton("更新", self.view)
        update_button.setFixedWidth(96)
        self.addGroupWidget(
            WheelTransparentGroupWidget(
                FluentIcon.SYNC,
                "从题目源更新题目",
                "上次更新时间：暂无",
                update_button,
            )
        )

        export_button = PushButton("导出", self.view)
        export_button.setFixedWidth(96)
        self.addGroupWidget(
            WheelTransparentGroupWidget(
                FluentIcon.SAVE,
                "导出所有题目",
                "",
                export_button,
            )
        )

        clear_button = PushButton("清空", self.view)
        clear_button.setFixedWidth(96)
        clear_button.clicked.connect(self._confirm_clear_subject)
        clear_group = WheelTransparentGroupWidget(
            FluentIcon.DELETE,
            "清空该科目的所有题目",
            "",
            clear_button,
        )
        self.addGroupWidget(clear_group)

    def _confirm_clear_subject(self) -> None:
        dialog = MessageBox("清空题目", f"是否要清空[{self.subject_title}]科目的所有题目？", self.window())
        dialog.yesButton.setText("清空")
        dialog.cancelButton.setText("取消")
        dialog.exec()


class QuestionBankPage(QWidget):
    PAGE_TABS = {
        "question_manage": "题目管理",
        "local_paper": "本地组卷",
        "smart_paper": "智能组卷",
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_page = "question_manage"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.page_title = SubtitleLabel("题库", self)
        apply_page_title_style(self.page_title)
        layout.addWidget(self.page_title)

        self.pivot = Pivot(self)
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.pivot)
        nav_layout.addStretch(1)
        layout.addLayout(nav_layout)

        self.page_stack = QStackedWidget(self)
        for route_key, text in self.PAGE_TABS.items():
            self.pivot.addItem(routeKey=route_key, text=text, onClick=lambda: None)
            if route_key == "question_manage":
                self.page_stack.addWidget(self._create_question_manage_page())
            else:
                self.page_stack.addWidget(self._create_blank_page(route_key))
        self.pivot.setCurrentItem(self.current_page)

        layout.addWidget(self.page_stack, 1)
        self.pivot.currentItemChanged.connect(self._on_page_changed)

    def _create_question_manage_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("questionManagePage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = SingleDirectionScrollArea(page, Qt.Orientation.Vertical)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.enableTransparentBackground()
        page_layout.addWidget(scroll)

        content = QWidget(scroll)
        content.setObjectName("questionManageContent")
        content.setStyleSheet("QWidget#questionManageContent{background: transparent; border: none;}")
        scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)

        for title in ("语文", "数学", "英语", "计算机基础", "Python", "MySQL"):
            content_layout.addWidget(SubjectManageCard(FluentIcon.DICTIONARY, title, 0, content))
        content_layout.addStretch(1)

        return page

    def _create_blank_page(self, route_key: str) -> QWidget:
        page = QWidget(self)
        page.setObjectName(f"{route_key}Page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addStretch(1)
        return page

    def _on_page_changed(self, route_key: str) -> None:
        self.current_page = route_key
        index = list(self.PAGE_TABS).index(route_key)
        self.page_stack.setCurrentIndex(index)
