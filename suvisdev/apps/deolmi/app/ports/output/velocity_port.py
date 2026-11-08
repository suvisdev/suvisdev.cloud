from __future__ import annotations

from abc import ABC, abstractmethod


class VelocityPort(ABC):
    @abstractmethod
    def record(self, key: str) -> int:
        """요청 1건을 기록하고 창 안의 최근 요청 수(이번 것 포함)를 돌려준다."""
