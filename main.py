from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from config.theme import apply_theme, apply_ui_scale
from core.data_manager import bootstrap_app
from core.errors import AppError, install_exception_hook
from core.favorite_manager import FavoriteManager
from core.question_index import QuestionIndexManager
from core.user_data import UserDataManager
from core.wrong_manager import WrongManager
from ui.main_window import MainWindow


def main() -> int:
    install_exception_hook()
    bootstrap_app()

    apply_ui_scale()
    app = QApplication(sys.argv)

    user_manager = UserDataManager()
    question_index_manager = QuestionIndexManager()
    wrong_manager = WrongManager()
    favorite_manager = FavoriteManager()

    apply_theme()

    window = MainWindow(
        user_manager=user_manager,
        question_index_manager=question_index_manager,
        wrong_manager=wrong_manager,
        favorite_manager=favorite_manager,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AppError:
        raise
