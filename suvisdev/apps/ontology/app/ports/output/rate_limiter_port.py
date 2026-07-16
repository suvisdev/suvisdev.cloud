from __future__ import annotations

from abc import ABC, abstractmethod


class RateLimiterPort(ABC):
    @abstractmethod
    def acquire(self, domain: str) -> None:
        """domain에 대한 다음 요청이 허용될 때까지 블로킹한다."""
