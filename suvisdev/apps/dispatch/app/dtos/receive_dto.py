from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ReceiveSaveCommand:
    sender: str
    subject: str
    body: str


@dataclass(frozen=True)
class ReceiveItem:
    id: int
    sender: str
    subject: str
    body: str
    received_at: datetime
