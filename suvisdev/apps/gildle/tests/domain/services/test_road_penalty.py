"""차도 중심선 페널티(2026-10-01) — 보도가 따로 있는 차도는 비싸고, 선호·계절 가중치에 한 번만 곱힌다."""

from __future__ import annotations

from gildle.domain.services.road_penalty import is_car_road, road_penalty
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.services.walk_preference import make_combined_weight, make_weight
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode

_P = Coordinate(37.5, 127.0)
ALLEY = RouteEdge("a", "b", 100, _P, "골목길", highway="residential")
PRIMARY_SW = RouteEdge("a", "b", 100, _P, "강남대로", highway="primary", sidewalk=True)
PRIMARY_NO_SW = RouteEdge("a", "b", 100, _P, "국도", highway="primary", sidewalk=False)
TERTIARY_SW = RouteEdge("a", "b", 100, _P, "", highway="tertiary", sidewalk=True)
UNKNOWN = RouteEdge("a", "b", 100, _P, "")  # 옛 데이터(highway 없음)


def test_penalty_by_kind_and_sidewalk():
    assert road_penalty(ALLEY) == 1.0 and road_penalty(UNKNOWN) == 1.0
    assert road_penalty(PRIMARY_SW) == 4.0
    assert road_penalty(TERTIARY_SW) == 2.0
    assert road_penalty(PRIMARY_NO_SW) == 1.3  # 보도가 안 그려진 차도는 살짝만
    assert is_car_road("busway") and not is_car_road("footway") and not is_car_road(None)


def test_fast_weight_uses_penalty_and_floor_stays():
    fast, floor = make_weight("fast", shade_lookup=None, elevation=None)
    assert floor == 1.0 and fast(ALLEY) == 100 and fast(PRIMARY_SW) == 400


def test_combined_weight_applies_penalty_once():
    one, _ = make_weight("green", shade_lookup=None, elevation={})
    both, floor = make_combined_weight(("green", "flat"), shade_lookup=None, elevation={})
    # 수관 0·경사 0이라 선호 배율은 전부 1 → 차도 배율 4만 남아야 한다(16이면 두 번 곱힌 것)
    assert one(PRIMARY_SW) == 400 and both(PRIMARY_SW) == 400 and floor == 0.4


def test_season_weight_uses_penalty():
    calc = RouteWeightCalculator()
    assert calc.calculate_edge_weight(PRIMARY_SW, SeasonMode.WINTER_SAFETY, [], []).value == 400
    assert calc.calculate_edge_weight(ALLEY, SeasonMode.WINTER_SAFETY, [], []).value == 100
