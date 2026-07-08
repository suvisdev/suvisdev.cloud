"""검색 라우터 — GET /mova/search?q="""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.studio_search_schema import SearchResultSchema
from mova.app.ports.input.studio_search_use_case import SearchUseCase
from mova.dependencies.studio_search_provider import get_search_use_case

studio_search_router = APIRouter(prefix="/search", tags=["mova-search"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@studio_search_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="검색 감독 (Search Director)")


@studio_search_router.get("", response_model=SearchResultSchema)
async def search_movies(
    q: str = Query(..., min_length=1, description="검색어 (태그 label 또는 영화 제목)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: SearchUseCase = Depends(get_search_use_case),
) -> SearchResultSchema:
    """태그 label 또는 영화 제목 ILIKE로 영화를 검색한다."""
    dto = await search.search_movies(q, limit, offset)
    return dto.to_schema()
