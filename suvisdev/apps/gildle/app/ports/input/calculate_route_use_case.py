from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode


class CalculateDogFriendlyRouteUseCase(ABC):
    """모드별 가중치를 반영한 반려견 친화 경로 계산 입력 포트."""

    @abstractmethod
    def execute(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
    ) -> list[str]:
        ...
