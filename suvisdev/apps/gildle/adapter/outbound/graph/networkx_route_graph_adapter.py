from __future__ import annotations

from collections.abc import Callable
from typing import Any

import networkx as nx

from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.domain.value_objects.route_edge import RouteEdge


class NetworkXRouteGraphAdapter(RouteGraphPort):
    """RouteGraphPort의 NetworkX 구현체.

    비즈니스 규칙은 전혀 모른다 — 간선마다 주입된 `weight_fn`을 기계적으로 적용한 뒤
    networkx 최단경로(weight='weight')를 구할 뿐이다.
    """

    def build_graph(self, edges: list[RouteEdge]) -> nx.Graph:
        graph = nx.Graph()
        for edge in edges:
            # 도로명과 원본 RouteEdge를 간선 속성으로 보관 → weight_fn이 나중에 참조.
            graph.add_edge(
                edge.from_node,
                edge.to_node,
                route_edge=edge,
                road_name=edge.road_name,
            )
        return graph

    def find_shortest_path(
        self,
        graph: Any,
        start: str,
        end: str,
        weight_fn: Callable[[RouteEdge], float],
    ) -> list[str]:
        for _u, _v, data in graph.edges(data=True):
            data["weight"] = weight_fn(data["route_edge"])

        try:
            return list(nx.shortest_path(graph, source=start, target=end, weight="weight"))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
