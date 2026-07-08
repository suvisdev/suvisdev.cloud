from __future__ import annotations

import json
from pathlib import Path

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class SampleWalkGraphSource:
    """번들된 샘플 보행로 그래프(JSON) 소스.

    운영에서는 OpenStreetMap(osmnx, network_type='walk')으로 대체될 자리다.
    인바운드 어댑터가 요청 시점에 간선 목록과 시작/끝 노드를 확보하는 데 쓴다.
    """

    def __init__(self, json_path: str | Path) -> None:
        self._json_path = Path(json_path)

    def load_edges(self) -> list[RouteEdge]:
        rows = json.loads(self._json_path.read_text(encoding="utf-8"))
        edges: list[RouteEdge] = []
        for row in rows:
            start = Coordinate(latitude=row["from_lat"], longitude=row["from_lng"])
            end = Coordinate(latitude=row["to_lat"], longitude=row["to_lng"])
            edges.append(
                RouteEdge(
                    from_node=row["from"],
                    to_node=row["to"],
                    base_distance_m=float(row["base_distance_m"]),
                    midpoint=Coordinate(
                        latitude=(start.latitude + end.latitude) / 2,
                        longitude=(start.longitude + end.longitude) / 2,
                    ),
                    road_name=row.get("road_name"),
                )
            )
        return edges

    def nearest_node(self, point: Coordinate) -> str | None:
        """좌표에서 가장 가까운 그래프 노드 id를 반환한다. 그래프가 비면 None."""
        node_coords = self._node_coordinates()
        if not node_coords:
            return None
        return min(
            node_coords,
            key=lambda node_id: point.distance_to(node_coords[node_id]),
        )

    def _node_coordinates(self) -> dict[str, Coordinate]:
        rows = json.loads(self._json_path.read_text(encoding="utf-8"))
        coords: dict[str, Coordinate] = {}
        for row in rows:
            coords[row["from"]] = Coordinate(
                latitude=row["from_lat"], longitude=row["from_lng"]
            )
            coords[row["to"]] = Coordinate(
                latitude=row["to_lat"], longitude=row["to_lng"]
            )
        return coords
