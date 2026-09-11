from __future__ import annotations

from collections.abc import Callable
from typing import Any

import networkx as nx

from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.domain.value_objects.route_edge import RouteEdge

# 그래프 토폴로지 캐시 — 라우터가 mtime 캐시로 같은 edges 리스트 객체를 재사용
# 하므로, 리스트 동일성(is)으로 재구축 여부를 판정한다(233k 간선 그래프를 요청
# 마다 다시 만들던 것 제거, 2026-09-11 리뷰). 키 리스트에 강한 참조를 함께
# 보관해 id 재사용 오판이 없다.
_graph_cache: tuple[list[RouteEdge], nx.Graph] | None = None


class NetworkXRouteGraphAdapter(RouteGraphPort):
    """RouteGraphPort의 NetworkX 구현체.

    비즈니스 규칙은 전혀 모른다 — 간선마다 주입된 `weight_fn`을 기계적으로 적용해
    networkx 최단경로를 구할 뿐이다.
    """

    def build_graph(self, edges: list[RouteEdge]) -> nx.Graph:
        global _graph_cache  # noqa: PLW0603
        if _graph_cache is not None and _graph_cache[0] is edges:
            return _graph_cache[1]
        graph = nx.Graph()
        for edge in edges:
            # 도로명과 원본 RouteEdge를 간선 속성으로 보관 → weight_fn이 나중에 참조.
            graph.add_edge(
                edge.from_node,
                edge.to_node,
                route_edge=edge,
                road_name=edge.road_name,
            )
        _graph_cache = (edges, graph)
        return graph

    def find_shortest_path(
        self,
        graph: Any,
        start: str,
        end: str,
        weight_fn: Callable[[RouteEdge], float],
    ) -> list[str]:
        # weight를 간선 속성에 사전 대입하지 않고 콜러블로 넘긴다 — 전 간선
        # 233k회 사전 계산 제거 + 캐시된 공유 그래프를 요청마다 변이하는
        # 동시성 문제 회피(다익스트라가 방문한 간선만 평가된다).
        def nx_weight(_u: str, _v: str, data: dict[str, Any]) -> float:
            return weight_fn(data["route_edge"])

        try:
            return list(nx.shortest_path(graph, source=start, target=end, weight=nx_weight))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
