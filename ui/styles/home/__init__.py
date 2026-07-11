from ui.styles.home.base import HomeWelcomeStyle
from ui.styles.home.style_one import HomeStyleOne
from ui.styles.home.style_two import HomeStyleTwo
from ui.styles.home.style_three import HomeStyleThree


HOME_STYLE_CLASSES: tuple[type[HomeWelcomeStyle], ...] = (
    HomeStyleOne,
    HomeStyleTwo,
    HomeStyleThree,
)

__all__ = [
    "HOME_STYLE_CLASSES",
    "HomeStyleOne",
    "HomeStyleTwo",
    "HomeStyleThree",
    "HomeWelcomeStyle",
]
