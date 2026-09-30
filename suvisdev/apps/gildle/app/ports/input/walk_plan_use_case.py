from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

from gildle.app.dtos.walk_plan_dto import WalkPlanDto
from gildle.domain.services.walk_request import WalkRequest
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class WalkPlanUseCase(ABC):
    """자연어·폼 산책 요청을 이해하고(모델+검증) 시간·거리·선호에 맞는 경로를 추천한다."""

    @abstractmethod
    def understand(
        self,
        text: str | None,
        *,
        minutes: int | None,
        distance_km: float | None,
        preference: str | None,
        stops: list[str] | None,
        has_end: bool,
        preferences: list[str] | None = None,
    ) -> WalkRequest: ...

    @abstractmethod
    def plan(
        self,
        request: WalkRequest,
        edges: list[RouteEdge],
        start: str,
        end: str | None,
        *,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        elevation: Mapping[str, float] | None,
        nearest_node: Callable[[Coordinate], str | None],
    ) -> WalkPlanDto: ...
