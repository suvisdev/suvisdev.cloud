"""태그 HTTP 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TagSchema(BaseModel):
    id: int
    movie_id: int
    character_id: int | None
    tag_kind: Literal["mood", "genre", "cast"]
    slug: str
    label: str
    description: str


class TagGroupSchema(BaseModel):
    """영화 태그를 kind별로 묶은 응답."""

    movie_id: int
    mood: list[TagSchema]
    genre: list[TagSchema]
    cast: list[TagSchema]


# 생성 요청 (import/admin 용)
class TagCreateSchema(BaseModel):
    movie_id: int
    label: str
    slug: str = ""
    description: str = ""
    character_id: int | None = None
    tag_kind: Literal["mood", "genre", "cast"] = "mood"
