from __future__ import annotations

from dataclasses import dataclass

from gildle.domain.value_objects.coordinate import Coordinate


@dataclass(frozen=True)
class RouteEdge:
    """보행로 그래프의 간선 값 객체.

    시작/끝 노드 식별자, 기본 거리(m), 간선 중간 좌표, 그리고 OSM `name`에서 온
    도로명(없을 수 있음)을 담는다. 가중치 규칙은 이 도로명·중간 좌표를 사용한다.
    `highway`는 OSM 도로 종류(primary·footway…), `sidewalk`는 차도 옆에 보도형 간선이
    따로 그려져 있는지(배치 산정, 2026-10-01) — 차도 중심선 페널티(road_penalty)가 쓴다.
    """

    from_node: str
    to_node: str
    base_distance_m: float
    midpoint: Coordinate
    road_name: str | None
    from_coord: Coordinate | None = None
    to_coord: Coordinate | None = None
    tree_score: float = 0.0
    hazard_score: float = 0.0
    dog_friendly_score: float = 0.0
    highway: str | None = None
    sidewalk: bool = False
