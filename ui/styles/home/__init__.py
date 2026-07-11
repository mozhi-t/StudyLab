from ui.styles.home.base import HomeWelcomeStyle
from ui.styles.home.style_one import HomeStyleOne
from ui.styles.home.style_two import HomeStyleTwo


HOME_STYLE_CLASSES: tuple[type[HomeWelcomeStyle], ...] = (
    HomeStyleOne,
    HomeStyleTwo,
)

__all__ = [
    "HOME_STYLE_CLASSES",
    "HomeStyleOne",
    "HomeStyleTwo",
    "HomeWelcomeStyle",
]
