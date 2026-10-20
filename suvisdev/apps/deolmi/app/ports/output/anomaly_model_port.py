from __future__ import annotations

from abc import ABC, abstractmethod


class AnomalyModelPort(ABC):
    """2겹 탐지 — '정상에서 얼마나 벗어났나'를 0~1로 돌려준다. CPU 연산이라 동기 메서드다."""

    @property
    @abstractmethod
    def source(self) -> str:
        """'bootstrap' 또는 'trained(n=..)'."""

    @abstractmethod
    def score(self, features: list[float]) -> float: ...
