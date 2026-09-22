"""산책 루프 계획 — 출발점으로 돌아오는 목표 거리 경로.

최단경로 엔진은 "집에서 집"을 만들 수 없다(항상 0m). 표준 기법으로 우회한다
(`_docs/GILDLE_ROUTING_ALGORITHM.md` §1-⑤):

  방위각 θ를 30° 간격으로 돌며, s에서 θ 방향 D/3 지점과 θ+60° 방향 D/3 지점의
  최근접 노드 m1·m2를 잡아 s→m1→m2→s 세 변을 모드 가중치로 잇는다(정삼각형이면
  세 변이 각 D/3). 2·3번째 변 탐색에서는 이미 지난 간선을 ×3으로 무겁게 해
  왔던 길을 되밟지 않게 한다. 후보는 목표 거리 오차·되밟기 비율·(여름) 그늘로
  점수를 매겨 상위 limit개를 돌려준다.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from gildle.app.dtos.loop_dto import LoopCandidateDto
from gildle.app.ports.input.plan_loop_use_case import PlanLoopRouteUseCase
from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.app.use_cases.calculate_route_interactor import (
    ShadeLookup,
    build_weight_fn,
    shade_of,
)
from gildle.domain.services.geo import offset
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode

_BEARING_STEP_DEG = 30
_REUSE_PENALTY = 3.0  # 이미 지난 간선 재사용 가중치 배율
_LENGTH_TOLERANCE = 0.35  # 목표 거리 ±35% 밖이면 버린다


def _edge_key(e: RouteEdge) -> tuple[str, str]:
    return (e.from_node, e.to_node) if e.from_node < e.to_node else (e.to_node, e.from_node)


class PlanLoopRouteInteractor(PlanLoopRouteUseCase):
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
        target_m: float,
        mode: SeasonMode,
        nearest_node: Callable[[Coordinate], str | None],
        shade_lookup: ShadeLookup | None = None,
        limit: int = 3,
    ) -> list[LoopCandidateDto]:
        graph = self._route_graph.build_graph(edges)
        edge_map: dict[tuple[str, str], RouteEdge] = {_edge_key(e): e for e in edges}
        origin = self._node_coord(edges, start)
        if origin is None:
            return []
        segments = self._tree_repository.find_all()
        hazards = self._hazard_repository.find_all()
        base = build_weight_fn(self._weight_calculator, mode, segments, hazards, shade_lookup)
        leg = target_m / 3.0

        candidates: list[tuple[float, LoopCandidateDto]] = []
        for bearing in range(0, 360, _BEARING_STEP_DEG):
            m1 = nearest_node(offset(origin, bearing, leg))
            m2 = nearest_node(offset(origin, bearing + 60, leg))
            if not m1 or not m2 or len({start, m1, m2}) < 3:
                continue
            used: set[tuple[str, str]] = set()

            def penalized(e: RouteEdge, used: set[tuple[str, str]] = used) -> float:
                w = base(e)
                return w * _REUSE_PENALTY if _edge_key(e) in used else w

            path: list[str] = [start]
            ok = True
            for a, b in ((start, m1), (m1, m2), (m2, start)):
                seg = self._route_graph.find_shortest_path(graph, a, b, penalized)
                if len(seg) < 2:
                    ok = False
                    break
                for i in range(len(seg) - 1):
                    a_, b_ = seg[i], seg[i + 1]
                    used.add((a_, b_) if a_ < b_ else (b_, a_))
                path.extend(seg[1:])
            if not ok:
                continue
            dto = self._describe(edge_map, path, mode, shade_lookup, bearing)
            if abs(dto.length_m - target_m) > _LENGTH_TOLERANCE * target_m:
                continue
            score = abs(dto.length_m - target_m) / target_m + 0.5 * dto.overlap_ratio
            if dto.shade_ratio is not None:
                score -= 0.3 * dto.shade_ratio
            candidates.append((score, dto))

        candidates.sort(key=lambda c: c[0])
        return [dto for _, dto in candidates[:limit]]

    @staticmethod
    def _node_coord(edges: list[RouteEdge], node: str) -> Coordinate | None:
        for e in edges:
            if e.from_node == node and e.from_coord is not None:
                return e.from_coord
            if e.to_node == node and e.to_coord is not None:
                return e.to_coord
        return None

    @staticmethod
    def _describe(
        edge_map: Mapping[tuple[str, str], RouteEdge],
        path: list[str],
        mode: SeasonMode,
        shade_lookup: ShadeLookup | None,
        bearing: int,
    ) -> LoopCandidateDto:
        total = shaded = dup = 0.0
        seen: set[tuple[str, str]] = set()
        for i in range(len(path) - 1):
            key = (path[i], path[i + 1]) if path[i] < path[i + 1] else (path[i + 1], path[i])
            e = edge_map[key]
            total += e.base_distance_m
            if key in seen:
                dup += e.base_distance_m
            seen.add(key)
            if mode is SeasonMode.SUMMER_SHADE:
                shaded += e.base_distance_m * (shade_of(e, shade_lookup) or 0.0)
        return LoopCandidateDto(
            path=path,
            length_m=round(total, 1),
            overlap_ratio=round(dup / total, 3) if total else 0.0,
            shade_ratio=round(shaded / total, 3)
            if (mode is SeasonMode.SUMMER_SHADE and total)
            else None,
            bearing_deg=bearing,
        )
