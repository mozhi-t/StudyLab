from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

if __package__ in (None, ""):
    from core.bootstrap import ensure_server_files
    from core.errors import AppError, install_exception_hook
    from core.theme import apply_theme
    from ui.window import ExamServerWindow
else:
    from .core.bootstrap import ensure_server_files
    from .core.errors import AppError, install_exception_hook
    from .core.theme import apply_theme
    from .ui.window import ExamServerWindow


def main() -> int:
    install_exception_hook()
    ensure_server_files()
    app = QApplication(sys.argv)
    apply_theme()
    window = ExamServerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AppError:
        raise
