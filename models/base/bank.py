from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BankMeta:
    name: str
    subject: str
    create_time: str
