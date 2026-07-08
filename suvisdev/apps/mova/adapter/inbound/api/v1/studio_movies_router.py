"""영화 라우터 — GET /mova/movies, GET /mova/movies/{slug}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.studio_movies_schema import (
    MovieDetailSchema,
    MovieListSchema,
)
from mova.app.dtos.studio_movies_dto import MovieFilterQuery
from mova.app.ports.input.studio_movies_use_case import MoviesUseCase
from mova.dependencies.studio_movies_provider import get_movies_use_case

studio_movies_router = APIRouter(prefix="/movies", tags=["mova-movies"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@studio_movies_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="감독 (Director)")


@studio_movies_router.get("/{slug}", response_model=MovieDetailSchema)
async def get_movie_detail(
    slug: str,
    movies: MoviesUseCase = Depends(get_movies_use_case),
) -> MovieDetailSchema:
    """영화 상세 — 출연진·태그·플랫폼 포함."""
    dto = await movies.get_movie_detail(slug)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Movie '{slug}' not found")
    return dto.to_schema()


@studio_movies_router.get("", response_model=MovieListSchema)
async def list_movies(
    genre: str | None = Query(None, description="장르 필터 (예: SF, 코미디)"),
    release_year: str | None = Query(None, description="개봉 연도 (예: 2024)"),
    min_rating: float | None = Query(None, ge=0.0, le=5.0, description="최소 평점"),
    age_rating: str | None = Query(None, description="관람 등급 (전체|12세|15세|청불)"),
    platform: str | None = Query(None, description="플랫폼 (netflix|disney|watcha 등)"),
    sort: str = Query("latest", description="정렬 (latest|rating|popular)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    movies: MoviesUseCase = Depends(get_movies_use_case),
) -> MovieListSchema:
    """영화 탐색 — 장르·연도·평점·등급·플랫폼 필터 + 페이지네이션."""
    query = MovieFilterQuery(
        genre=genre,
        release_year=release_year,
        min_rating=min_rating,
        age_rating=age_rating,
        platform=platform,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    dto = await movies.list_movies(query)
    return dto.to_schema()
