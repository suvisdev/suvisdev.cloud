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
