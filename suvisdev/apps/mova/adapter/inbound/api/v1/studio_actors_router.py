"""배우/감독 라우터 — GET /mova/actors/{id}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.studio_actors_schema import ActorDetailSchema
from mova.app.ports.input.studio_actors_use_case import ActorsUseCase
from mova.dependencies.studio_actors_provider import get_actors_use_case

studio_actors_router = APIRouter(prefix="/actors", tags=["mova-actors"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@studio_actors_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="배우 (Actor)")


@studio_actors_router.get("/{actor_id}", response_model=ActorDetailSchema)
async def get_actor_detail(
    actor_id: int,
    actors: ActorsUseCase = Depends(get_actors_use_case),
) -> ActorDetailSchema:
    """배우/감독 정보 + 출연작 목록."""
    dto = await actors.get_actor_detail(actor_id)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    return dto.to_schema()
