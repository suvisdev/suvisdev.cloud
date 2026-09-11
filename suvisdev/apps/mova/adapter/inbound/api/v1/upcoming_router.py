"""개봉예정작 라우터 — TMDB /movie/upcoming 얇은 프록시.

한국 개봉(region=KR) 고정. DB에 저장하지 않고 매 요청 시 TMDB에 위임 —
개봉 예정작은 소량·자주 안 바뀌어 실시간 프록시가 실용적. 프론트 캐시
(next: { revalidate: N })로 rate limit 보완.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.adapter.inbound.api.schemas.upcoming_schema import (
    UpcomingActorSchema,
    UpcomingDetailSchema,
    UpcomingListSchema,
    UpcomingMovieSchema,
    UpcomingPlatformSchema,
)
from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapterError
from mova.adapter.outbound.http.tmdb_catalog_adapter import TmdbCatalogAdapter

upcoming_router = APIRouter(prefix="/upcoming", tags=["mova-upcoming"])


@lru_cache(maxsize=1)
def _get_catalog() -> TmdbCatalogAdapter:
    # 요청마다 새 인스턴스를 만들면 어댑터 내부 장르맵 캐시가 매번 재조회된다
    # (2026-09-11 리뷰) — 프로세스당 1개를 공유한다.
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
    # TMDB /movie/upcoming은 region=KR로도 이미 개봉된 항목이 섞여 오므로
    # 한국 기준 오늘 이전 날짜는 걸러낸다. 개봉일 미정(빈 문자열)은 남긴다.
    today_kr = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
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
        if not release_date or release_date >= today_kr
    ]
    # 개봉일 오름차순(=먼저 개봉하는 것부터). 빈 문자열(=미정)은 뒤로.
    items.sort(key=lambda m: (m.release_date == "", m.release_date))
    return UpcomingListSchema(region="KR", items=items)


@upcoming_router.get("/{tmdb_id}", response_model=UpcomingDetailSchema)
async def get_upcoming_detail(
    tmdb_id: int,
    catalog: TmdbCatalogAdapter = Depends(_get_catalog),
) -> UpcomingDetailSchema:
    """TMDB 영화 상세 — DB에 없는 개봉 예정작도 트레일러·출연진을 볼 수 있게 한다."""
    from mova.adapter.outbound.http.tmdb_adapter import build_image_url
    from mova.adapter.outbound.http.tmdb_mapper import (
        map_tmdb_row,
        tmdb_slug,
    )

    try:
        row = await catalog._client.fetch_movie_detail(tmdb_id)
    except TmdbAdapterError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    genre_map = await catalog._genres()
    poster = catalog._client.poster_url(str(row.get("poster_path") or ""))
    mapped = map_tmdb_row(row, genre_map=genre_map, poster_url=poster)
    if mapped is None:
        raise HTTPException(status_code=404, detail="TMDB에서 영화를 찾을 수 없습니다")

    actors: list[UpcomingActorSchema] = []
    credits = row.get("credits") or {}
    for d in credits.get("crew") or []:
        if d.get("job") == "Director" and d.get("name"):
            actors.append(
                UpcomingActorSchema(
                    name=d["name"],
                    role_type="director",
                    profile_photo_url=build_image_url(d.get("profile_path")),
                )
            )
    for c in (credits.get("cast") or [])[:10]:
        if c.get("name"):
            actors.append(
                UpcomingActorSchema(
                    name=c["name"],
                    role_type="actor",
                    profile_photo_url=build_image_url(c.get("profile_path")),
                    character_name=str(c.get("character") or "") or None,
                )
            )

    platforms = [
        UpcomingPlatformSchema(provider=str(p.get("provider", "")), url=p.get("url"))
        for p in mapped.platforms
        if p.get("provider")
    ]

    return UpcomingDetailSchema(
        id=mapped.tmdb_id,
        slug=tmdb_slug(mapped.tmdb_id),
        title=mapped.title,
        release_year=mapped.release_year,
        rating=mapped.rating,
        poster_url=mapped.poster_url,
        platforms=platforms,
        age_rating=mapped.age_rating,
        genres=list(mapped.genres),
        synopsis=mapped.overview or None,
        trailer_key=mapped.trailer_key,
        actors=actors,
        release_date=str(row.get("release_date") or ""),
    )
