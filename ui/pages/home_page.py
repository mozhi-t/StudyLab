from __future__ import annotations

from datetime import date, timedelta

from PyQt6.QtCore import QByteArray, QBuffer, QIODevice, QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    SegmentedWidget,
    SingleDirectionScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    isDarkTheme,
    themeColor,
)

from config.settings import APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE
from core.base.json_store import JsonStore
from ui.styles.home import HOME_STYLE_CLASSES, HomeWelcomeStyle
from ui.styles.title_style import apply_page_title_style
from ui.widgets.base import AbilityRadarWidget, AbilityRadarWindow, StyledCardWidget


class AvatarWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._name = "用户"
        self._pixmap: QPixmap | None = None
        self.setFixedSize(76, 76)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点击更换头像")

    def set_name(self, name: str) -> None:
        self._name = name.strip() or "用户"
        self.update()

    def set_image_data(self, image_data: bytes | None) -> None:
        pixmap = QPixmap()
        self._pixmap = pixmap if image_data and pixmap.loadFromData(image_data) else None
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = themeColor()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 38))
        painter.drawEllipse(self.rect().adjusted(2, 2, -2, -2))
        painter.setPen(QPen(accent, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))

        if self._pixmap is not None:
            target = self.rect().adjusted(5, 5, -5, -5)
            scaled = self._pixmap.scaled(
                target.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            source_x = max((scaled.width() - target.width()) // 2, 0)
            source_y = max((scaled.height() - target.height()) // 2, 0)
            painter.save()
            clip = QPainterPath()
            clip.addEllipse(QRectF(target))
            painter.setClipPath(clip)
            painter.drawPixmap(
                QRectF(target),
                scaled,
                QRectF(source_x, source_y, target.width(), target.height()),
            )
            painter.restore()
            return

        font = QFont(self.font())
        font.setPointSize(22)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(accent)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._name[0].upper())


class MetricWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        self.title_label = CaptionLabel(title, self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label = SubtitleLabel("0", self)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_font = QFont(self.value_label.font())
        value_font.setPointSize(17)
        value_font.setWeight(QFont.Weight.DemiBold)
        self.value_label.setFont(value_font)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class StudyHeatmapWidget(QWidget):
    CELL_SIZE = 12
    CELL_GAP = 3
    LABEL_WIDTH = 24
    TOP_MARGIN = 28

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._counts: dict[date, int] = {}
        self._duration_seconds: dict[date, int] = {}
        self._mode = "questions"
        self._day_span = 365
        self._start_date = self._aligned_start(date.today(), self._day_span)
        self._end_date = date.today()
        self.setMouseTracking(True)
        self.setMinimumHeight(184)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(820, 184)

    def set_data(
        self,
        counts: dict[date, int],
        end_date: date | None = None,
        duration_seconds: dict[date, int] | None = None,
    ) -> None:
        self._end_date = end_date or date.today()
        self._start_date = self.start_date_for(self._end_date)
        self._counts = counts
        self._duration_seconds = duration_seconds or {}
        self.update()

    def set_mode(self, mode: str) -> None:
        if mode not in {"questions", "duration"}:
            return
        self._mode = mode
        self.update()

    def _value_for(self, day: date) -> int:
        source = self._duration_seconds if self._mode == "duration" else self._counts
        return source.get(day, 0)

    def set_day_span(self, days: int) -> None:
        self._day_span = max(int(days), 7)
        self._start_date = self.start_date_for(self._end_date)
        self.update()

    def start_date_for(self, end_date: date) -> date:
        return self._aligned_start(end_date, self._day_span)

    @staticmethod
    def _aligned_start(end_date: date, day_span: int = 365) -> date:
        start = end_date - timedelta(days=day_span - 1)
        return start - timedelta(days=(start.weekday() + 1) % 7)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        text_color = QColor(205, 205, 205) if isDarkTheme() else QColor(95, 95, 95)
        painter.setPen(text_color)
        font = QFont(self.font())
        font.setPointSize(8)
        painter.setFont(font)
        origin_x, _grid_width = self._grid_geometry()

        for row, label in ((1, "一"), (3, "三"), (5, "五")):
            y = self.TOP_MARGIN + row * (self.CELL_SIZE + self.CELL_GAP)
            painter.drawText(
                origin_x - self.LABEL_WIDTH - 7,
                y,
                self.LABEL_WIDTH,
                self.CELL_SIZE,
                Qt.AlignmentFlag.AlignRight,
                label,
            )

        last_month_x = -100
        current = self._start_date
        while current <= self._end_date:
            week, weekday = self._cell_position(current)
            x = origin_x + week * (self.CELL_SIZE + self.CELL_GAP)
            y = self.TOP_MARGIN + weekday * (self.CELL_SIZE + self.CELL_GAP)
            if current.day <= 7 and x - last_month_x >= 28:
                painter.setPen(text_color)
                painter.drawText(x, 0, 32, 18, Qt.AlignmentFlag.AlignLeft, f"{current.month}月")
                last_month_x = x
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._cell_color(self._value_for(current)))
            painter.drawRoundedRect(QRectF(x, y, self.CELL_SIZE, self.CELL_SIZE), 2, 2)
            current += timedelta(days=1)

        self._draw_legend(painter)

    def mouseMoveEvent(self, event) -> None:
        cell = self._date_at(event.position())
        if cell is None or cell > self._end_date:
            QToolTip.hideText()
            return
        value = self._value_for(cell)
        detail = self._format_duration(value) if self._mode == "duration" else f"{value} 题"
        QToolTip.showText(event.globalPosition().toPoint(), f"{cell:%Y-%m-%d} · {detail}", self)

    def leaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().leaveEvent(event)

    def _cell_position(self, day: date) -> tuple[int, int]:
        offset = (day - self._start_date).days
        return offset // 7, (day.weekday() + 1) % 7

    def _date_at(self, position: QPointF) -> date | None:
        origin_x, _grid_width = self._grid_geometry()
        x = position.x() - origin_x
        y = position.y() - self.TOP_MARGIN
        if x < 0 or y < 0:
            return None
        step = self.CELL_SIZE + self.CELL_GAP
        week, weekday = int(x // step), int(y // step)
        if weekday > 6 or x % step > self.CELL_SIZE or y % step > self.CELL_SIZE:
            return None
        result = self._start_date + timedelta(days=week * 7 + weekday)
        return result if result >= self._start_date else None

    def _grid_geometry(self) -> tuple[int, int]:
        step = self.CELL_SIZE + self.CELL_GAP
        week_count = (self._end_date - self._start_date).days // 7 + 1
        grid_width = week_count * step - self.CELL_GAP
        total_width = self.LABEL_WIDTH + 7 + grid_width
        left = max((self.width() - total_width) // 2, 0)
        return left + self.LABEL_WIDTH + 7, grid_width

    def _cell_color(self, count: int) -> QColor:
        if count <= 0:
            return QColor(255, 255, 255, 18) if isDarkTheme() else QColor(30, 30, 30, 18)
        if self._mode == "duration":
            colors = ((159, 205, 255), (91, 160, 232), (45, 112, 200), (25, 75, 150))
            level = 0 if count <= 15 * 60 else 1 if count <= 30 * 60 else 2 if count <= 60 * 60 else 3
        else:
            colors = ((155, 233, 168), (79, 201, 111), (35, 154, 73), (20, 108, 52))
            level = 0 if count <= 5 else 1 if count <= 15 else 2 if count <= 30 else 3
        red, green, blue = colors[level]
        if isDarkTheme():
            red = max(red - 18, 0)
            green = max(green - 18, 0)
            blue = max(blue - 18, 0)
        return QColor(red, green, blue)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds} 秒"
        hours, remaining = divmod(seconds, 3600)
        minutes = remaining // 60
        if hours:
            return f"{hours} 小时 {minutes} 分钟" if minutes else f"{hours} 小时"
        return f"{minutes} 分钟"

    def _draw_legend(self, painter: QPainter) -> None:
        y = self.TOP_MARGIN + 7 * (self.CELL_SIZE + self.CELL_GAP) + 10
        origin_x, grid_width = self._grid_geometry()
        x = max(origin_x + grid_width - 128, origin_x)
        painter.setPen(QColor(205, 205, 205) if isDarkTheme() else QColor(95, 95, 95))
        painter.drawText(x, y, 20, 14, Qt.AlignmentFlag.AlignVCenter, "少")
        x += 23
        samples = (0, 60, 16 * 60, 31 * 60, 61 * 60) if self._mode == "duration" else (0, 1, 6, 16, 31)
        for count in samples:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._cell_color(count))
            painter.drawRoundedRect(QRectF(x, y + 2, self.CELL_SIZE, self.CELL_SIZE), 2, 2)
            x += self.CELL_SIZE + self.CELL_GAP
        painter.setPen(QColor(205, 205, 205) if isDarkTheme() else QColor(95, 95, 95))
        painter.drawText(x + 2, y, 20, 14, Qt.AlignmentFlag.AlignVCenter, "多")



class HomePage(QWidget):
    METRICS = (
        ("total_days", "累计学习天数"),
        ("total_questions", "累计刷题数"),
        ("continuous_days", "连续学习天数"),
        ("today_questions", "今日刷题数"),
        ("today_time", "今日学习时间"),
        ("today_accuracy", "今日刷题正确率"),
    )

    def __init__(self, user_manager, parent: QWidget | None = None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.settings_store = JsonStore(APP_SETTINGS_FILE, APP_SETTINGS_TEMPLATE)
        self.metric_widgets: dict[str, MetricWidget] = {}
        self._ability_values: dict[str, float] = {}
        self._ability_radar_window: AbilityRadarWindow | None = None

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = SingleDirectionScrollArea(self, Qt.Orientation.Vertical)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.enableTransparentBackground()
        page_layout.addWidget(self.scroll)

        self.content = QWidget(self.scroll)
        self.content.setObjectName("homePageContent")
        root = QVBoxLayout(self.content)
        root.setContentsMargins(20, 20, 20, 24)
        root.setSpacing(10)

        self.page_title = SubtitleLabel("主页", self.content)
        apply_page_title_style(self.page_title)
        root.addWidget(self.page_title)

        self.home_styles: dict[str, HomeWelcomeStyle] = {
            style_class.style_name: style_class(
                AvatarWidget,
                AbilityRadarWidget,
                self.content,
            )
            for style_class in HOME_STYLE_CLASSES
        }
        self.welcome_stack = QStackedWidget(self.content)
        self.welcome_stack.setFixedHeight(164)
        for style_widget in self.home_styles.values():
            style_widget.avatar.clicked.connect(self._choose_avatar)
            style_widget.radar.clicked.connect(self._show_ability_radar)
            self.welcome_stack.addWidget(style_widget)
        root.addWidget(self.welcome_stack)

        self.stats_card = StyledCardWidget(self.content, radius=14)
        stats_layout = QHBoxLayout(self.stats_card)
        stats_layout.setContentsMargins(12, 18, 12, 18)
        stats_layout.setSpacing(0)
        for index, (key, title) in enumerate(self.METRICS):
            metric = MetricWidget(title, self.stats_card)
            self.metric_widgets[key] = metric
            stats_layout.addWidget(metric, 1)
            if index < len(self.METRICS) - 1:
                separator = QFrame(self.stats_card)
                separator.setFrameShape(QFrame.Shape.VLine)
                separator.setFrameShadow(QFrame.Shadow.Plain)
                separator.setStyleSheet(
                    "QFrame{color: rgba(128, 128, 128, 0.34); max-width: 1px;}"
                )
                stats_layout.addWidget(separator)
        root.addWidget(self.stats_card)

        self.analytics_container = QWidget(self.content)
        analytics_layout = QHBoxLayout(self.analytics_container)
        analytics_layout.setContentsMargins(0, 0, 0, 0)
        analytics_layout.setSpacing(10)

        self.heatmap_card = StyledCardWidget(self.analytics_container, radius=14)
        self.heatmap_card.setMinimumHeight(252)
        heatmap_layout = QVBoxLayout(self.heatmap_card)
        heatmap_layout.setContentsMargins(20, 16, 20, 16)
        heatmap_layout.setSpacing(4)
        self.heatmap_title = StrongBodyLabel("学习活跃度", self.heatmap_card)
        self.heatmap_summary = CaptionLabel("过去一年暂无学习记录", self.heatmap_card)
        heatmap_header = QHBoxLayout()
        heatmap_header.setContentsMargins(0, 0, 0, 0)
        heatmap_header.addWidget(self.heatmap_title)
        heatmap_header.addStretch(1)
        self.heatmap_mode = SegmentedWidget(self.heatmap_card)
        self.heatmap_mode.addItem("questions", "刷题数", lambda: self._set_heatmap_mode("questions"))
        self.heatmap_mode.addItem("duration", "刷题时长", lambda: self._set_heatmap_mode("duration"))
        self.heatmap_mode.setCurrentItem("questions")
        heatmap_header.addWidget(self.heatmap_mode)
        self.heatmap = StudyHeatmapWidget(self.heatmap_card)
        heatmap_layout.addLayout(heatmap_header)
        heatmap_layout.addWidget(self.heatmap_summary)
        heatmap_layout.addWidget(self.heatmap)
        analytics_layout.addWidget(self.heatmap_card, 1)

        self.ability_card = StyledCardWidget(self.analytics_container, radius=14)
        self.ability_card.setFixedWidth(340)
        self.ability_card.setMinimumHeight(252)
        ability_layout = QVBoxLayout(self.ability_card)
        ability_layout.setContentsMargins(20, 16, 20, 16)
        ability_layout.setSpacing(8)
        self.ability_title = StrongBodyLabel("学科能力", self.ability_card)
        ability_layout.addWidget(self.ability_title)
        ability_layout.addStretch(1)
        style_three_radar = self.home_styles["样式三"].radar
        style_three_radar.setFixedSize(300, 180)
        ability_layout.addWidget(
            style_three_radar,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        ability_layout.addStretch(1)
        analytics_layout.addWidget(self.ability_card)
        root.addWidget(self.analytics_container)
        root.addStretch(1)

        self.scroll.setWidget(self.content)
        self.content.setStyleSheet("QWidget#homePageContent{background: transparent; border: none;}")
        self.reload()

    def reload(self) -> None:
        user = self.user_manager.load_user()
        today = date.today()
        today_stats = self.user_manager.get_daily_stats(today)
        abilities = self.user_manager.get_subject_abilities()
        nickname = user.nickname.strip() or "用户"

        avatar_data = self.user_manager.load_avatar()
        ability_values = {item.subject: item.ability_index for item in abilities}
        self._ability_values = ability_values
        for style_widget in self.home_styles.values():
            style_widget.set_profile(nickname, avatar_data)
            style_widget.set_abilities(ability_values)
        if self._ability_radar_window is not None:
            self._ability_radar_window.set_values(ability_values)

        settings = APP_SETTINGS_TEMPLATE | self.settings_store.load()
        daily_goal = max(int(settings.get("daily_question_goal", 50)), 1)
        completion = today_stats.answered_count / daily_goal * 100
        for style_widget in self.home_styles.values():
            style_widget.set_completion(completion)
        self._set_home_page_style(settings.get("home_page_style", "样式一"))

        accuracy = (
            f"{today_stats.score_earned / today_stats.score_possible * 100:.0f}%"
            if today_stats.score_possible > 0
            else "--"
        )
        metric_values = {
            "total_days": f"{user.total_study_days} 天",
            "total_questions": f"{user.total_questions} 题",
            "continuous_days": f"{user.continuous_days} 天",
            "today_questions": f"{today_stats.answered_count} 题",
            "today_time": self._format_duration(today_stats.study_seconds),
            "today_accuracy": accuracy,
        }
        for key, value in metric_values.items():
            self.metric_widgets[key].set_value(value)

        start_date = self.heatmap.start_date_for(today)
        daily_items = self.user_manager.list_daily_stats(start_date, today)
        heatmap_counts = {
            date.fromisoformat(item.study_date): item.answered_count
            for item in daily_items
        }
        heatmap_durations = {
            date.fromisoformat(item.study_date): item.study_seconds
            for item in daily_items
        }
        self.heatmap.set_data(heatmap_counts, today, heatmap_durations)
        active_days = sum(1 for item in daily_items if item.answered_count > 0 or item.study_seconds > 0)
        self._heatmap_active_days = active_days
        self._heatmap_total_questions = sum(item.answered_count for item in daily_items)
        self._heatmap_total_seconds = sum(item.study_seconds for item in daily_items)
        self._update_heatmap_summary()

    def _set_heatmap_mode(self, mode: str) -> None:
        self.heatmap.set_mode(mode)
        self._update_heatmap_summary()

    def _update_heatmap_summary(self) -> None:
        if not hasattr(self, "_heatmap_active_days"):
            return
        period_text = "近半年" if self.heatmap._day_span == 182 else "过去一年"
        if self.heatmap._mode == "duration":
            total = self._format_duration(self._heatmap_total_seconds)
            detail = f"累计学习 {total}"
        else:
            detail = f"共完成 {self._heatmap_total_questions} 题"
        self.heatmap_summary.setText(
            f"{period_text}活跃 {self._heatmap_active_days} 天，{detail}"
        )

    def _set_home_page_style(self, style: str) -> None:
        style_widget = self.home_styles.get(style, self.home_styles["样式一"])
        self.welcome_stack.setCurrentWidget(style_widget)
        self.ability_card.setVisible(style_widget.shows_separate_ability_card)
        self.heatmap.set_day_span(182 if style_widget.shows_separate_ability_card else 365)

    def _show_ability_radar(self) -> None:
        if self._ability_radar_window is None:
            self._ability_radar_window = AbilityRadarWindow(self)
        self._ability_radar_window.set_values(self._ability_values)
        if self._ability_radar_window.isMinimized():
            self._ability_radar_window.showNormal()
        else:
            self._ability_radar_window.show()
        self._ability_radar_window.raise_()
        self._ability_radar_window.activateWindow()

    def _choose_avatar(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择头像",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        normalized = pixmap.scaled(
            512,
            512,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max((normalized.width() - 512) // 2, 0)
        y = max((normalized.height() - 512) // 2, 0)
        normalized = normalized.copy(x, y, 512, 512)
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        normalized.save(buffer, "PNG")
        buffer.close()
        self.user_manager.save_avatar(bytes(data))
        for style_widget in self.home_styles.values():
            style_widget.avatar.set_image_data(bytes(data))

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds < 60:
            return "<1 分钟" if seconds > 0 else "0 分钟"
        hours, remaining = divmod(seconds, 3600)
        minutes = remaining // 60
        if hours:
            return f"{hours}小时{minutes}分" if minutes else f"{hours}小时"
        return f"{minutes} 分钟"
