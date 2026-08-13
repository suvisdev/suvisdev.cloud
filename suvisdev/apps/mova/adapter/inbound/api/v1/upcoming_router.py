"""개봉예정작 라우터 — TMDB /movie/upcoming 얇은 프록시.

한국 개봉(region=KR) 고정. DB에 저장하지 않고 매 요청 시 TMDB에 위임 —
개봉 예정작은 소량·자주 안 바뀌어 실시간 프록시가 실용적. 프론트 캐시
(next: { revalidate: N })로 rate limit 보완.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.inbound.api.schemas.upcoming_schema import (
    UpcomingListSchema,
    UpcomingMovieSchema,
)
from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapterError
from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter

upcoming_router = APIRouter(prefix="/upcoming", tags=["mova-upcoming"])


def _get_catalog() -> TmdbCatalogAdapter:
    return TmdbCatalogAdapter(get_keymaker().tmdb_api_key)


@upcoming_router.get("", response_model=UpcomingListSchema)
async def list_upcoming(
    page: int = Query(1, ge=1, le=10),
    catalog: TmdbCatalogAdapter = Depends(_get_catalog),
) -> UpcomingListSchema:
    try:
        pairs = await catalog.fetch_upcoming_dated(page=page, region="KR")
    except TmdbAdapterError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    items = [
        UpcomingMovieSchema(
            tmdb_id=s.tmdb_id,
            slug=s.slug,
            title=s.title,
            release_year=s.release_year,
            release_date=release_date,
            rating=s.rating,
            poster_url=s.poster_url,
            genres=list(s.genres),
            overview=s.overview or "",
        )
        for s, release_date in pairs
    ]
    # 개봉일 오름차순(=먼저 개봉하는 것부터). 빈 문자열(=미정)은 뒤로.
    items.sort(key=lambda m: (m.release_date == "", m.release_date))
    return UpcomingListSchema(region="KR", items=items)
