from __future__ import annotations

from abc import ABC, abstractmethod


class RoseModelStrategy(ABC):
    """생존 예측 알고리즘 전략 포트 (Strategy 패턴) — titanic-algorithm.md TOP 10."""

    key: str

    @abstractmethod
    def fit(self, X: list[list[float]], y: list[int]) -> None:
        pass

    @abstractmethod
    def predict_proba(self, X: list[list[float]]) -> list[float]:
        """각 샘플의 생존(1) 확률을 반환."""
        pass
