"""노드 경로 ↔ 좌표·길이·장소 근접 — 라우터와 경로 후보 유스케이스가 공유한다."""

from __future__ import annotations

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

EdgeLookup = dict[tuple[str, str], RouteEdge]


def path_coordinates(edge_lookup: EdgeLookup, path: list[str]) -> list[list[float]]:
    """노드 경로 → 좌표열. 간선은 양방향으로 색인되므로 저장 방향이 아니라 **경로
    진행 방향**의 끝점을 골라야 한다 — 예전엔 항상 from_coord를 써서 역방향 간선에서
    폴리라인이 되돌아갔다(2026-09-27 수정). 좌표 없는 노드는 간선 중점으로 대체."""
    coords: list[list[float]] = []
    for i in range(len(path) - 1):
        edge = edge_lookup.get((path[i], path[i + 1]))
        if edge is None:
            continue
        src = edge.from_coord if edge.from_node == path[i] else edge.to_coord
        pt = src or edge.midpoint
        coords.append([pt.latitude, pt.longitude])
    if len(path) >= 2:
        last = edge_lookup.get((path[-2], path[-1]))
        if last is not None:
            dst = last.to_coord if last.to_node == path[-1] else last.from_coord
            if dst is not None:
                coords.append([dst.latitude, dst.longitude])
    return coords


def path_edges(edge_lookup: EdgeLookup, path: list[str]) -> list[RouteEdge]:
    return [e for i in range(len(path) - 1) if (e := edge_lookup.get((path[i], path[i + 1])))]


def nearest_vertex(coords: list[list[float]], point: Coordinate) -> tuple[int, float]:
    """경로 좌표 중 point에 가장 가까운 꼭짓점의 (인덱스, 거리 m). 간선이 수십 m라 근사로 충분."""
    best_i, best_d = -1, float("inf")
    for i, (lat, lng) in enumerate(coords):
        d = point.distance_to(Coordinate(lat, lng))
        if d < best_d:
            best_i, best_d = i, d
    return best_i, best_d
