from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QWidget
from qfluentwidgets import BodyLabel, SubtitleLabel

from ui.widgets.styled_card import StyledCardWidget


class HomeWelcomeStyle(StyledCardWidget):
    """主页欢迎卡样式接口。

    自定义样式应继承此类、完成布局，并实现 ``set_completion``。
    ``avatar_factory`` 与 ``radar_factory`` 由主页注入，避免样式与具体组件耦合。
    """

    style_name = ""

    def __init__(
        self,
        avatar_factory: Callable[[QWidget], QWidget],
        radar_factory: Callable[[QWidget], QWidget],
        parent: QWidget | None = None,
    ):
        super().__init__(parent, radius=16)
        self.setFixedHeight(164)
        self.avatar = avatar_factory(self)
        self.greeting_label = SubtitleLabel("欢迎，用户", self)
        self.subtitle_label = BodyLabel("今天也向目标再靠近一点。", self)
        self.radar = radar_factory(self)

    def set_profile(self, nickname: str, avatar_data: bytes | None) -> None:
        self.greeting_label.setText(f"欢迎，{nickname}")
        self.avatar.set_name(nickname)
        self.avatar.set_image_data(avatar_data)

    def set_abilities(self, abilities: dict[str, float]) -> None:
        self.radar.set_values(abilities)

    def set_completion(self, completion: float) -> None:
        raise NotImplementedError
