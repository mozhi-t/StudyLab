from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.theme import apply_theme
from core.errors import AppError, install_exception_hook
from exam_server.bootstrap import ensure_server_files
from exam_server.window import ExamServerWindow


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
