"""경로 후보(빠른·그늘·푸른) + 고를 이유 + 경로 곁 반려동물 장소(2026-09-28)."""

from __future__ import annotations

from tests.app.fakes import FakeHazardZoneRepository, FakeTreeSegmentRepository

from gildle.adapter.outbound.graph.dijkstra_route_graph_adapter import AStarRouteGraphAdapter
from gildle.app.ports.output.pet_place_port import PetPlacePort
from gildle.app.use_cases.calculate_route_interactor import CalculateDogFriendlyRouteInteractor
from gildle.app.use_cases.route_options_interactor import RouteOptionsInteractor
from gildle.domain.services.route_option_describer import RouteOptionMetrics, describe
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.pet_place import PetPlace
from gildle.domain.value_objects.route_edge import RouteEdge

# A(0,0) → D(0,0.004): 짧은 맨길 A-B-D, 조금 긴 숲길 A-C-D
_C = {
    "A": Coordinate(37.5000, 127.0000),
    "B": Coordinate(37.5000, 127.0020),
    "D": Coordinate(37.5000, 127.0040),
    "C": Coordinate(37.5020, 127.0020),
}


def _edge(a: str, b: str, dist: float, tree: float, road: str) -> RouteEdge:
    mid = Coordinate((_C[a].latitude + _C[b].latitude) / 2, (_C[a].longitude + _C[b].longitude) / 2)
    return RouteEdge(a, b, dist, mid, road, from_coord=_C[a], to_coord=_C[b], tree_score=tree)


EDGES = [
    _edge("A", "B", 180, 0.0, "대로"),
    _edge("B", "D", 180, 0.0, "대로"),
    _edge("A", "C", 200, 1.0, "숲길"),
    _edge("C", "D", 200, 1.0, "숲길"),
]


class _Places(PetPlacePort):
    def search_around(self, center: Coordinate, radius_m: int) -> list[PetPlace]:
        return [
            PetPlace(
                "1", "숲길동물병원", "동물병원", Coordinate(37.5021, 127.0020)
            ),  # C 옆(맨길에선 220m)
            PetPlace("2", "먼펫샵", "펫샵", Coordinate(37.5100, 127.0100)),  # 멀다
        ]


def _interactor() -> RouteOptionsInteractor:
    route = CalculateDogFriendlyRouteInteractor(
        tree_repository=FakeTreeSegmentRepository(),
        hazard_repository=FakeHazardZoneRepository(),
        route_graph=AStarRouteGraphAdapter(),
        weight_calculator=RouteWeightCalculator(),
    )
    return RouteOptionsInteractor(route=route, places=_Places())


def test_fast_and_green_options_with_reasons_and_nearby_places():
    opts = _interactor().plan(EDGES, "A", "D", shade_lookup=None, recommended_kind="green")
    kinds = [o.kind for o in opts]
    assert kinds == ["fast", "green"]
    fast, green = opts
    assert fast.path == ["A", "B", "D"] and green.path == ["A", "C", "D"]
    assert green.recommended and not fast.recommended
    assert green.extra_m == 40.0
    assert "가장 푸른 길" in green.reason and "숲길" in green.reason
    assert [p.name for p in green.places] == ["숲길동물병원"]  # 150m 밖 펫샵은 제외
    assert "동물병원 1곳" in green.reason
    assert fast.places == []


def test_same_path_keeps_recommended_kind():
    # 숲길은 수관 1.0이라 그늘 후보와 푸른 후보가 같은 길 → 하나만, 추천 종류 이름으로 남긴다
    opts = _interactor().plan(EDGES, "A", "D", shade_lookup={}, recommended_kind="shade")
    assert [o.kind for o in opts] == ["fast", "shade"]
    assert opts[1].recommended
    opts = _interactor().plan(EDGES, "A", "D", shade_lookup={}, recommended_kind="fast")
    assert opts[0].recommended and len(opts) == 2


def test_via_goes_through_place():
    opt = _interactor().via(
        EDGES,
        "A",
        "C",
        "D",
        base_kind="fast",
        shade_lookup=None,
        via_name="숲길동물병원",
        via_point=_C["C"],
    )
    assert opt is not None and opt.path == ["A", "C", "D"]
    assert opt.label == "숲길동물병원 들렀다 가기" and "『숲길동물병원』에 들렀다" in opt.reason


def test_describer_uses_numbers_only():
    m = RouteOptionMetrics(length_m=1500, shade_ratio=0.9, green_ratio=0.2, roads=("청계천로",))
    t = describe("shade", m, shortest_m=1200)
    assert t.reason.startswith("300m 더 걷지만 그늘이 90%")
    assert "청계천로" in t.reason and "약 21분" in t.highlights[0]


def test_describer_josa():
    m = RouteOptionMetrics(length_m=1000, shade_ratio=None, green_ratio=0.1, roads=("종로", "다동길"))
    assert "종로·다동길을 지나요" in describe("fast", m, 1000).reason
    m2 = RouteOptionMetrics(length_m=1000, shade_ratio=None, green_ratio=0.1, roads=("양화로",))
    assert "양화로를 지나요" in describe("fast", m2, 1000).reason

