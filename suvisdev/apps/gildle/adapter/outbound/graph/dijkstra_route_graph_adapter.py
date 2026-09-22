"""RouteGraphPort의 자체 구현 — 힙 다익스트라 + 선택적 A*(하버사인 휴리스틱).

networkx 대체(2026-09-22, `_docs/GILDLE_ROUTING_ALGORITHM.md` §1-①②). 포트
시그니처를 바꾸지 않았으므로 유스케이스·라우터·기존 테스트는 그대로다.

- 간선 가중치는 방문할 때만 `weight_fn`으로 평가한다(전 간선 사전 계산 금지 —
  23만 간선 그래프를 요청마다 다시 재지 않는 현 설계 유지).
- A*의 휴리스틱은 "도착점까지 직선거리 × heuristic_scale". 봄가을 모드가 간선
  가중치를 거리의 0.7배까지 감면하므로 scale은 모드 최소 배율(0.7) 이하여야
  admissible하다 — 기본값을 0.7로 두면 모든 모드에서 최적 경로가 보장된다.
  좌표가 없는 노드(from_coord/to_coord None)가 하나라도 있으면 휴리스틱 0(=다익스트라).
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass, field

from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

# 봄가을 보너스 감면(0.7)이 모드 전체의 최소 배율 — RouteWeightCalculator와 짝.
DEFAULT_HEURISTIC_SCALE = 0.7


@dataclass
class AdjacencyGraph:
    """간선 리스트에서 만든 인접 리스트. 노드 좌표는 A* 휴리스틱용."""

    adjacency: dict[str, list[tuple[str, RouteEdge]]] = field(default_factory=dict)
    coords: dict[str, Coordinate] = field(default_factory=dict)
    all_nodes_have_coords: bool = True
    # 마지막 탐색 통계 — 알고리즘 비교(하네스 §3-②)용. 동시 요청 간 공유되므로
    # 진단 값으로만 쓴다.
    last_visited: int = 0


_graph_cache: tuple[list[RouteEdge], AdjacencyGraph] | None = None


def _build_adjacency(edges: list[RouteEdge]) -> AdjacencyGraph:
    g = AdjacencyGraph()
    for e in edges:
        g.adjacency.setdefault(e.from_node, []).append((e.to_node, e))
        g.adjacency.setdefault(e.to_node, []).append((e.from_node, e))
        for node, coord in ((e.from_node, e.from_coord), (e.to_node, e.to_coord)):
            if coord is None:
                g.all_nodes_have_coords = False
            elif node not in g.coords:
                g.coords[node] = coord
    return g


class DijkstraRouteGraphAdapter(RouteGraphPort):
    """힙 다익스트라. `heuristic_scale > 0`이고 노드 좌표가 전부 있으면 A*로 동작한다."""

    def __init__(self, heuristic_scale: float = 0.0) -> None:
        if heuristic_scale < 0:
            raise ValueError("heuristic_scale은 0 이상이어야 합니다")
        self._scale = heuristic_scale

    def build_graph(self, edges: list[RouteEdge]) -> AdjacencyGraph:
        global _graph_cache  # noqa: PLW0603
        if _graph_cache is not None and _graph_cache[0] is edges:
            return _graph_cache[1]
        graph = _build_adjacency(edges)
        _graph_cache = (edges, graph)
        return graph

    def find_shortest_path(
        self,
        graph: AdjacencyGraph,
        start: str,
        end: str,
        weight_fn: Callable[[RouteEdge], float],
    ) -> list[str]:
        if start not in graph.adjacency or end not in graph.adjacency:
            return []
        use_astar = self._scale > 0 and graph.all_nodes_have_coords
        goal = graph.coords.get(end)

        def h(node: str) -> float:
            if not use_astar or goal is None:
                return 0.0
            return graph.coords[node].distance_to(goal) * self._scale

        dist: dict[str, float] = {start: 0.0}
        prev: dict[str, str] = {}
        heap: list[tuple[float, float, str]] = [(h(start), 0.0, start)]
        visited = 0
        while heap:
            _f, d, u = heapq.heappop(heap)
            if d > dist.get(u, math.inf):
                continue  # 지연 삭제된 낡은 항목
            visited += 1
            if u == end:
                break
            for v, edge in graph.adjacency[u]:
                nd = d + weight_fn(edge)
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd + h(v), nd, v))
        graph.last_visited = visited
        if end not in dist:
            return []
        path = [end]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path

    def find_shortest_path_time_dependent(
        self,
        graph: AdjacencyGraph,
        start: str,
        end: str,
        weight_fn_t: Callable[[RouteEdge, float], float],
    ) -> list[str]:
        """비용 기준 라벨 세팅 + 노드별 누적 거리(m) 동반. 걷는 시간이 흐르면 뒤
        간선의 그늘이 바뀌므로 weight_fn_t(edge, 도달까지 걸은 m)로 평가한다.
        FIFO(늦게 출발하면 늦게 도착)가 성립하는 도보 그래프에서는 다익스트라가 그대로
        최적이다."""
        if start not in graph.adjacency or end not in graph.adjacency:
            return []
        use_astar = self._scale > 0 and graph.all_nodes_have_coords
        goal = graph.coords.get(end)

        def h(node: str) -> float:
            if not use_astar or goal is None:
                return 0.0
            return graph.coords[node].distance_to(goal) * self._scale

        dist: dict[str, float] = {start: 0.0}
        meters: dict[str, float] = {start: 0.0}
        prev: dict[str, str] = {}
        heap: list[tuple[float, float, str]] = [(h(start), 0.0, start)]
        visited = 0
        while heap:
            _f, d, u = heapq.heappop(heap)
            if d > dist.get(u, math.inf):
                continue
            visited += 1
            if u == end:
                break
            walked = meters[u]
            for v, edge in graph.adjacency[u]:
                nd = d + weight_fn_t(edge, walked)
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    meters[v] = walked + edge.base_distance_m
                    prev[v] = u
                    heapq.heappush(heap, (nd + h(v), nd, v))
        graph.last_visited = visited
        if end not in dist:
            return []
        path = [end]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path


class AStarRouteGraphAdapter(DijkstraRouteGraphAdapter):
    """기본 휴리스틱(0.7)을 켠 다익스트라 — 서비스 DI에서 쓰는 이름."""

    def __init__(self, heuristic_scale: float = DEFAULT_HEURISTIC_SCALE) -> None:
        super().__init__(heuristic_scale=heuristic_scale)
