"""영화↔배우 연결 HTTP 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CharacterWithActorSchema(BaseModel):
    """출연진 한 줄 — characters + actors JOIN."""

    id: int
    movie_id: int
    actor_id: int
    actor_name: str
    role_type: Literal["director", "actor"]
    profile_photo_url: str


class CastListSchema(BaseModel):
    """영화 출연진 전체 목록 응답."""

    movie_id: int
    cast: list[CharacterWithActorSchema]


# 연결 생성 요청 (import/admin 용)
class CharacterLinkCreateSchema(BaseModel):
    movie_id: int
    actor_id: int
