from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

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
        shade_lookup: Mapping[tuple[str, str], float] | None = None,
    ) -> list[str]: ...

    @abstractmethod
    def execute_bounded(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
        shade_lookup: Mapping[tuple[str, str], float] | None = None,
        max_detour_ratio: float = 0.3,
    ) -> list[str]:
        """모드 선호를 최대한 반영하되 길이가 최단거리의 (1+max_detour_ratio)배를 넘지 않는 경로."""
        ...

    @abstractmethod
    def execute_time_aware(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
        shade_by_slot: Mapping[int, Mapping[tuple[str, str], float]],
        slot_of_elapsed: Callable[[float], int],
    ) -> list[str]:
        """걸은 거리(m)→슬롯 함수로 간선마다 그 시각의 그늘을 적용하는 여름 경로."""
        ...

    def execute_shortest(self, edges: list[RouteEdge], start: str, end: str) -> list[str]:
        """순수 거리 최단 경로(모드 선호 없음) — 경로 후보의 '빠른 길'. 기본 구현은 미지원."""
        raise NotImplementedError

    def execute_weighted(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        weight_fn: Callable[[RouteEdge], float],
        min_multiplier: float,
        max_detour_ratio: float = 0.5,
    ) -> list[str]:
        """임의 가중치(산책 선호)로, 길이가 최단의 (1+max_detour_ratio)배를 넘지 않는 경로."""
        raise NotImplementedError
