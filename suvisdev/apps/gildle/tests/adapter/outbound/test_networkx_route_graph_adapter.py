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
    # A ─ B ─ D  (벚꽃길)   /   A ─ C ─ D  (일반로)  두 갈래.
    return [
        _edge("A", "B", "벚꽃길"),
        _edge("B", "D", "벚꽃길"),
        _edge("A", "C", "일반로"),
        _edge("C", "D", "일반로"),
    ]


class TestNetworkXRouteGraphAdapter:
    def test_weight_fn_favoring_cherry_route_picks_abd(self):
        adapter = NetworkXRouteGraphAdapter()
        graph = adapter.build_graph(_diamond_edges())

        # 벚꽃길은 싸고, 일반로는 비싸게 → A-B-D 선택.
        def weight_fn(edge: RouteEdge) -> float:
            return 1.0 if edge.road_name == "벚꽃길" else 1000.0

        path = adapter.find_shortest_path(graph, "A", "D", weight_fn)

        assert path == ["A", "B", "D"]

    def test_weight_fn_favoring_normal_route_picks_acd(self):
        adapter = NetworkXRouteGraphAdapter()
        graph = adapter.build_graph(_diamond_edges())

        # 반대로 일반로를 싸게 → A-C-D 선택. (어댑터는 규칙을 모르고 weight_fn만 적용)
        def weight_fn(edge: RouteEdge) -> float:
            return 1.0 if edge.road_name == "일반로" else 1000.0

        path = adapter.find_shortest_path(graph, "A", "D", weight_fn)

        assert path == ["A", "C", "D"]

    def test_no_path_returns_empty_list(self):
        adapter = NetworkXRouteGraphAdapter()
        graph = adapter.build_graph([_edge("A", "B", "벚꽃길")])

        path = adapter.find_shortest_path(graph, "A", "Z", lambda e: e.base_distance_m)

        assert path == []
