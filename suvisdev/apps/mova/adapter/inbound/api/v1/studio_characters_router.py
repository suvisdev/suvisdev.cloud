"""영화↔배우 연결 라우터 — GET /mova/characters/by-movie/{movie_id}."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.studio_characters_schema import CastListSchema
from mova.app.ports.input.studio_characters_use_case import CharactersUseCase
from mova.dependencies.studio_characters_provider import get_characters_use_case

studio_characters_router = APIRouter(prefix="/characters", tags=["mova-characters"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@studio_characters_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="캐스팅 감독 (Casting Director)")


@studio_characters_router.get("/by-movie/{movie_id}", response_model=CastListSchema)
async def get_cast_by_movie(
    movie_id: int,
    characters: CharactersUseCase = Depends(get_characters_use_case),
) -> CastListSchema:
    """영화 id로 출연진(배우·감독) 목록 조회."""
    dto = await characters.get_cast_by_movie(movie_id)
    return dto.to_schema()
