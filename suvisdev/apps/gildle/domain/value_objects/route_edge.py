from __future__ import annotations

from dataclasses import dataclass

from gildle.domain.value_objects.coordinate import Coordinate


@dataclass(frozen=True)
class RouteEdge:
    """보행로 그래프의 간선 값 객체.

    시작/끝 노드 식별자, 기본 거리(m), 간선 중간 좌표, 그리고 OSM `name`에서 온
    도로명(없을 수 있음)을 담는다. 가중치 규칙은 이 도로명·중간 좌표를 사용한다.
    """

    from_node: str
    to_node: str
    base_distance_m: float
    midpoint: Coordinate
    road_name: str | None
