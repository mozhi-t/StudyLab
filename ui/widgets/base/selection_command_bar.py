from __future__ import annotations

from PyQt6.QtCore import QEvent, QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import Action, BodyLabel, CommandBar, FluentIcon


class SelectionCommandBar(CommandBar):
    practice_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._expanded_search_width = 0
        self._animation_group: QParallelAnimationGroup | None = None
        self._focus_animation_group: QParallelAnimationGroup | None = None
        self._follow_search_edge = False
        self._search_edit: QWidget | None = None
        self._toolbar_layout: QHBoxLayout | None = None
        self._selection_pair_width = 0
        self._collapsed_search_width = 160
        self._focused_search_width = 420
        self._search_focus_expanded = False
        self._pinned_sibling_widths: list[tuple[QWidget, int, int]] = []

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

    def set_active(
        self,
        active: bool,
        search_edit: QWidget,
        toolbar_layout: QHBoxLayout,
        collapsed_search_width: int = 160,
        focused_search_width: int = 420,
    ) -> None:
        """Animate the search field and this bar into their selection states."""
        if active == self._active:
            return

        self._active = active
        self._attach_search_edit(search_edit, toolbar_layout)
        self._collapsed_search_width = collapsed_search_width
        self._focused_search_width = focused_search_width
        self._search_focus_expanded = active and search_edit.hasFocus()
        if active:
            self._pin_sibling_widths(search_edit, toolbar_layout)
        self._stop_focus_animation()
        if self._animation_group is not None:
            self._animation_group.stop()
            self._animation_group.deleteLater()
            self._animation_group = None

        current_search_width = search_edit.width()
        if active:
            self._expanded_search_width = max(self._expanded_search_width, current_search_width)
        elif self._expanded_search_width <= 0:
            self._expanded_search_width = current_search_width

        toolbar_layout.setStretchFactor(search_edit, 0)
        toolbar_layout.setStretchFactor(self, 1)

        if active and not self.isVisible():
            self.setMaximumWidth(0)
            self._follow_search_edge = True
            self.show()

        current_bar_width = self.width() if self.isVisible() else 0
        if active:
            spacing = max(toolbar_layout.spacing(), 0)
            desired_search_width = min(collapsed_search_width, self._expanded_search_width)
            freed_search_width = max(self._expanded_search_width - desired_search_width - spacing, 0)
            bar_target = max(self.suitableWidth(), freed_search_width)
            search_target = max(self._expanded_search_width - bar_target - spacing, 0)
            self._selection_pair_width = search_target + bar_target
        else:
            search_target = self._expanded_search_width
            bar_target = 0
            self._follow_search_edge = True

        # Pin the current geometries before changing the layout so the transition
        # begins exactly where the previous frame ended.
        search_edit.setMaximumWidth(max(current_search_width, 0))
        self.setMaximumWidth(max(current_bar_width, 0))

        group = QParallelAnimationGroup(self)
        easing = QEasingCurve.Type.InOutCubic
        self._add_animation(group, search_edit, b"maximumWidth", current_search_width, search_target, 460, easing)
        self._add_animation(group, self, b"maximumWidth", current_bar_width, bar_target, 460, easing)
        group.finished.connect(lambda: self._finish_transition(group, search_edit, toolbar_layout, active))
        self._animation_group = group
        group.start()

    @staticmethod
    def _add_animation(group, target, property_name, start, end, duration, easing) -> None:
        animation = QPropertyAnimation(target, property_name, group)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setDuration(duration)
        animation.setEasingCurve(easing)
        group.addAnimation(animation)

    def _finish_transition(
        self,
        group: QParallelAnimationGroup,
        search_edit: QWidget,
        toolbar_layout: QHBoxLayout,
        active: bool,
    ) -> None:
        if group is not self._animation_group or active != self._active:
            return

        self._animation_group = None
        if active:
            self.setMaximumWidth(max(self.width(), self.suitableWidth()))
            if self._search_focus_expanded:
                self._start_focus_animation()
        else:
            self.hide()
            self.setMaximumWidth(16777215)
            search_edit.setMaximumWidth(16777215)
            toolbar_layout.setStretchFactor(search_edit, 1)
            toolbar_layout.setStretchFactor(self, 0)
            self._follow_search_edge = False
            self._search_focus_expanded = False
            self._restore_sibling_widths()
        group.deleteLater()

    def _pin_sibling_widths(
        self,
        search_edit: QWidget,
        toolbar_layout: QHBoxLayout,
    ) -> None:
        if self._pinned_sibling_widths:
            return

        for index in range(toolbar_layout.count()):
            widget = toolbar_layout.itemAt(index).widget()
            if widget is None or widget is search_edit or widget is self:
                continue
            self._pinned_sibling_widths.append(
                (widget, widget.minimumWidth(), widget.maximumWidth())
            )
            widget.setFixedWidth(widget.width())

    def _restore_sibling_widths(self) -> None:
        for widget, minimum_width, maximum_width in self._pinned_sibling_widths:
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(16777215)
            widget.setMinimumWidth(minimum_width)
            widget.setMaximumWidth(maximum_width)
        self._pinned_sibling_widths.clear()

    def _attach_search_edit(self, search_edit: QWidget, toolbar_layout: QHBoxLayout) -> None:
        if self._search_edit is not search_edit:
            if self._search_edit is not None:
                self._search_edit.removeEventFilter(self)
            self._search_edit = search_edit
            search_edit.installEventFilter(self)
        self._toolbar_layout = toolbar_layout

    def eventFilter(self, watched, event: QEvent) -> bool:
        if watched is self._search_edit and self._active:
            if event.type() == QEvent.Type.FocusIn:
                self._search_focus_expanded = True
                if self._animation_group is None:
                    self._start_focus_animation()
            elif event.type() == QEvent.Type.FocusOut:
                self._search_focus_expanded = False
                if self._animation_group is None:
                    self._start_focus_animation()
            elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                watched.clearFocus()
        return super().eventFilter(watched, event)

    def _start_focus_animation(self) -> None:
        if not self._active or self._search_edit is None or self._toolbar_layout is None:
            return

        self._stop_focus_animation()
        current_search_width = self._search_edit.width()
        current_bar_width = self.width()
        desired_search_width = (
            self._focused_search_width
            if self._search_focus_expanded
            else self._collapsed_search_width
        )
        maximum_search_width = max(self._selection_pair_width - self.suitableWidth(), 0)
        search_target = min(desired_search_width, maximum_search_width)
        bar_target = self._selection_pair_width - search_target

        self._search_edit.setMaximumWidth(current_search_width)
        self.setMaximumWidth(current_bar_width)
        group = QParallelAnimationGroup(self)
        easing = QEasingCurve.Type.InOutCubic
        self._add_animation(
            group,
            self._search_edit,
            b"maximumWidth",
            current_search_width,
            search_target,
            280,
            easing,
        )
        self._add_animation(
            group,
            self,
            b"maximumWidth",
            current_bar_width,
            bar_target,
            280,
            easing,
        )
        group.finished.connect(
            lambda: self._finish_focus_animation(group, search_target, bar_target)
        )
        self._focus_animation_group = group
        group.start()

    def _finish_focus_animation(
        self,
        group: QParallelAnimationGroup,
        search_target: int,
        bar_target: int,
    ) -> None:
        if group is not self._focus_animation_group:
            return
        self._focus_animation_group = None
        if self._search_edit is not None:
            self._search_edit.setMaximumWidth(search_target)
        self.setMaximumWidth(bar_target)
        group.deleteLater()

    def _stop_focus_animation(self) -> None:
        if self._focus_animation_group is None:
            return
        self._focus_animation_group.stop()
        self._focus_animation_group.deleteLater()
        self._focus_animation_group = None

    def updateGeometry(self) -> None:
        """Keep command content attached to the moving right edge of the search field."""
        if not getattr(self, "_follow_search_edge", False):
            super().updateGeometry()
            return

        self._hiddenWidgets.clear()
        self.moreButton.hide()
        spacing = self.spacing()
        x = self.contentsMargins().left()
        height = self.height()
        for widget in self._widgets:
            widget.show()
            widget.move(x, (height - widget.height()) // 2)
            x += widget.width() + spacing
