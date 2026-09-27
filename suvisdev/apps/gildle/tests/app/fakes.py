"""Phase 2 Use Case 단위 테스트용 Fake 포트 구현.

실제 CSV/Kakao/NetworkX 없이 Use Case 로직만 검증한다.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from gildle.app.ports.output.geocoding_port import GeocodingPort
from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.app.ports.output.route_graph_port import RouteGraphPort
from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.app.ports.output.walk_graph_port import WalkGraphPort
from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class FakeTreeSegmentRepository(TreeSegmentRepository):
    def __init__(self, segments: list[TreeSegment] | None = None) -> None:
        self._segments = list(segments or [])

    def find_all(self) -> list[TreeSegment]:
        return list(self._segments)


class FakeHazardZoneRepository(HazardZoneRepository):
    def __init__(self, hazards: list[HazardZone] | None = None) -> None:
        self._hazards = list(hazards or [])

    def find_all(self) -> list[HazardZone]:
        return list(self._hazards)


class FakeGeocodingAdapter(GeocodingPort):
    def __init__(self, mapping: dict[str, Coordinate] | None = None) -> None:
        self._mapping = mapping or {}
        self.calls: list[str] = []

    def geocode(self, address: str) -> Coordinate | None:
        self.calls.append(address)
        return self._mapping.get(address)


class CapturingRouteGraphPort(RouteGraphPort):
    """build_graph/find_shortest_path 호출과 weight_fn 클로저를 포착하는 Fake."""

    def __init__(self, path: list[str] | None = None) -> None:
        self._path = path or []
        self.built_edges: list[RouteEdge] | None = None
        self.weight_fn: Callable[[RouteEdge], float] | None = None
        self.start: str | None = None
        self.end: str | None = None

    def build_graph(self, edges: list[RouteEdge]) -> Any:
        self.built_edges = list(edges)
        return {"edges": list(edges)}

    def find_shortest_path(
        self,
        graph: Any,
        start: str,
        end: str,
        weight_fn: Callable[[RouteEdge], float],
        *,
        heuristic_scale: float | None = None,  # 휴리스틱 없음 — 포트 호환용
    ) -> list[str]:
        self.start = start
        self.end = end
        self.weight_fn = weight_fn
        return list(self._path)


class FakeWalkGraphSource(WalkGraphPort):
    """OSM 네트워크 호출 없이 WalkGraphPort를 테스트하기 위한 Fake."""

    def __init__(self, edges: list[RouteEdge] | None = None) -> None:
        self._edges = list(edges or [])

    def load_edges(self, place: str) -> list[RouteEdge]:
        return list(self._edges)

    def nearest_node(self, edges: list[RouteEdge], point: Coordinate) -> str | None:
        all_nodes: dict[str, Coordinate] = {}
        for edge in edges or self._edges:
            all_nodes.setdefault(edge.from_node, edge.midpoint)
            all_nodes.setdefault(edge.to_node, edge.midpoint)
        if not all_nodes:
            return None
        return min(all_nodes, key=lambda nid: point.distance_to(all_nodes[nid]))

    def save_graphml(self, place: str, path: Path) -> Path:
        return path

    def load_from_graphml(self, path: Path) -> list[RouteEdge]:
        return list(self._edges)
