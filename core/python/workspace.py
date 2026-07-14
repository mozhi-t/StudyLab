from __future__ import annotations

import re
import shutil
from pathlib import Path

from config.settings import PYTHON_ANSWER_WORKSPACE_DIR


PROGRAM_MARKER = "#********Program********"
END_MARKER = "#********End********"


class PythonWorkspace:
    def __init__(self, root: Path = PYTHON_ANSWER_WORKSPACE_DIR):
        self.root = root.resolve()

    @staticmethod
    def safe_name(value: str) -> str:
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
        return value[:80] or "python_bank"

    def question_dir(self, bank_name: str, question_id: int) -> Path:
        return self.root / f"{self.safe_name(bank_name)}_question_{question_id}"

    def question_file(self, bank_name: str, question_id: int) -> Path:
        return self.question_dir(bank_name, question_id) / "main.py"

    def prepare_question(self, bank_name: str, question_id: int, template: str, *, reset: bool = False) -> Path:
        directory = self.question_dir(bank_name, question_id)
        if reset and directory.exists():
            self._assert_inside_root(directory)
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "main.py"
        if not path.exists():
            path.write_text(template, encoding="utf-8")
        return path

    def load(self, bank_name: str, question_id: int) -> str:
        return self.question_file(bank_name, question_id).read_text(encoding="utf-8")

    def save(self, bank_name: str, question_id: int, source: str) -> Path:
        path = self.question_file(bank_name, question_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def _assert_inside_root(self, path: Path) -> None:
        resolved = path.resolve()
        if resolved == self.root or self.root not in resolved.parents:
            raise ValueError("拒绝操作 Python 答题工作区以外的目录")


def split_template(source: str) -> tuple[str, str, str]:
    if source.count(PROGRAM_MARKER) != 1 or source.count(END_MARKER) != 1:
        raise ValueError("Program/End 标志缺失或重复")
    before, remainder = source.split(PROGRAM_MARKER, 1)
    program, after = remainder.split(END_MARKER, 1)
    return before, program, after


def fill_template(template: str, program: str) -> str:
    before, _template_program, after = split_template(template)
    program = program.strip("\r\n")
    return (
        f"{before}{PROGRAM_MARKER}\n"
        f"{program}\n"
        f"{END_MARKER}{after}"
    )


def validate_template(template: str, submitted: str) -> tuple[bool, str]:
    try:
        template_before, _template_program, template_after = split_template(template)
        submitted_before, _submitted_program, submitted_after = split_template(submitted)
    except ValueError as exc:
        return False, str(exc)
    if template_before != submitted_before or template_after != submitted_after:
        return False, "Program/End 标志之外的代码已被修改"
    return True, ""
