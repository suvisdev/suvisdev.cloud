"""태그 라우터 — GET /mova/tags/by-movie/{movie_id}."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.studio_tags_schema import TagGroupSchema
from mova.app.ports.input.studio_tags_use_case import TagsUseCase
from mova.dependencies.studio_tags_provider import get_tags_use_case

studio_tags_router = APIRouter(prefix="/tags", tags=["mova-tags"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@studio_tags_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="홍보 담당자 (Publicist)")


@studio_tags_router.get("/by-movie/{movie_id}", response_model=TagGroupSchema)
async def get_tags_by_movie(
    movie_id: int,
    tags: TagsUseCase = Depends(get_tags_use_case),
) -> TagGroupSchema:
    """영화 id로 감성·장르·등장인물 태그 조회."""
    dto = await tags.get_tags_by_movie(movie_id)
    return dto.to_schema()
