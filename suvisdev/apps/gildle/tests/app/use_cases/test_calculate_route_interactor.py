from tests.app.fakes import (
    CapturingRouteGraphPort,
    FakeHazardZoneRepository,
    FakeTreeSegmentRepository,
)

from gildle.app.use_cases.calculate_route_interactor import (
    CalculateDogFriendlyRouteInteractor,
)
from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode
from gildle.domain.value_objects.tree_species import TreeSpecies


def _edge(road_name=None, base=100.0) -> RouteEdge:
    return RouteEdge(
        from_node="A",
        to_node="B",
        base_distance_m=base,
        midpoint=Coordinate(latitude=37.5, longitude=127.0),
        road_name=road_name,
    )


def _interactor(graph, segments=None, hazards=None):
    return CalculateDogFriendlyRouteInteractor(
        tree_repository=FakeTreeSegmentRepository(segments),
        hazard_repository=FakeHazardZoneRepository(hazards),
        route_graph=graph,
        weight_calculator=RouteWeightCalculator(),
    )


class TestCalculateRoute:
    def test_returns_path_from_graph_port(self):
        graph = CapturingRouteGraphPort(path=["A", "B", "C"])
        interactor = _interactor(graph)

        path = interactor.execute(
            edges=[_edge()], start="A", end="C", mode=SeasonMode.SPRING_AUTUMN
        )

        assert path == ["A", "B", "C"]
        assert graph.start == "A"
        assert graph.end == "C"

    def test_passes_edges_to_build_graph(self):
        graph = CapturingRouteGraphPort(path=["A"])
        edges = [_edge(road_name="여의대로"), _edge(road_name="국회대로")]
        interactor = _interactor(graph)

        interactor.execute(edges=edges, start="A", end="B", mode=SeasonMode.SPRING_AUTUMN)

        assert graph.built_edges == edges

    def test_weight_fn_applies_spring_discount_via_calculator(self):
        bonus_segment = TreeSegment(
            id=1,
            road_name="여의대로",
            start=Coordinate(latitude=37.5, longitude=127.0),
            end=Coordinate(latitude=37.5, longitude=127.0),
            species=TreeSpecies.CHERRY,
            quantity=10,
            managing_agency="구청",
        )
        graph = CapturingRouteGraphPort(path=["A", "B"])
        interactor = _interactor(graph, segments=[bonus_segment])

        interactor.execute(
            edges=[_edge(road_name="여의대로")],
            start="A",
            end="B",
            mode=SeasonMode.SPRING_AUTUMN,
        )

        # weight_fn 클로저가 RouteWeightCalculator에 위임 → 30% 감면된 float 반환.
        assert graph.weight_fn is not None
        assert graph.weight_fn(_edge(road_name="여의대로")) == 70.0

    def test_weight_fn_applies_winter_penalty_via_calculator(self):
        hazard = HazardZone(
            id=1,
            center=Coordinate(latitude=37.50005, longitude=127.0),  # ≈5.5m < 20m
            radius_meters=200.0,
            accident_count=3,
            description="결빙",
        )
        graph = CapturingRouteGraphPort(path=["A", "B"])
        interactor = _interactor(graph, hazards=[hazard])

        interactor.execute(
            edges=[_edge()], start="A", end="B", mode=SeasonMode.WINTER_SAFETY
        )

        assert graph.weight_fn is not None
        assert graph.weight_fn(_edge()) == 600.0  # 500% 증가
