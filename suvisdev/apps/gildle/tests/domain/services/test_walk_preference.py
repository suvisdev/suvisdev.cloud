"""편한 길·언덕길 가중치와 누적 오르막(2026-09-28)."""

from __future__ import annotations

from gildle.domain.services.walk_preference import (
    climb_m,
    combined_label,
    edge_grade,
    make_combined_weight,
    make_weight,
    normalize_preferences,
)
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

_P = Coordinate(37.5, 127.0)
FLAT = RouteEdge("a", "b", 100, _P, "", tree_score=0.0)
STEEP = RouteEdge("b", "c", 100, _P, "", tree_score=0.0)
ELEV = {"a": 10.0, "b": 10.0, "c": 20.0}


def test_grade_and_weights():
    assert edge_grade(FLAT, ELEV) == 0 and edge_grade(STEEP, ELEV) == 0.1
    assert edge_grade(STEEP, None) == 0
    flat, floor = make_weight("flat", shade_lookup=None, elevation=ELEV)
    assert floor == 1.0 and flat(STEEP) > flat(FLAT) == 100
    hilly, floor = make_weight("hilly", shade_lookup=None, elevation=ELEV)
    assert hilly(STEEP) < hilly(FLAT) == 100 and hilly(STEEP) >= 100 * floor


def test_climb_counts_only_uphill():
    assert climb_m(["a", "b", "c"], ELEV) == 10.0
    assert climb_m(["c", "b", "a"], ELEV) == 0.0
    assert climb_m(["a", "b"], None) is None


def test_normalize_preferences_drops_meaningless_combinations():
    assert normalize_preferences(["flat", "shade", "flat"]) == ("flat", "shade")
    # 빠른 길은 다른 성격과 같이 고르면 의미가 없다
    assert normalize_preferences(["fast", "green"]) == ("green",)
    assert normalize_preferences(["fast"]) == ("fast",)
    # 편한 길과 언덕길은 반대 — 먼저 고른 쪽만
    assert normalize_preferences(["hilly", "shade", "flat"]) == ("hilly", "shade")
    assert normalize_preferences(["없는값"]) == ()


def test_combined_weight_applies_both_penalties():
    sunny_steep = RouteEdge("b", "c", 100, _P, "", tree_score=0.0)
    shade = {("a", "b"): 1.0, ("b", "c"): 0.0}
    flat, _ = make_weight("flat", shade_lookup=shade, elevation=ELEV)
    shady, _ = make_weight("shade", shade_lookup=shade, elevation=ELEV)
    both, floor = make_combined_weight(["flat", "shade"], shade_lookup=shade, elevation=ELEV)
    # 평지·그늘 구간은 거리 그대로, 경사·햇빛 구간은 두 페널티가 곱해진다
    assert both(FLAT) == 100
    assert both(sunny_steep) == flat(sunny_steep) * shady(sunny_steep) / 100
    assert both(sunny_steep) > max(flat(sunny_steep), shady(sunny_steep))
    assert floor == 1.0
    # 감면이 있는 선호가 섞이면 하한도 곱으로 내려간다(A* 휴리스틱 안전)
    _, green_floor = make_combined_weight(["green", "shade"], shade_lookup=shade, elevation=ELEV)
    assert green_floor == 0.4
    assert combined_label(("flat", "shade")) == "편한 길 + 그늘 많은 길"
