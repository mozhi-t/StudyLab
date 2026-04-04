from __future__ import annotations

from PyQt6.QtGui import QFont


def apply_page_title_style(label) -> None:
    font = QFont(label.font())
    font.setPointSize(18)
    font.setWeight(QFont.Weight.DemiBold)
    label.setFont(font)
