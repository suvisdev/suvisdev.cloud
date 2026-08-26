from __future__ import annotations

from collections.abc import Callable
from typing import Any

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from gildle.adapter.outbound.orm.route_edge_orm import RouteEdgeOrm
from gildle.adapter.outbound.orm.route_node_orm import RouteNodeOrm
from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class PgRouteGraphRepository(RouteGraphPort):
    """RouteGraphPort의 PostgreSQL 구현체(sync).

    route_nodes + route_edges를 조회해 RouteEdge 도메인 객체로 변환하고,
    NetworkX 그래프를 구성한다. 최단경로 로직은 NetworkXRouteGraphAdapter와 동일.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def load_edges(self) -> list[RouteEdge]:
        session = self._session_factory()
        rows = session.execute(
            select(RouteEdgeOrm, RouteNodeOrm).join(
                RouteNodeOrm, RouteEdgeOrm.from_node_id == RouteNodeOrm.id
            )
        ).all()

        node_map: dict[int, RouteNodeOrm] = {}
        for _edge_orm, node_orm in rows:
            node_map[node_orm.id] = node_orm

        to_nodes = session.execute(select(RouteNodeOrm)).scalars().all()
        for n in to_nodes:
            node_map[n.id] = n

        edge_rows = session.execute(select(RouteEdgeOrm)).scalars().all()
        edges: list[RouteEdge] = []
        for e in edge_rows:
            fn = node_map.get(e.from_node_id)
            tn = node_map.get(e.to_node_id)
            if fn is None or tn is None:
                continue
            mid_lat = (fn.latitude + tn.latitude) / 2
            mid_lng = (fn.longitude + tn.longitude) / 2
            edges.append(
                RouteEdge(
                    from_node=fn.osm_id or str(fn.id),
                    to_node=tn.osm_id or str(tn.id),
                    base_distance_m=e.base_distance_m,
                    midpoint=Coordinate(latitude=mid_lat, longitude=mid_lng),
                    road_name=e.road_name,
                    tree_score=e.tree_score,
                    hazard_score=e.hazard_score,
                    dog_friendly_score=e.dog_friendly_score,
                )
            )
        return edges

    def build_graph(self, edges: list[RouteEdge]) -> nx.Graph:
        graph = nx.Graph()
        for edge in edges:
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
