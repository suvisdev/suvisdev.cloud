from __future__ import annotations

from abc import ABC, abstractmethod


class VisitedStorePort(ABC):
    """키워드별 이미 수집한 URL 중복 방지. --no-dedup이면 이 포트를 아예 거치지 않는다."""

    @abstractmethod
    def is_visited(self, keyword: str, url: str) -> bool: ...

    @abstractmethod
    def mark(self, keyword: str, url: str) -> None: ...
