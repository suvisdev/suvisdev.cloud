from __future__ import annotations

from gildle.app.ports.input.calculate_route_use_case import (
    CalculateDogFriendlyRouteUseCase,
)
from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode


class CalculateDogFriendlyRouteInteractor(CalculateDogFriendlyRouteUseCase):
    """반려견 친화 경로 계산 유스케이스.

    조회한 가로수 구간/위험구역을 RouteWeightCalculator(도메인 서비스)에 위임하는
    `weight_fn` 클로저를 만들고, RouteGraphPort에 넘겨 최단 경로를 구한다.

    NetworkX를 직접 import하지 않는다 — 그래프 구현은 RouteGraphPort 뒤에 숨는다(DIP).
    모든 의존성은 생성자 주입(Constructor Injection)이다.
    """

    def __init__(
        self,
        tree_repository: TreeSegmentRepository,
        hazard_repository: HazardZoneRepository,
        route_graph: RouteGraphPort,
        weight_calculator: RouteWeightCalculator,
    ) -> None:
        self._tree_repository = tree_repository
        self._hazard_repository = hazard_repository
        self._route_graph = route_graph
        self._weight_calculator = weight_calculator

    def execute(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
    ) -> list[str]:
        segments = self._tree_repository.find_all()
        hazards = self._hazard_repository.find_all()

        def weight_fn(edge: RouteEdge) -> float:
            return self._weight_calculator.calculate_edge_weight(
                edge, mode, segments, hazards
            ).value

        graph = self._route_graph.build_graph(edges)
        return self._route_graph.find_shortest_path(graph, start, end, weight_fn)
