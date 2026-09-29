from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from gildle.adapter.inbound.api.schemas.route_schema import (
    LoopRequestSchema,
    NavigateRequestSchema,
    RouteOptionsRequestSchema,
    RouteRequestSchema,
    RouteViaRequestSchema,
    WalkPlanRequestSchema,
)
from gildle.app.dtos.route_option_dto import RouteOptionDto
from gildle.app.ports.input.calculate_route_use_case import (
    CalculateDogFriendlyRouteUseCase,
)
from gildle.app.ports.input.get_map_data_use_case import (
    GetMapVisualizationDataUseCase,
)
from gildle.app.ports.input.plan_loop_use_case import PlanLoopRouteUseCase
from gildle.app.ports.input.route_options_use_case import RouteOptionsUseCase
from gildle.app.ports.input.walk_plan_use_case import WalkPlanUseCase
from gildle.dependencies.route_provider import (
    get_calculate_route_use_case,
    get_map_data_use_case,
    get_plan_loop_use_case,
    get_route_options_use_case,
    get_walk_plan_use_case,
)
from gildle.domain.services.route_geometry import path_coordinates
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
    """좌표 기반 경로 — 최근접 노드로 스냅한 뒤 `/navigate`와 같은 탐색·응답을 쓴다.

    2026-09-27까지는 여름 모드여도 그늘 조회 없이(나무 점수 폴백) 돌았고 응답에
    그늘 필드가 없었다 — 앱은 좌표만 알기 때문에 이 엔드포인트가 `/navigate`와
    같은 기능을 가져야 한다.
    """
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
        return _empty_route_response()

    return _plan_route(
        edges,
        start_node,
        end_node,
        mode,
        use_case,
        departure_time=request.departure_time,
        max_detour_ratio=request.max_detour_ratio,
    )


def _empty_route_response() -> dict[str, Any]:
    return {
        "path": [],
        "coordinates": [],
        "length_m": 0.0,
        "shade_ratio": None,
        "edge_shades": None,
        "night": False,
    }


def _path_coordinates(
    edge_lookup: dict[tuple[str, str], RouteEdge], path: list[str]
) -> list[list[float]]:
    """노드 경로 → 좌표열(진행 방향 기준). 구현은 도메인 route_geometry로 옮김(09-28 경로 후보와 공유)."""
    return path_coordinates(edge_lookup, path)


def _path_length_m(edge_lookup: dict[tuple[str, str], RouteEdge], path: list[str]) -> float:
    total = 0.0
    for i in range(len(path) - 1):
        edge = edge_lookup.get((path[i], path[i + 1]))
        if edge is not None:
            total += edge.base_distance_m
    return round(total, 1)


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


_shade_cache: dict[Path, tuple[float, dict[str, Any]]] = {}


def _month_distance(a: int, b: int) -> int:
    d = abs(a - b)
    return min(d, 12 - d)


def _shade_path(today: date) -> Path | None:
    """오늘 날짜에 가장 가까운 달의 표(shade_scores_MM.json, 2026-09-29 월별화).
    환경변수 GILDLE_SHADE_SCORES가 최우선, 월별 표가 하나도 없으면 구 shade_scores.json(8월 1일)."""
    env = os.getenv("GILDLE_SHADE_SCORES")
    if env:
        return Path(env) if Path(env).exists() else None
    monthly = {int(p.stem[-2:]): p for p in _DATA_DIR.glob("shade_scores_[0-1][0-9].json")}
    if monthly:
        return monthly[min(monthly, key=lambda m: (_month_distance(m, today.month), m))]
    legacy = _DATA_DIR / "shade_scores.json"
    return legacy if legacy.exists() else None


def _load_shade_scores(today: date | None = None) -> dict[str, Any] | None:
    """그늘 표 로더 — 경로별 mtime 캐시(scored_edges와 같은 패턴). 반환 dict에 `_key`(경로·mtime)를
    붙여 슬롯 lookup 캐시가 어느 표에서 나왔는지 구분한다."""
    path = _shade_path(today or datetime.now(_KST).date())
    if path is None:
        return None
    mtime = path.stat().st_mtime
    hit = _shade_cache.get(path)
    if hit is not None and hit[0] == mtime:
        return hit[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_key"] = (str(path), mtime)
    _shade_cache[path] = (mtime, data)
    return data


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


_WALK_SPEED_M_PER_S = 1.2  # 평지 도보 — ETA 모델(§2-E)이 생기면 대체


def _slot_of_elapsed(departure_time: str | None, start_slot: int) -> Callable[[float], int]:
    """걸은 거리(m) → 슬롯(hour). 출발 "HH:MM"(없으면 현재 시각)에 도보 시간을 더해
    30분 반올림한다. 시간 의존 탐색(③)에 넘긴다."""
    now = datetime.now(_KST)
    if departure_time:
        try:
            h, m = departure_time.split(":")
            base_min = int(h) * 60 + int(m)
        except ValueError:
            base_min = start_slot * 60
    else:
        base_min = now.hour * 60 + now.minute

    def slot_of(elapsed_m: float) -> int:
        total_min = base_min + elapsed_m / _WALK_SPEED_M_PER_S / 60.0
        return int((total_min + 30) // 60)

    return slot_of


class _FullShadeLookup(dict[str, Any]):
    """밤 시간대: 해가 없으므로 모든 간선을 그늘(1.0)로 취급 → 순수 최단 경로."""

    def get(self, key: Any, default: Any = None) -> float:
        return 1.0


_shade_lookup_by_slot: dict[tuple[str, float, int], dict[tuple[str, str], float]] = {}


def _build_shade_lookup(
    slot: int, data: dict[str, Any] | None = None
) -> dict[tuple[str, str], float] | None:
    """(표, 슬롯)별 lookup을 캐시한다 — 233k 엔트리 dict를 요청마다 재구축하지 않게
    (2026-09-11 리뷰). 같은 표가 갱신되면(mtime) 그 표의 항목만 버린다."""
    data = data if data is not None else _load_shade_scores()
    if data is None:
        return None
    path, mtime = data["_key"]
    key = (path, mtime, slot)
    cached = _shade_lookup_by_slot.get(key)
    if cached is not None:
        return cached
    for old in [k for k in _shade_lookup_by_slot if k[0] == path and k[1] != mtime]:
        del _shade_lookup_by_slot[old]
    idx = data["slots"].index(slot)
    lookup: dict[tuple[str, str], float] = {}
    for edge_key, pcts in data["edges"].items():
        from_node, _, to_node = edge_key.partition("-")
        lookup[(from_node, to_node)] = pcts[idx] / 100.0
    _shade_lookup_by_slot[key] = lookup
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

    return _plan_route(
        edges,
        request.start_node,
        request.end_node,
        season,
        use_case,
        departure_time=request.departure_time,
        max_detour_ratio=request.max_detour_ratio,
    )


def _plan_route(
    edges: list[RouteEdge],
    start_node: str,
    end_node: str,
    season: SeasonMode,
    use_case: CalculateDogFriendlyRouteUseCase,
    *,
    departure_time: str | None,
    max_detour_ratio: float | None,
) -> dict[str, Any]:
    """`/routes`·`/navigate` 공통 — 그늘 슬롯 결정 → 탐색(④ 제약 / ③ 시간 의존 / 기본)
    → 좌표·길이·그늘 통계."""
    # 여름 그늘 모드: 출발 시각을 슬롯에 매핑해 사전 계산 그늘을 조회한다.
    # 밤(슬롯 범위 밖)이면 해가 없으므로 그늘 계산을 제외하고 최단 경로로 안내.
    shade_lookup: dict[tuple[str, str], float] | None = None
    night = False
    slot: int | None = None
    slots: list[int] = []
    if season is SeasonMode.SUMMER_SHADE:
        shade_data = _load_shade_scores()
        slots = shade_data["slots"] if shade_data else list(range(7, 20))
        slot = _resolve_slot(departure_time, slots)
        if slot is None:
            night = True
            shade_lookup = _FullShadeLookup()  # type: ignore[assignment]
        elif shade_data is not None:
            shade_lookup = _build_shade_lookup(slot, shade_data)

    if max_detour_ratio is None and season is SeasonMode.SPRING_AUTUMN:
        # 봄가을 수관 감면(최대 60%, 09-28)은 상한이 없으면 2.5배까지 돌 수 있다 — 최단 × 1.5로 묶는다.
        max_detour_ratio = 0.5
    if max_detour_ratio is not None:
        # ④ 제약 최단경로 — 그늘·가로수 선호를 반영하되 길이 상한을 지킨다.
        path = use_case.execute_bounded(
            edges,
            start_node,
            end_node,
            season,
            shade_lookup=shade_lookup,
            max_detour_ratio=max_detour_ratio,
        )
    elif season is SeasonMode.SUMMER_SHADE and not night and slot is not None and slots:
        # ③ 시간 의존 — 걷는 동안 슬롯이 넘어가면 그 시각의 그늘을 쓴다.
        # networkx 구현체는 지원하지 않아 출발 슬롯 하나로 동작한다(포트 기본 구현).
        by_slot = {s: lk for s in slots if s >= slot and (lk := _build_shade_lookup(s)) is not None}
        path = use_case.execute_time_aware(
            edges,
            start_node,
            end_node,
            season,
            shade_by_slot=by_slot,
            slot_of_elapsed=_slot_of_elapsed(departure_time, slot),
        )
    else:
        path = use_case.execute(edges, start_node, end_node, season, shade_lookup=shade_lookup)

    edge_lookup = _edge_lookup(edges)
    coordinates = _path_coordinates(edge_lookup, path)

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
                # 가중치(RouteWeightCalculator)와 같은 정의: 건물 그늘·수관 중 큰 값.
                shade = max(found if found is not None else 0.0, edge.tree_score)
                total_len += edge.base_distance_m
                shaded_len += edge.base_distance_m * shade
            edge_shades.append(round(shade, 2))
        shade_ratio = round(shaded_len / total_len, 2) if total_len > 0 else None

    return {
        "path": path,
        "coordinates": coordinates,
        "length_m": _path_length_m(edge_lookup, path),
        "shade_ratio": shade_ratio,
        "edge_shades": edge_shades,
        "night": night,
    }


@route_router.post("/loops")
def plan_loops(
    request: LoopRequestSchema,
    use_case: PlanLoopRouteUseCase = Depends(get_plan_loop_use_case),
) -> dict[str, Any]:
    """출발점으로 돌아오는 목표 거리 산책 루프 후보(§1-⑤). 여름 모드는 출발 슬롯 그늘 적용."""
    try:
        season = SeasonMode.from_value(request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    edges = _load_scored_edges()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")
    start = _find_nearest_node_id(edges, Coordinate(latitude=request.lat, longitude=request.lng))
    if start is None:
        return {"candidates": [], "night": False}

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
            shade_lookup = _build_shade_lookup(slot, shade_data)

    candidates = use_case.execute(
        edges,
        start,
        request.target_m,
        season,
        nearest_node=lambda c: _find_nearest_node_id(edges, c),
        shade_lookup=shade_lookup,
        limit=request.limit,
    )
    edge_lookup = _edge_lookup(edges)
    out = []
    for c in candidates:
        out.append(
            {
                "path": c.path,
                "coordinates": _path_coordinates(edge_lookup, c.path),
                "length_m": c.length_m,
                "overlap_ratio": c.overlap_ratio,
                "shade_ratio": None if night else c.shade_ratio,
                "bearing_deg": c.bearing_deg,
            }
        )
    return {"candidates": out, "night": night}


def _edge_to_dict(e: RouteEdge) -> dict[str, Any]:
    """graph-edges 응답 한 건 — scored_edges.json 레코드와 같은 키.
    2026-09-27: 원본 dict 23만 건을 별도 캐시로 들고 있던 것을 없앴다(RouteEdge 리스트와
    이중 보관 — 파드 RSS 약 1.7GB 중 상당분). 응답은 bbox 필터 뒤 최대 2만 건만 직렬화한다."""
    rec: dict[str, Any] = {
        "from_node": e.from_node,
        "to_node": e.to_node,
        "base_distance_m": e.base_distance_m,
        "midpoint_lat": e.midpoint.latitude,
        "midpoint_lng": e.midpoint.longitude,
        "road_name": e.road_name,
        "tree_score": e.tree_score,
        "hazard_score": e.hazard_score,
        "dog_friendly_score": e.dog_friendly_score,
    }
    if e.from_coord is not None:
        rec["from_lat"] = e.from_coord.latitude
        rec["from_lng"] = e.from_coord.longitude
    if e.to_coord is not None:
        rec["to_lat"] = e.to_coord.latitude
        rec["to_lng"] = e.to_coord.longitude
    return rec


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
    edges = _load_scored_edges()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")
    filtered = [
        e
        for e in edges
        if south <= e.midpoint.latitude <= north and west <= e.midpoint.longitude <= east
    ]
    if zoom is not None and zoom < 15 and len(filtered) > 5000:
        filtered = _decimate_by_grid(filtered, zoom)
    return [_edge_to_dict(e) for e in filtered[:_MAX_EDGES_RESPONSE]]


def _decimate_by_grid(edges: list[RouteEdge], zoom: int) -> list[RouteEdge]:
    grid_sizes = {12: 0.004, 13: 0.002, 14: 0.001}
    grid = grid_sizes.get(zoom, 0.005)
    seen: set[tuple[int, int]] = set()
    result: list[RouteEdge] = []
    scored: list[tuple[float, RouteEdge]] = []
    for e in edges:
        key = (int(e.midpoint.latitude / grid), int(e.midpoint.longitude / grid))
        score = e.tree_score + e.hazard_score
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


_RECOMMENDED_KIND = {"summer_shade": "shade", "spring_autumn": "green", "winter_safety": "fast"}


def _day_shade_lookup(departure_time: str | None) -> tuple[Any, bool]:
    """(그늘 조회 또는 None, 밤 여부). 밤이면 그늘 후보를 내지 않는다."""
    shade_data = _load_shade_scores()
    slots = shade_data["slots"] if shade_data else list(range(7, 20))
    slot = _resolve_slot(departure_time, slots)
    if slot is None:
        return None, True
    return (_build_shade_lookup(slot, shade_data) if shade_data is not None else None), False


def _option_json(o: RouteOptionDto) -> dict[str, Any]:
    return {
        "kind": o.kind,
        "label": o.label,
        "reason": o.reason,
        "highlights": o.highlights,
        "recommended": o.recommended,
        "path": o.path,
        "coordinates": o.coordinates,
        "length_m": o.length_m,
        "minutes": o.minutes,
        "extra_m": o.extra_m,
        "shade_ratio": o.shade_ratio,
        "green_ratio": o.green_ratio,
        "climb_m": o.climb_m,
        "places": [
            {
                "id": p.place_id,
                "name": p.name,
                "category": p.category,
                "lat": p.coordinate.latitude,
                "lng": p.coordinate.longitude,
                "address": p.address,
                "url": p.url,
                "phone": p.phone,
            }
            for p in o.places
        ],
    }


@route_router.post("/routes/options")
def route_options(
    request: RouteOptionsRequestSchema,
    use_case: RouteOptionsUseCase = Depends(get_route_options_use_case),
) -> dict[str, Any]:
    """경로 후보(빠른·그늘·푸른 길) + 고를 이유 + 경로 곁 반려동물 장소(2026-09-28)."""
    edges = _load_scored_edges()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")
    try:
        start = Coordinate(request.start_lat, request.start_lng)
        end = Coordinate(request.end_lat, request.end_lng)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    start_node = _find_nearest_node_id(edges, start)
    end_node = _find_nearest_node_id(edges, end)
    if start_node is None or end_node is None:
        return {"options": [], "night": False}
    shade_lookup, night = _day_shade_lookup(request.departure_time)
    options = use_case.plan(
        edges,
        start_node,
        end_node,
        shade_lookup=shade_lookup,
        recommended_kind=_RECOMMENDED_KIND.get(request.mode, "fast"),
        elevation=_load_elevation(),
    )
    return {"options": [_option_json(o) for o in options], "night": night}


@route_router.post("/routes/via")
def route_via(
    request: RouteViaRequestSchema,
    use_case: RouteOptionsUseCase = Depends(get_route_options_use_case),
) -> dict[str, Any]:
    """고른 반려동물 장소에 들렀다 가는 경로 — 출발→장소→도착을 같은 성격(빠른·그늘·푸른)으로."""
    edges = _load_scored_edges()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")
    try:
        start = Coordinate(request.start_lat, request.start_lng)
        end = Coordinate(request.end_lat, request.end_lng)
        via = Coordinate(request.via_lat, request.via_lng)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    nodes = [_find_nearest_node_id(edges, c) for c in (start, via, end)]
    if any(n is None for n in nodes):
        raise HTTPException(status_code=404, detail="경로를 만들 수 없는 위치예요.")
    shade_lookup, _ = _day_shade_lookup(request.departure_time)
    option = use_case.via(
        edges,
        nodes[0],  # type: ignore[arg-type]
        nodes[1],  # type: ignore[arg-type]
        nodes[2],  # type: ignore[arg-type]
        base_kind=request.base_kind if request.base_kind != "shade" or shade_lookup else "fast",
        shade_lookup=shade_lookup,
        via_name=request.via_name,
        via_point=via,
        elevation=_load_elevation(),
    )
    if option is None:
        raise HTTPException(status_code=404, detail="들렀다 가는 경로를 찾지 못했어요.")
    return {"option": _option_json(option)}


_elevation_cache: tuple[float, dict[str, float]] | None = None


def _load_elevation() -> dict[str, float] | None:
    """노드 고도(SRTM 30m, scripts/compute_node_elevation.py) — 파일이 바뀌면 다시 읽는다."""
    global _elevation_cache  # noqa: PLW0603
    path = Path(os.getenv("GILDLE_ELEVATION_JSON", str(_DATA_DIR / "node_elevation.json")))
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _elevation_cache is None or _elevation_cache[0] != mtime:
        with path.open(encoding="utf-8") as f:
            _elevation_cache = (mtime, {k: float(v) for k, v in json.load(f)["nodes"].items()})
        logger.info("[gildle] 노드 고도 %d개 로드", len(_elevation_cache[1]))
    return _elevation_cache[1]


@route_router.post("/walk/plan")
def walk_plan(
    request: WalkPlanRequestSchema,
    use_case: WalkPlanUseCase = Depends(get_walk_plan_use_case),
) -> dict[str, Any]:
    """ "오늘은 40분 동안 3키로, 편한 길로" — 이해(7.8B+규칙) 후 출발지로 돌아오는 루프를 추천."""
    edges = _load_scored_edges()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")
    try:
        start = Coordinate(request.lat, request.lng)
        end = (
            Coordinate(request.end_lat, request.end_lng)
            if request.end_lat is not None and request.end_lng is not None
            else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    understood = use_case.understand(
        request.text,
        minutes=request.minutes,
        distance_km=request.distance_km,
        preference=request.preference,
        stops=request.stops,
        has_end=end is not None,
    )
    start_node = _find_nearest_node_id(edges, start)
    end_node = _find_nearest_node_id(edges, end) if end is not None else None
    if start_node is None:
        raise HTTPException(status_code=404, detail="이 위치 근처엔 길 데이터가 없어요.")
    shade_lookup, night = _day_shade_lookup(request.departure_time)
    result = use_case.plan(
        understood,
        edges,
        start_node,
        end_node,
        shade_lookup=shade_lookup,
        elevation=_load_elevation(),
        nearest_node=lambda c: _find_nearest_node_id(edges, c),
        start_point=start,
    )
    u = result.understood
    p = result.destination_place
    v = result.via_place
    return {
        "understood": {
            "kind": u.kind,
            "minutes": u.minutes,
            "distance_km": u.distance_km,
            "preference": u.preference,
            "stops": list(u.stops),
            "destination": u.destination,
            "source": u.source,
        },
        "destination_place": {
            "name": p.name,
            "category": p.category,
            "lat": p.coordinate.latitude,
            "lng": p.coordinate.longitude,
            "address": p.address,
        }
        if p is not None
        else None,
        "via_place": {
            "name": v.name,
            "category": v.category,
            "lat": v.coordinate.latitude,
            "lng": v.coordinate.longitude,
            "address": v.address,
        }
        if v is not None
        else None,
        "target_m": round(result.target_m),
        "max_m": round(result.max_m) if result.max_m else None,
        "options": [_option_json(o) for o in result.options],
        "night": night,
    }
