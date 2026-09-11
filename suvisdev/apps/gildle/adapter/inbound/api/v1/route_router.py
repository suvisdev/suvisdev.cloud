from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from gildle.adapter.inbound.api.schemas.route_schema import (
    NavigateRequestSchema,
    RouteRequestSchema,
)
from gildle.app.ports.input.calculate_route_use_case import (
    CalculateDogFriendlyRouteUseCase,
)
from gildle.app.ports.input.get_map_data_use_case import (
    GetMapVisualizationDataUseCase,
)
from gildle.dependencies.route_provider import (
    get_calculate_route_use_case,
    get_map_data_use_case,
)
from gildle.domain.services.sun_position import sun_altitude_azimuth
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode

route_router = APIRouter(tags=["gildle"])
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[4] / "data"


@route_router.post("/routes")
def calculate_route(
    request: RouteRequestSchema,
    use_case: CalculateDogFriendlyRouteUseCase = Depends(get_calculate_route_use_case),
) -> dict[str, Any]:
    try:
        start, end, mode = request.to_domain()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    edges = _load_scored_edges()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")

    start_node = _find_nearest_node_id(edges, start)
    end_node = _find_nearest_node_id(edges, end)
    if start_node is None or end_node is None:
        return {"path": [], "coordinates": []}

    path = use_case.execute(edges, start_node, end_node, mode)

    edge_lookup = _edge_lookup(edges)

    coordinates: list[list[float]] = []
    for i in range(len(path) - 1):
        edge = edge_lookup.get((path[i], path[i + 1]))
        if edge and edge.from_coord is not None:
            coordinates.append([edge.from_coord.latitude, edge.from_coord.longitude])
        elif edge:
            coordinates.append([edge.midpoint.latitude, edge.midpoint.longitude])
    if path and len(path) >= 2:
        last_edge = edge_lookup.get((path[-2], path[-1]))
        if last_edge and last_edge.to_coord is not None:
            coordinates.append([last_edge.to_coord.latitude, last_edge.to_coord.longitude])

    return {"path": path, "coordinates": coordinates}


# ── 요청당 재구축 방지 캐시(2026-09-11 리뷰) ──────────────────────────────
# 라우터의 mtime 캐시가 같은 edges 리스트 객체를 재사용하므로, 파생 구조물
# (간선 lookup·노드 그리드)은 리스트 동일성(is)으로 재사용을 판정한다.

_edge_lookup_cache: tuple[list[RouteEdge], dict[tuple[str, str], RouteEdge]] | None = None


def _edge_lookup(edges: list[RouteEdge]) -> dict[tuple[str, str], RouteEdge]:
    global _edge_lookup_cache  # noqa: PLW0603
    if _edge_lookup_cache is not None and _edge_lookup_cache[0] is edges:
        return _edge_lookup_cache[1]
    lookup: dict[tuple[str, str], RouteEdge] = {}
    for e in edges:
        lookup[(e.from_node, e.to_node)] = e
        lookup[(e.to_node, e.from_node)] = e
    _edge_lookup_cache = (edges, lookup)
    return lookup


# 최근접 노드 탐색용 그리드 인덱스 — 셀 한 변 ≈0.005°(서울 위도에서 약 450~550m).
# 전수 스캔(간선 233k × 하버사인 2회)을 셀 몇 개 조회로 줄인다.
_NODE_GRID_CELL_DEG = 0.005
_NODE_GRID_MAX_RING = 200  # ≈1° — 이 밖이면 데이터 커버리지 밖으로 보고 포기
_node_grid_cache: (
    tuple[list[RouteEdge], dict[tuple[int, int], list[tuple[str, Coordinate]]]] | None
) = None


def _node_grid(edges: list[RouteEdge]) -> dict[tuple[int, int], list[tuple[str, Coordinate]]]:
    global _node_grid_cache  # noqa: PLW0603
    if _node_grid_cache is not None and _node_grid_cache[0] is edges:
        return _node_grid_cache[1]
    grid: dict[tuple[int, int], list[tuple[str, Coordinate]]] = {}
    seen: set[str] = set()
    for edge in edges:
        for node, coord in ((edge.from_node, edge.from_coord), (edge.to_node, edge.to_coord)):
            if coord is None or node in seen:
                continue
            seen.add(node)
            cell = (
                int(coord.latitude // _NODE_GRID_CELL_DEG),
                int(coord.longitude // _NODE_GRID_CELL_DEG),
            )
            grid.setdefault(cell, []).append((node, coord))
    _node_grid_cache = (edges, grid)
    return grid


def _find_nearest_node_id(edges: list[RouteEdge], point: Coordinate) -> str | None:
    grid = _node_grid(edges)
    if not grid:
        return None
    center = (
        int(point.latitude // _NODE_GRID_CELL_DEG),
        int(point.longitude // _NODE_GRID_CELL_DEG),
    )
    best_dist = float("inf")
    best_node = ""
    found_ring: int | None = None
    for ring in range(_NODE_GRID_MAX_RING + 1):
        # 후보를 처음 찾은 링에서 +2링까지 더 훑는다 — 셀 경계 바로 너머의
        # 더 가까운 노드를 놓치지 않기 위한 여유분.
        if found_ring is not None and ring > found_ring + 2:
            break
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                if max(abs(dx), abs(dy)) != ring:
                    continue
                for node, coord in grid.get((center[0] + dx, center[1] + dy), []):
                    d = point.distance_to(coord)
                    if d < best_dist:
                        best_dist = d
                        best_node = node
        if best_node and found_ring is None:
            found_ring = ring
    return best_node or None


_route_edges_cache: list[RouteEdge] | None = None
_route_edges_mtime: float = 0.0


def _load_scored_edges() -> list[RouteEdge]:
    global _route_edges_cache, _route_edges_mtime  # noqa: PLW0603
    scored_path = Path(os.getenv("GILDLE_SCORED_EDGES", str(_DATA_DIR / "scored_edges.json")))
    if not scored_path.exists():
        return []
    mtime = scored_path.stat().st_mtime
    if _route_edges_cache is not None and mtime == _route_edges_mtime:
        return _route_edges_cache
    rows = json.loads(scored_path.read_text(encoding="utf-8"))
    edges = [
        RouteEdge(
            from_node=r["from_node"],
            to_node=r["to_node"],
            base_distance_m=float(r["base_distance_m"]),
            midpoint=Coordinate(latitude=r["midpoint_lat"], longitude=r["midpoint_lng"]),
            road_name=r.get("road_name"),
            from_coord=Coordinate(latitude=r["from_lat"], longitude=r["from_lng"])
            if "from_lat" in r
            else None,
            to_coord=Coordinate(latitude=r["to_lat"], longitude=r["to_lng"])
            if "to_lat" in r
            else None,
            tree_score=float(r.get("tree_score", 0)),
            hazard_score=float(r.get("hazard_score", 0)),
            dog_friendly_score=float(r.get("dog_friendly_score", 0)),
        )
        for r in rows
    ]
    _route_edges_cache = edges
    _route_edges_mtime = mtime
    return edges


_shade_cache: dict[str, Any] | None = None
_shade_mtime: float = 0.0


def _load_shade_scores() -> dict[str, Any] | None:
    """shade_scores.json 로더 — scored_edges와 동일한 mtime 캐시 패턴."""
    global _shade_cache, _shade_mtime  # noqa: PLW0603
    path = Path(os.getenv("GILDLE_SHADE_SCORES", str(_DATA_DIR / "shade_scores.json")))
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _shade_cache is not None and mtime == _shade_mtime:
        return _shade_cache
    _shade_cache = json.loads(path.read_text(encoding="utf-8"))
    _shade_mtime = mtime
    return _shade_cache


_KST = timezone(timedelta(hours=9))
_SEOUL_CENTER = (37.5665, 126.9780)


def _resolve_slot(departure_time: str | None, slots: list[int]) -> int | None:
    """ "HH:MM"을 가장 가까운 슬롯 시(hour)로 매핑.

    밤 판정은 고정 슬롯 경계가 아니라 실제 오늘 날짜의 태양 고도로 한다
    (일출·일몰 자동 연동, 외부 API 불필요). 해가 떠 있는데 사전 계산 슬롯
    밖인 새벽·저녁 언저리는 가장 가까운 슬롯으로 클램프한다.
    """
    now_kst = datetime.now(_KST)
    if departure_time:
        try:
            hour_str, minute_str = departure_time.split(":")
            hour, minute = int(hour_str), int(minute_str)
            dt_kst = now_kst.replace(hour=hour, minute=minute)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail='departure_time은 "HH:MM" 형식이어야 합니다'
            ) from exc
    else:
        hour, minute = now_kst.hour, now_kst.minute
        dt_kst = now_kst

    altitude, _ = sun_altitude_azimuth(*_SEOUL_CENTER, dt_kst)
    if altitude <= 0:
        return None  # 일몰 후/일출 전 — 그늘 계산 제외

    slot = hour + (1 if minute >= 30 else 0)
    return min(max(slot, slots[0]), slots[-1])


class _FullShadeLookup(dict[str, Any]):
    """밤 시간대: 해가 없으므로 모든 간선을 그늘(1.0)로 취급 → 순수 최단 경로."""

    def get(self, key: Any, default: Any = None) -> float:
        return 1.0


_shade_lookup_by_slot: dict[int, dict[tuple[str, str], float]] = {}
_shade_lookup_src_mtime: float = 0.0


def _build_shade_lookup(slot: int) -> dict[tuple[str, str], float] | None:
    """슬롯별 lookup을 캐시한다 — 233k 엔트리 dict를 요청마다 재구축하지 않게
    (2026-09-11 리뷰). 원본 shade_scores.json이 바뀌면(mtime) 전체 무효화."""
    global _shade_lookup_src_mtime  # noqa: PLW0603
    data = _load_shade_scores()
    if data is None:
        return None
    if _shade_mtime != _shade_lookup_src_mtime:
        _shade_lookup_by_slot.clear()
        _shade_lookup_src_mtime = _shade_mtime
    cached = _shade_lookup_by_slot.get(slot)
    if cached is not None:
        return cached
    idx = data["slots"].index(slot)
    lookup: dict[tuple[str, str], float] = {}
    for key, pcts in data["edges"].items():
        from_node, _, to_node = key.partition("-")
        lookup[(from_node, to_node)] = pcts[idx] / 100.0
    _shade_lookup_by_slot[slot] = lookup
    return lookup


@route_router.post("/navigate")
def navigate(
    request: NavigateRequestSchema,
    use_case: CalculateDogFriendlyRouteUseCase = Depends(get_calculate_route_use_case),
) -> dict[str, Any]:
    try:
        season = SeasonMode.from_value(request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    edges = _load_scored_edges()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")

    # 여름 그늘 모드: 출발 시각을 슬롯에 매핑해 사전 계산 그늘을 조회한다.
    # 밤(슬롯 범위 밖)이면 해가 없으므로 그늘 계산을 제외하고 최단 경로로 안내.
    shade_lookup: dict[tuple[str, str], float] | None = None
    night = False
    if season is SeasonMode.SUMMER_SHADE:
        shade_data = _load_shade_scores()
        slots = shade_data["slots"] if shade_data else list(range(7, 20))
        slot = _resolve_slot(request.departure_time, slots)
        if slot is None:
            night = True
            shade_lookup = _FullShadeLookup()  # type: ignore[assignment]
        elif shade_data is not None:
            shade_lookup = _build_shade_lookup(slot)

    path = use_case.execute(
        edges, request.start_node, request.end_node, season, shade_lookup=shade_lookup
    )

    edge_lookup = _edge_lookup(edges)

    coordinates: list[list[float]] = []
    for i in range(len(path) - 1):
        edge = edge_lookup.get((path[i], path[i + 1]))
        if edge:
            if edge.from_coord is not None:
                coordinates.append([edge.from_coord.latitude, edge.from_coord.longitude])
            else:
                coordinates.append([edge.midpoint.latitude, edge.midpoint.longitude])

    if path and coordinates:
        last_edge = edge_lookup.get((path[-2], path[-1]))
        if last_edge and last_edge.to_coord is not None:
            coordinates.append([last_edge.to_coord.latitude, last_edge.to_coord.longitude])

    # 여름 그늘 모드(낮)에서만 경로의 길이가중 그늘 비율·구간별 그늘을 계산.
    edge_shades: list[float] | None = None
    shade_ratio: float | None = None
    if (
        season is SeasonMode.SUMMER_SHADE
        and shade_lookup is not None
        and not night
        and len(path) >= 2
    ):
        edge_shades = []
        total_len = 0.0
        shaded_len = 0.0
        for i in range(len(path) - 1):
            edge = edge_lookup.get((path[i], path[i + 1]))
            shade = 0.0
            if edge is not None:
                found = shade_lookup.get((edge.from_node, edge.to_node))
                if found is None:
                    found = shade_lookup.get((edge.to_node, edge.from_node))
                shade = found if found is not None else 0.0
                total_len += edge.base_distance_m
                shaded_len += edge.base_distance_m * shade
            edge_shades.append(round(shade, 2))
        shade_ratio = round(shaded_len / total_len, 2) if total_len > 0 else None

    return {
        "path": path,
        "coordinates": coordinates,
        "shade_ratio": shade_ratio,
        "edge_shades": edge_shades,
        "night": night,
    }


_scored_edges_cache: list[dict[str, Any]] | None = None
_scored_edges_mtime: float = 0.0


def _get_scored_edges_raw() -> list[dict[str, Any]]:
    global _scored_edges_cache, _scored_edges_mtime  # noqa: PLW0603
    scored_path = Path(os.getenv("GILDLE_SCORED_EDGES", str(_DATA_DIR / "scored_edges.json")))
    if not scored_path.exists():
        return []
    mtime = scored_path.stat().st_mtime
    if _scored_edges_cache is None or mtime != _scored_edges_mtime:
        _scored_edges_cache = json.loads(scored_path.read_text(encoding="utf-8"))
        _scored_edges_mtime = mtime
    return _scored_edges_cache


# 2026-09-11 리뷰 H5: bbox 없는 호출이 23.4만 간선(80MB급) 전체를 반환하는
# DoS 표면이었다 — 지도(gildle-map.tsx)는 항상 bbox+zoom을 보내므로 bbox를
# 필수화하고, zoom과 무관한 절대 상한을 둔다.
_MAX_EDGES_RESPONSE = 20_000


@route_router.get("/graph-edges")
def get_graph_edges(
    south: float = Query(...),
    west: float = Query(...),
    north: float = Query(...),
    east: float = Query(...),
    zoom: int | None = Query(None),
) -> list[dict[str, Any]]:
    edges = _get_scored_edges_raw()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")
    filtered = [
        e
        for e in edges
        if south <= e["midpoint_lat"] <= north and west <= e["midpoint_lng"] <= east
    ]
    if zoom is not None and zoom < 15 and len(filtered) > 5000:
        filtered = _decimate_by_grid(filtered, zoom)
    return filtered[:_MAX_EDGES_RESPONSE]


def _decimate_by_grid(edges: list[dict[str, Any]], zoom: int) -> list[dict[str, Any]]:
    grid_sizes = {12: 0.004, 13: 0.002, 14: 0.001}
    grid = grid_sizes.get(zoom, 0.005)
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, Any]] = []
    scored: list[tuple[float, dict[str, Any]]] = []
    for e in edges:
        key = (int(e["midpoint_lat"] / grid), int(e["midpoint_lng"] / grid))
        score = e.get("tree_score", 0) + e.get("hazard_score", 0)
        if key not in seen:
            seen.add(key)
            result.append(e)
        elif score > 0.3:
            scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    for _, e in scored[:1000]:
        result.append(e)
    return result


@route_router.get("/map-data")
def get_map_data(
    mode: str,
    use_case: GetMapVisualizationDataUseCase = Depends(get_map_data_use_case),
) -> dict[str, Any]:
    try:
        season = SeasonMode.from_value(mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return use_case.execute(season)
