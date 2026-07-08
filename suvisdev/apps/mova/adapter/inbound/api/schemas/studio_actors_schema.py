"""배우/감독 HTTP 요청/응답 Pydantic 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MovieInActorSchema(BaseModel):
    """배우 filmography 항목."""

    character_id: int
    movie_id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str
    genres: list[str]


class ActorDetailSchema(BaseModel):
    """배우/감독 상세 응답 (GET /actors/{id})."""

    id: int
    name: str
    role_type: Literal["director", "actor"]
    profile_photo_url: str
    filmography: list[MovieInActorSchema]


# 생성 요청 (import/admin 용)
class ActorCreateSchema(BaseModel):
    name: str
    role_type: Literal["director", "actor"] = "actor"
    profile_photo_url: str = ""
