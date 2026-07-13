from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from config.theme import apply_theme, apply_ui_scale
from core.base import (
    FavoriteManager,
    QuestionIndexManager,
    UserDataManager,
    WrongManager,
    initialize_app,
)
from core.base.errors import AppError, install_exception_hook
from ui.main_window import MainWindow


def main() -> int:
    install_exception_hook()
    database = initialize_app()

    apply_ui_scale()
    app = QApplication(sys.argv)

    user_manager = UserDataManager(database)
    question_index_manager = QuestionIndexManager()
    wrong_manager = WrongManager(database)
    favorite_manager = FavoriteManager(database)

    app.aboutToQuit.connect(database.close)

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
