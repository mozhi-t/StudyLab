from __future__ import annotations

import random
import re
import socket
import string
from datetime import datetime


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def random_client_id(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def get_local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"


def safe_filename_part(value: str, fallback: str = "unknown") -> str:
    text = (value or "").strip()
    if not text:
        return fallback
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    sanitized = re.sub(r"\s+", "_", sanitized).strip(" .")
    return sanitized or fallback
