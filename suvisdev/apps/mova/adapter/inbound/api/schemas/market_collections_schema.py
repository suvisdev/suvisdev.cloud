"""컬렉션 HTTP 요청/응답 Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mova.adapter.inbound.api.schemas.studio_movies_schema import MovieListItemSchema


class CollectionDetailSchema(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    movie_count: int = Field(ge=0, description="이 컬렉션에 속한 영화 수")


class CollectionMoviesSchema(BaseModel):
    collection_id: int
    collection_slug: str
    collection_name: str
    items: list[MovieListItemSchema]
    total: int
    limit: int
    offset: int


class CollectionCreateSchema(BaseModel):
    slug: str
    name: str
    description: str = ""


class CollectionListItemSchema(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    movie_count: int


class CollectionListSchema(BaseModel):
    items: list[CollectionListItemSchema]
    total: int
    limit: int
    offset: int


class CollectionMoviesMutationRequest(BaseModel):
    """PATCH/DELETE /collections/{slug}/movies 요청 본문."""

    movie_ids: list[int] = Field(min_length=1, max_length=500)


class CollectionAssignResultSchema(BaseModel):
    """배정/해제 결과. one-to-many 시맨틱상 부분 성공을 명시적으로 응답한다."""

    collection_id: int
    collection_slug: str
    affected: int = Field(ge=0, description="배정: SET된 영화 수 · 해제: NULL 처리된 영화 수")
    skipped_ids: list[int] = Field(
        description="배정: DB에 없는 movie_id · 해제: 이 컬렉션에 없던 movie_id"
    )
    moved_from_other_collection: int = Field(
        ge=0, description="배정 전용 — 다른 컬렉션에서 이동돼 온 영화 수(덮어쓰기 관측성). 해제 시 0"
    )
