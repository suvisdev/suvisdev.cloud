from __future__ import annotations

from abc import ABC, abstractmethod


class ModerationPort(ABC):
    @abstractmethod
    def is_clean(self, text: str) -> bool: ...
