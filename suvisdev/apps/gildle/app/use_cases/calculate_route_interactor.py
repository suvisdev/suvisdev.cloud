from __future__ import annotations

from collections.abc import Callable, Mapping

from gildle.app.ports.input.calculate_route_use_case import (
    CalculateDogFriendlyRouteUseCase,
)
from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode

ShadeLookup = Mapping[tuple[str, str], float]

# 제약 최단경로의 이분탐색 반복 — 8회면 t 해상도 1/256, 탐색 8번.
_BOUNDED_ITERATIONS = 8


def shade_of(edge: RouteEdge, lookup: ShadeLookup | None) -> float | None:
    if lookup is None:
        return None
    shade = lookup.get((edge.from_node, edge.to_node))
    if shade is None:
        shade = lookup.get((edge.to_node, edge.from_node))
    return shade


def build_weight_fn(
    calculator: RouteWeightCalculator,
    mode: SeasonMode,
    segments: list[TreeSegment],
    hazards: list[HazardZone],
    shade_lookup: ShadeLookup | None,
) -> Callable[[RouteEdge], float]:
    """모드 규칙을 닫아 넣은 간선 가중치 함수 — 경로·루프 유스케이스가 공유한다."""

    def weight_fn(edge: RouteEdge) -> float:
        return calculator.calculate_edge_weight(
            edge, mode, segments, hazards, shade_fraction=shade_of(edge, shade_lookup)
        ).value

    return weight_fn


def path_length_m(edges: list[RouteEdge], path: list[str]) -> float:
    lookup: dict[tuple[str, str], RouteEdge] = {}
    for e in edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e
    return sum(lookup[(path[i], path[i + 1])].base_distance_m for i in range(len(path) - 1))


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
        shade_lookup: ShadeLookup | None = None,
    ) -> list[str]:
        segments = self._tree_repository.find_all()
        hazards = self._hazard_repository.find_all()
        weight_fn = build_weight_fn(self._weight_calculator, mode, segments, hazards, shade_lookup)
        graph = self._route_graph.build_graph(edges)
        return self._route_graph.find_shortest_path(graph, start, end, weight_fn)

    def execute_bounded(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
        shade_lookup: ShadeLookup | None = None,
        max_detour_ratio: float = 0.3,
    ) -> list[str]:
        """길이 상한 아래에서 모드 선호를 최대로 — 라그랑주 완화 + 이분탐색.

        여름 규칙(햇빛 ×5)은 그늘을 위해 길이 5배까지 돌 수 있다. 가중치를
        `거리 + t·(모드가중치 − 거리)`로 두고(t=1이 현행), 길이가 최단거리의
        (1+max_detour_ratio)배 이하가 되는 가장 큰 t를 이분탐색한다.
        `_docs/GILDLE_ROUTING_ALGORITHM.md` §1-④.
        """
        segments = self._tree_repository.find_all()
        hazards = self._hazard_repository.find_all()
        full = build_weight_fn(self._weight_calculator, mode, segments, hazards, shade_lookup)
        graph = self._route_graph.build_graph(edges)

        shortest = self._route_graph.find_shortest_path(
            graph, start, end, lambda e: e.base_distance_m
        )
        if not shortest:
            return []
        limit = path_length_m(edges, shortest) * (1.0 + max_detour_ratio)

        def scaled(t: float) -> Callable[[RouteEdge], float]:
            return lambda e: e.base_distance_m + t * (full(e) - e.base_distance_m)

        preferred = self._route_graph.find_shortest_path(graph, start, end, full)
        if path_length_m(edges, preferred) <= limit + 1e-6:
            return preferred
        lo, hi, best = 0.0, 1.0, shortest
        for _ in range(_BOUNDED_ITERATIONS):
            mid = (lo + hi) / 2
            candidate = self._route_graph.find_shortest_path(graph, start, end, scaled(mid))
            if candidate and path_length_m(edges, candidate) <= limit + 1e-6:
                best, lo = candidate, mid
            else:
                hi = mid
        return best

    def execute_time_aware(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
        shade_by_slot: Mapping[int, ShadeLookup],
        slot_of_elapsed: Callable[[float], int],
    ) -> list[str]:
        """걸은 거리→슬롯으로 간선마다 그 시각의 그늘을 쓴다(§1-③)."""
        segments = self._tree_repository.find_all()
        hazards = self._hazard_repository.find_all()
        slots = sorted(shade_by_slot)

        def lookup_for(elapsed_m: float) -> ShadeLookup | None:
            if not slots:
                return None
            slot = min(max(slot_of_elapsed(elapsed_m), slots[0]), slots[-1])
            return shade_by_slot.get(slot)

        def weight_fn_t(edge: RouteEdge, elapsed_m: float) -> float:
            return self._weight_calculator.calculate_edge_weight(
                edge, mode, segments, hazards, shade_fraction=shade_of(edge, lookup_for(elapsed_m))
            ).value

        graph = self._route_graph.build_graph(edges)
        return self._route_graph.find_shortest_path_time_dependent(graph, start, end, weight_fn_t)
