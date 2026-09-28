from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

from gildle.app.dtos.route_option_dto import RouteOptionDto
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class RouteOptionsUseCase(ABC):
    """출발·도착 사이의 성격이 다른 경로 후보(빠른·그늘·푸른)와 고를 이유, 들렀다 가기."""

    @abstractmethod
    def plan(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        *,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        recommended_kind: str,
        elevation: Mapping[str, float] | None = None,
        extra_kinds: tuple[str, ...] = (),
    ) -> list[RouteOptionDto]: ...

    @abstractmethod
    def via(
        self,
        edges: list[RouteEdge],
        start: str,
        via_node: str,
        end: str,
        *,
        base_kind: str,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        via_name: str,
        via_point: Coordinate,
        elevation: Mapping[str, float] | None = None,
    ) -> RouteOptionDto | None: ...

    @abstractmethod
    def loops(
        self,
        edges: list[RouteEdge],
        start: str,
        *,
        target_m: float,
        max_m: float | None,
        preference: str,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        elevation: Mapping[str, float] | None,
        stop_categories: tuple[str, ...],
        nearest_node: Callable[[Coordinate], str | None],
        limit: int = 3,
    ) -> list[RouteOptionDto]: ...
