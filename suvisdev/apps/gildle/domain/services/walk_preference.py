"""산책 선호별 간선 가중치 — 빠른 길·그늘·푸른 길·편한 길·언덕길(2026-09-28).

계절 모드(SeasonMode)와 별개로, 사용자가 고른 "길의 성격"을 가중치로 옮긴다. 모두 순수 함수이고
A* 휴리스틱(직선거리 × 배율)이 안전하도록 가중치/거리의 하한(min_multiplier)을 함께 돌려준다.
경사는 SRTM 교차점 고도(node_elevation.json)에서 |Δh| / max(길이, 30m) — 30m 해상도 잡음 완화.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from gildle.domain.value_objects.route_edge import RouteEdge

PREFERENCES = ("fast", "shade", "green", "flat", "hilly")
PREFERENCE_LABEL = {
    "fast": "빠른 길",
    "shade": "그늘 많은 길",
    "green": "푸른 길",
    "flat": "편한 길",
    "hilly": "언덕길",
}

_SUN_PENALTY = 4.0  # 완전 햇빛 ×5 (RouteWeightCalculator 그늘 규칙과 같은 값)
_GREEN_DISCOUNT = 0.6  # 수관 1.0이면 60% 감면
_FLAT_PENALTY = 10.0  # 경사 5% → ×1.5, 10% → ×2
_HILL_DISCOUNT = 0.6  # 경사 8% 이상이면 60% 감면
_HILL_FULL_GRADE = 0.08
_MIN_RUN_M = 30.0

WeightFn = Callable[[RouteEdge], float]
ShadeLookup = Mapping[tuple[str, str], float]
Elevation = Mapping[str, float]


def edge_grade(edge: RouteEdge, elevation: Elevation | None) -> float:
    """구간 경사(0~). 고도가 없으면 0."""
    if not elevation:
        return 0.0
    h1 = elevation.get(edge.from_node)
    h2 = elevation.get(edge.to_node)
    if h1 is None or h2 is None:
        return 0.0
    return abs(h2 - h1) / max(edge.base_distance_m, _MIN_RUN_M)


def _shade(edge: RouteEdge, lookup: ShadeLookup | None) -> float:
    s = None
    if lookup is not None:
        s = lookup.get((edge.from_node, edge.to_node))
        if s is None:
            s = lookup.get((edge.to_node, edge.from_node))
    return max(0.0, min(1.0, max(s or 0.0, edge.tree_score)))


def make_weight(
    preference: str, *, shade_lookup: ShadeLookup | None, elevation: Elevation | None
) -> tuple[WeightFn, float]:
    """(간선 가중치 함수, 가중치/거리 하한). 모르는 선호는 빠른 길."""
    if preference == "shade":
        return (
            lambda e: e.base_distance_m * (1 + _SUN_PENALTY * (1 - _shade(e, shade_lookup)))
        ), 1.0
    if preference == "green":
        return (
            lambda e: e.base_distance_m * (1 - _GREEN_DISCOUNT * max(0.0, min(1.0, e.tree_score)))
        ), 1 - _GREEN_DISCOUNT
    if preference == "flat":
        return (lambda e: e.base_distance_m * (1 + _FLAT_PENALTY * edge_grade(e, elevation))), 1.0
    if preference == "hilly":
        return (
            lambda e: (
                e.base_distance_m
                * (1 - _HILL_DISCOUNT * min(edge_grade(e, elevation) / _HILL_FULL_GRADE, 1.0))
            )
        ), 1 - _HILL_DISCOUNT
    return (lambda e: e.base_distance_m), 1.0


def climb_m(path: list[str], elevation: Elevation | None) -> float | None:
    """경로 진행 방향 누적 오르막(m). 고도 데이터가 없으면 None."""
    if not elevation or len(path) < 2:
        return None
    total = 0.0
    for a, b in zip(path, path[1:], strict=False):
        ha, hb = elevation.get(a), elevation.get(b)
        if ha is not None and hb is not None and hb > ha:
            total += hb - ha
    return round(total, 1)
