"""차도 중심선 페널티 — 보행 그래프에 섞인 차도를 걷기 비용으로 밀어낸다(2026-10-01).

osmnx `network_type="walk"`는 차도(primary·secondary·tertiary·trunk·busway)의 **중심선**을
보도와 같은 비용으로 넣는다. 그래서 강남대로처럼 보도가 따로 그려진 길에서도 경로가 차도
한가운데를 지나고, 횡단보도가 아닌 곳에서 길을 건넜다(2026-09-30 제보). 간선에 OSM
`highway` 종류와 "옆에 보도형 간선이 그려져 있는지"(`sidewalk`, 배치 산정)를 싣고,
모든 가중치(선호·계절)가 이 배율을 한 번 곱한다. 배율은 항상 1 이상이므로 A* 휴리스틱
하한(min_multiplier)은 바뀌지 않는다.

- 보도가 따로 있는 차도: 보도를 쓰라는 뜻이라 크게(간선 등급별 ×2~×4).
- 보도가 그려지지 않은 차도: 그 선이 사실상 길의 유일한 표현이라 조금만(×1.3) —
  큰길보다 이면도로를 살짝 선호하되 끊지는 않는다.
"""

from __future__ import annotations

from gildle.domain.value_objects.route_edge import RouteEdge

# OSM highway 종류 → 보도가 따로 그려진 경우의 추가 비율(×(1+비율)).
CAR_ROAD_PENALTY: dict[str, float] = {
    "trunk": 3.0,
    "trunk_link": 3.0,
    "primary": 3.0,
    "primary_link": 3.0,
    "busway": 3.0,
    "secondary": 2.0,
    "secondary_link": 2.0,
    "tertiary": 1.0,
    "tertiary_link": 1.0,
}
_NO_SIDEWALK_PENALTY = 0.3


def is_car_road(highway: str | None) -> bool:
    return highway in CAR_ROAD_PENALTY


def road_penalty(edge: RouteEdge) -> float:
    """간선 걷기 비용 배율(≥ 1). 차도가 아니면 1."""
    rate = CAR_ROAD_PENALTY.get(edge.highway or "")
    if rate is None:
        return 1.0
    return 1.0 + (rate if edge.sidewalk else _NO_SIDEWALK_PENALTY)
