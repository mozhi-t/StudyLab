from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, TeachingTip, TeachingTipTailPosition


def show_favorite_tip(target: QWidget, favorite: bool, parent: QWidget) -> None:
    if favorite:
        TeachingTip.create(
            target,
            "收藏成功",
            "题目已加入收藏夹",
            icon=FluentIcon.HEART,
            duration=1500,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            parent=parent,
        )
        return
    TeachingTip.create(
        target,
        "已移出收藏",
        "题目已从收藏夹移除",
        icon=FluentIcon.DELETE,
        duration=1500,
        tailPosition=TeachingTipTailPosition.BOTTOM,
        parent=parent,
    )
