from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpamClassifyDto:
    category: str
    is_spam: bool
    reason: str
