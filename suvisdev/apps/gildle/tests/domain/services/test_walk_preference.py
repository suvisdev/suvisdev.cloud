"""편한 길·언덕길 가중치와 누적 오르막(2026-09-28)."""

from __future__ import annotations

from gildle.domain.services.walk_preference import climb_m, edge_grade, make_weight
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
