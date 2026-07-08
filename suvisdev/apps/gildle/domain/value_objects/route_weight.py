from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteWeight:
    """경로(간선) 가중치 값 객체.

    음수일 수 없으며, 감면·증가 연산은 자신을 바꾸지 않고 새 인스턴스를 반환한다.
    """

    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"가중치는 음수일 수 없습니다: {self.value}")

    def apply_discount(self, rate: float) -> RouteWeight:
        """rate(0~1) 비율만큼 감면한 새 가중치를 반환한다. 예: 0.3 → 30% 감면."""
        return RouteWeight(self.value * (1 - rate))

    def apply_penalty(self, rate: float) -> RouteWeight:
        """rate 비율만큼 증가한 새 가중치를 반환한다. 예: 5.0 → 500% 증가(6배)."""
        return RouteWeight(self.value * (1 + rate))
