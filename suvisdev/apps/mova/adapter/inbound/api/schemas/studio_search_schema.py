"""검색 HTTP 스키마."""

from __future__ import annotations

from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.studio_movies_schema import MovieListItemSchema


class MovaSearchItemSchema(BaseModel):
    """채팅 프롬프트 태그 카탈로그용 — chat_prompt.py에서 사용."""

    id: str
    title: str
    year: str
    rating: float
    poster: str
    match_type: str


class SearchResultSchema(BaseModel):
    """GET /mova/search 응답 스키마."""

    query: str
    items: list[MovieListItemSchema]
    total: int
    limit: int
    offset: int
