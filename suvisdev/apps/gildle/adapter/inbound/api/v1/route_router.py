from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from gildle.adapter.inbound.api.schemas.route_schema import (
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
from gildle.domain.value_objects.season_mode import SeasonMode

route_router = APIRouter(tags=["gildle"])
logger = logging.getLogger(__name__)


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
