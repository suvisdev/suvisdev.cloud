from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from gildle.app.ports.output.walk_graph_port import WalkGraphPort
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


def _ox() -> Any:
    return importlib.import_module("osmnx")


class OsmWalkGraphAdapter(WalkGraphPort):
    """WalkGraphPort의 osmnx 구현체.

    osmnx(network_type='walk')로 보행 그래프를 추출하고,
    RouteEdge 도메인 VO로 변환한다. MultiDiGraph → 무향 간선으로 중복 제거.
    cache_dir을 설정하면 GraphML 캐시를 자동으로 사용한다.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir

    def load_edges(self, place: str) -> list[RouteEdge]:
        if self._cache_dir is not None:
            cache_path = self._cache_dir / f"{place.replace(', ', '_')}.graphml"
            if cache_path.exists():
                return self.load_from_graphml(cache_path)
            graph = _ox().graph_from_place(place, network_type="walk")
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            _ox().save_graphml(graph, filepath=cache_path)
            return self._graph_to_edges(graph)
        graph = _ox().graph_from_place(place, network_type="walk")
        return self._graph_to_edges(graph)

    def nearest_node(self, edges: list[RouteEdge], point: Coordinate) -> str | None:
        if not edges:
            return None
        all_nodes = self._collect_node_coords(edges)
        return min(all_nodes, key=lambda nid: point.distance_to(all_nodes[nid]))

    def save_graphml(self, place: str, path: Path) -> Path:
        graph = _ox().graph_from_place(place, network_type="walk")
        _ox().save_graphml(graph, filepath=path)
        return path

    def load_from_graphml(self, path: Path) -> list[RouteEdge]:
        graph = _ox().load_graphml(filepath=path)
        return self._graph_to_edges(graph)

    def _graph_to_edges(self, graph: Any) -> list[RouteEdge]:
        edges: list[RouteEdge] = []
        seen: set[tuple[str, str]] = set()
        for u, v, _key, data in graph.edges(data=True, keys=True):
            pair = (str(min(u, v)), str(max(u, v)))
            if pair in seen:
                continue
            seen.add(pair)

            nodes = graph.nodes
            u_lat = float(nodes[u]["y"])
            u_lng = float(nodes[u]["x"])
            v_lat = float(nodes[v]["y"])
            v_lng = float(nodes[v]["x"])

            raw_name = data.get("name")
            if isinstance(raw_name, list):
                road_name = str(raw_name[0]) if raw_name else None
            elif raw_name is not None:
                road_name = str(raw_name)
            else:
                road_name = None

            length = float(data.get("length", 0.0))
            mid = Coordinate(
                latitude=(u_lat + v_lat) / 2,
                longitude=(u_lng + v_lng) / 2,
            )
            edges.append(
                RouteEdge(
                    from_node=str(u),
                    to_node=str(v),
                    base_distance_m=length,
                    midpoint=mid,
                    road_name=road_name,
                )
            )
        return edges

    @staticmethod
    def _collect_node_coords(edges: list[RouteEdge]) -> dict[str, Coordinate]:
        """간선 목록에서 노드별 좌표를 수집한다 (midpoint를 근사 좌표로 사용)."""
        coords: dict[str, Coordinate] = {}
        for edge in edges:
            coords.setdefault(edge.from_node, edge.midpoint)
            coords.setdefault(edge.to_node, edge.midpoint)
        return coords
