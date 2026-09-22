"""자체 다익스트라·A* 어댑터 — networkx 어댑터와 같은 계약을 지키는지."""

from __future__ import annotations

import random

from gildle.adapter.outbound.graph.dijkstra_route_graph_adapter import (
    AStarRouteGraphAdapter,
    DijkstraRouteGraphAdapter,
)
from gildle.adapter.outbound.graph.networkx_route_graph_adapter import (
    NetworkXRouteGraphAdapter,
)
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

_MID = Coordinate(latitude=37.5, longitude=127.0)


def _edge(u, v, road_name, base=100.0) -> RouteEdge:
    return RouteEdge(
        from_node=u, to_node=v, base_distance_m=base, midpoint=_MID, road_name=road_name
    )


def _diamond_edges() -> list[RouteEdge]:
    return [
        _edge("A", "B", "벚꽃길"),
        _edge("B", "D", "벚꽃길"),
        _edge("A", "C", "일반로"),
        _edge("C", "D", "일반로"),
    ]


def _grid_edges(n: int, seed: int = 7) -> list[RouteEdge]:
    """n×n 격자(간격 100m, 좌표 있음). 간선 길이는 80~140m로 흔든다."""
    rng = random.Random(seed)
    lat0, lng0 = 37.50, 127.00

    def coord(r: int, c: int) -> Coordinate:
        return Coordinate(latitude=lat0 + r * 0.0009, longitude=lng0 + c * 0.00113)

    edges: list[RouteEdge] = []
    for r in range(n):
        for c in range(n):
            for r2, c2 in ((r, c + 1), (r + 1, c)):
                if r2 >= n or c2 >= n:
                    continue
                a, b = coord(r, c), coord(r2, c2)
                edges.append(
                    RouteEdge(
                        from_node=f"{r}_{c}",
                        to_node=f"{r2}_{c2}",
                        base_distance_m=rng.uniform(80, 140),
                        midpoint=Coordinate(
                            latitude=(a.latitude + b.latitude) / 2,
                            longitude=(a.longitude + b.longitude) / 2,
                        ),
                        road_name=None,
                        from_coord=a,
                        to_coord=b,
                    )
                )
    return edges


def _cost(edges: list[RouteEdge], path: list[str], weight_fn) -> float:
    lookup = {}
    for e in edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e
    return sum(weight_fn(lookup[(path[i], path[i + 1])]) for i in range(len(path) - 1))


class TestDijkstraContract:
    def test_prefers_cheap_weight_fn(self):
        adapter = DijkstraRouteGraphAdapter()
        graph = adapter.build_graph(_diamond_edges())
        path = adapter.find_shortest_path(
            graph, "A", "D", lambda e: 1.0 if e.road_name == "벚꽃길" else 1000.0
        )
        assert path == ["A", "B", "D"]

    def test_no_path_and_unknown_node(self):
        adapter = DijkstraRouteGraphAdapter()
        graph = adapter.build_graph([_edge("A", "B", "x")])
        assert adapter.find_shortest_path(graph, "A", "Z", lambda e: 1.0) == []
        graph2 = adapter.build_graph([_edge("A", "B", "x"), _edge("C", "D", "y")])
        assert adapter.find_shortest_path(graph2, "A", "D", lambda e: 1.0) == []

    def test_start_equals_end(self):
        adapter = DijkstraRouteGraphAdapter()
        graph = adapter.build_graph(_diamond_edges())
        assert adapter.find_shortest_path(graph, "A", "A", lambda e: 1.0) == ["A"]

    def test_graph_cache_by_list_identity(self):
        adapter = DijkstraRouteGraphAdapter()
        edges = _diamond_edges()
        assert adapter.build_graph(edges) is adapter.build_graph(edges)
        assert adapter.build_graph(list(edges)) is not adapter.build_graph(edges)


class TestEquivalenceWithNetworkX:
    """무작위 격자·무작위 가중치에서 세 구현의 경로 비용이 같아야 한다."""

    def test_costs_match_on_random_grids(self):
        for seed in range(5):
            edges = _grid_edges(12, seed=seed)
            rng = random.Random(100 + seed)
            # 거리의 0.7~5배 — RouteWeightCalculator가 낼 수 있는 범위와 같다.
            factor = {id(e): rng.uniform(0.7, 5.0) for e in edges}

            def weight_fn(e: RouteEdge, factor: dict[int, float] = factor) -> float:
                return e.base_distance_m * factor[id(e)]

            nodes = sorted({e.from_node for e in edges} | {e.to_node for e in edges})
            pairs = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(20)]
            nx_adapter = NetworkXRouteGraphAdapter()
            dj = DijkstraRouteGraphAdapter()
            astar = AStarRouteGraphAdapter()
            g_nx, g_dj, g_as = (
                nx_adapter.build_graph(edges),
                dj.build_graph(edges),
                astar.build_graph(edges),
            )
            for s, t in pairs:
                ref = _cost(edges, nx_adapter.find_shortest_path(g_nx, s, t, weight_fn), weight_fn)
                got_dj = _cost(edges, dj.find_shortest_path(g_dj, s, t, weight_fn), weight_fn)
                got_as = _cost(edges, astar.find_shortest_path(g_as, s, t, weight_fn), weight_fn)
                assert abs(ref - got_dj) < 1e-6, (seed, s, t)
                assert abs(ref - got_as) < 1e-6, (seed, s, t)

    def test_astar_visits_fewer_nodes_than_dijkstra(self):
        edges = _grid_edges(30)
        dj, astar = DijkstraRouteGraphAdapter(), AStarRouteGraphAdapter()
        g_dj, g_as = dj.build_graph(edges), astar.build_graph(edges)
        weight_fn = lambda e: e.base_distance_m  # noqa: E731
        # build_graph 캐시는 edges 리스트 단위로 어댑터 인스턴스 간 공유된다 —
        # last_visited는 각 탐색 직후에 읽어야 한다.
        # 목적지를 격자 안쪽에 둔다 — 반대편 모서리면 다익스트라도 A*도 전 노드를
        # 훑어 차이가 안 난다(둘 다 900). 안쪽 목적지에선 다익스트라가 반경 안 전부를,
        # A*는 목적지 방향만 확장한다.
        dj.find_shortest_path(g_dj, "15_15", "21_21", weight_fn)
        dj_visited = g_dj.last_visited
        astar.find_shortest_path(g_as, "15_15", "21_21", weight_fn)
        astar_visited = g_as.last_visited
        assert 0 < astar_visited < dj_visited * 0.6, (astar_visited, dj_visited)

    def test_astar_falls_back_to_dijkstra_without_coords(self):
        # 좌표 없는 다이아몬드 — 휴리스틱 0으로 동작해야 하고 결과는 같다.
        astar = AStarRouteGraphAdapter()
        graph = astar.build_graph(_diamond_edges())
        assert graph.all_nodes_have_coords is False
        path = astar.find_shortest_path(
            graph, "A", "D", lambda e: 1.0 if e.road_name == "일반로" else 1000.0
        )
        assert path == ["A", "C", "D"]
