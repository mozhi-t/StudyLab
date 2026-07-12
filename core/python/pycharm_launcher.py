from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class PyCharmLauncher:
    EXECUTABLE_NAMES = ("pycharm64.exe", "pycharm.exe", "pycharm64", "pycharm")

    def resolve(self, install_dir: str) -> Path | None:
        if install_dir:
            base = Path(install_dir).expanduser()
            candidates = [base / "bin" / name for name in self.EXECUTABLE_NAMES]
            candidates += [base / name for name in self.EXECUTABLE_NAMES]
            if base.is_file():
                candidates.insert(0, base)
            for candidate in candidates:
                if candidate.is_file():
                    return candidate.resolve()
            return None
        return self.detect()

    def detect(self) -> Path | None:
        for name in self.EXECUTABLE_NAMES:
            found = shutil.which(name)
            if found:
                return Path(found).resolve()
        roots = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "JetBrains",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
            Path(os.environ.get("LOCALAPPDATA", "")) / "JetBrains" / "Toolbox" / "apps",
        ]
        for root in roots:
            if not root.is_dir():
                continue
            for name in self.EXECUTABLE_NAMES[:2]:
                try:
                    found = next(root.rglob(name), None)
                except OSError:
                    found = None
                if found and found.is_file():
                    return found.resolve()
        return None

    @staticmethod
    def install_dir_for(executable: Path) -> Path:
        executable = executable.resolve()
        if executable.parent.name.lower() == "bin":
            return executable.parent.parent
        return executable.parent

    def launch(self, install_dir: str, file_path: Path) -> tuple[bool, str]:
        executable = self.resolve(install_dir)
        if executable is None:
            return False, "未找到 PyCharm，请先在设置中配置安装目录"
        try:
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen([str(executable), str(file_path.resolve())], close_fds=True, creationflags=creationflags)
            return True, str(executable)
        except OSError as exc:
            return False, str(exc)
