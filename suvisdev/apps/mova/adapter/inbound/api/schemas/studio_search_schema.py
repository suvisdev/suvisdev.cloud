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
    # 2026-09-22: 프롬프트가 제목·연도만 주면 LLM이 작품 내용을 모른 채 제목으로
    # 추측한다("형사물"에 무관한 작품, 줄거리 왜곡 — v3 평가 패배 25건의 최다 사유).
    # 기본값을 둬서 이 스키마를 쓰는 다른 경로는 그대로 동작한다.
    genres: str = ""
    summary: str = ""
    # 2026-09-28: 추천 품질 하한(투표 30 미만은 뒤로) 판정용 — TMDB vote_count, 0=미수집
    vote_count: int = 0


class SearchResultSchema(BaseModel):
    """GET /mova/search 응답 스키마."""

    query: str
    items: list[MovieListItemSchema]
    total: int
    limit: int
    offset: int
