from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

from gildle.app.dtos.loop_dto import LoopCandidateDto
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode


class PlanLoopRouteUseCase(ABC):
    """출발점으로 돌아오는 목표 거리 산책 루프 계획 입력 포트."""

    @abstractmethod
    def execute(
        self,
        edges: list[RouteEdge],
        start: str,
        target_m: float,
        mode: SeasonMode,
        nearest_node: Callable[[Coordinate], str | None],
        shade_lookup: Mapping[tuple[str, str], float] | None = None,
        limit: int = 3,
        weight_fn: Callable[[RouteEdge], float] | None = None,
        heuristic_scale: float | None = None,
    ) -> list[LoopCandidateDto]: ...
