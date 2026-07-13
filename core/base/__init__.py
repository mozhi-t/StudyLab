"""Shared application services and infrastructure."""

from core.base.app_initializer import initialize_app
from core.base.database import DatabaseManager
from core.base.favorite_manager import FavoriteManager
from core.base.question_index import QuestionIndexManager
from core.base.user_data import UserDataManager
from core.base.wrong_manager import WrongManager

__all__ = [
    "DatabaseManager",
    "FavoriteManager",
    "QuestionIndexManager",
    "UserDataManager",
    "WrongManager",
    "initialize_app",
]
