from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse

from gildle.adapter.inbound.api.schemas.route_schema import (
    NavigateRequestSchema,
    RouteRequestSchema,
    RouteResponseSchema,
)
from gildle.adapter.outbound.graph.sample_walk_graph_source import SampleWalkGraphSource
from gildle.app.ports.input.calculate_route_use_case import (
    CalculateDogFriendlyRouteUseCase,
)
from gildle.app.ports.input.get_map_data_use_case import (
    GetMapVisualizationDataUseCase,
)
from gildle.dependencies.route_provider import (
    get_calculate_route_use_case,
    get_map_data_use_case,
    get_walk_graph_source,
)
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.season_mode import SeasonMode


route_router = APIRouter(tags=["gildle"])
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[4] / "data"


@route_router.post("/routes", response_model=RouteResponseSchema)
def calculate_route(
    request: RouteRequestSchema,
    use_case: CalculateDogFriendlyRouteUseCase = Depends(get_calculate_route_use_case),
    graph_source: SampleWalkGraphSource = Depends(get_walk_graph_source),
) -> RouteResponseSchema:
    try:
        start, end, mode = request.to_domain()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start_node = graph_source.nearest_node(start)
    end_node = graph_source.nearest_node(end)
    if start_node is None or end_node is None:
        return RouteResponseSchema(path=[])

    path = use_case.execute(graph_source.load_edges(), start_node, end_node, mode)
    return RouteResponseSchema(path=path)


_route_edges_cache: list[RouteEdge] | None = None
_route_edges_mtime: float = 0.0


def _load_scored_edges() -> list[RouteEdge]:
    global _route_edges_cache, _route_edges_mtime  # noqa: PLW0603
    scored_path = Path(
        os.getenv("GILDLE_SCORED_EDGES", str(_DATA_DIR / "scored_edges.json"))
    )
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
            if "from_lat" in r else None,
            to_coord=Coordinate(latitude=r["to_lat"], longitude=r["to_lng"])
            if "to_lat" in r else None,
            tree_score=float(r.get("tree_score", 0)),
            hazard_score=float(r.get("hazard_score", 0)),
            dog_friendly_score=float(r.get("dog_friendly_score", 0)),
        )
        for r in rows
    ]
    _route_edges_cache = edges
    _route_edges_mtime = mtime
    return edges


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

    path = use_case.execute(edges, request.start_node, request.end_node, season)

    edge_lookup: dict[tuple[str, str], RouteEdge] = {}
    for e in edges:
        edge_lookup[(e.from_node, e.to_node)] = e
        edge_lookup[(e.to_node, e.from_node)] = e

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

    return {"path": path, "coordinates": coordinates}


_scored_edges_cache: list[dict[str, Any]] | None = None
_scored_edges_mtime: float = 0.0


def _get_scored_edges_raw() -> list[dict[str, Any]]:
    global _scored_edges_cache, _scored_edges_mtime  # noqa: PLW0603
    scored_path = Path(
        os.getenv("GILDLE_SCORED_EDGES", str(_DATA_DIR / "scored_edges.json"))
    )
    if not scored_path.exists():
        return []
    mtime = scored_path.stat().st_mtime
    if _scored_edges_cache is None or mtime != _scored_edges_mtime:
        _scored_edges_cache = json.loads(scored_path.read_text(encoding="utf-8"))
        _scored_edges_mtime = mtime
    return _scored_edges_cache  # type: ignore[return-value]


@route_router.get("/graph-edges")
def get_graph_edges(
    south: float | None = Query(None),
    west: float | None = Query(None),
    north: float | None = Query(None),
    east: float | None = Query(None),
    zoom: int | None = Query(None),
) -> list[dict[str, Any]]:
    edges = _get_scored_edges_raw()
    if not edges:
        raise HTTPException(status_code=404, detail="scored_edges.json 없음")
    if south is not None and west is not None and north is not None and east is not None:
        filtered = [
            e for e in edges
            if south <= e["midpoint_lat"] <= north and west <= e["midpoint_lng"] <= east
        ]
        if zoom is not None and zoom < 15 and len(filtered) > 5000:
            filtered = _decimate_by_grid(filtered, zoom)
        return filtered
    return edges


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
