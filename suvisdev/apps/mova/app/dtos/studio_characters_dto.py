"""영화↔배우 연결 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterDto:
    """characters 행 기본 정보."""

    id: int
    movie_id: int
    actor_id: int

    @classmethod
    def from_orm(cls, orm: object) -> CharacterDto:
        return cls(id=orm.id, movie_id=orm.movie_id, actor_id=orm.actor_id)


@dataclass(frozen=True)
class CharacterWithActorDto:
    """characters + actors JOIN — 영화 기준 출연진 한 줄."""

    id: int
    movie_id: int
    actor_id: int
    actor_name: str
    role_type: str
    profile_photo_url: str

    @classmethod
    def from_orm(cls, char: object, actor: object) -> CharacterWithActorDto:
        return cls(
            id=char.id,
            movie_id=char.movie_id,
            actor_id=actor.id,
            actor_name=actor.name,
            role_type=actor.role_type or "actor",
            profile_photo_url=actor.profile_photo_url or "",
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_characters_schema import (
            CharacterWithActorSchema,
        )

        return CharacterWithActorSchema(
            id=self.id,
            movie_id=self.movie_id,
            actor_id=self.actor_id,
            actor_name=self.actor_name,
            role_type=self.role_type,
            profile_photo_url=self.profile_photo_url,
        )


@dataclass(frozen=True)
class CastListDto:
    """영화의 전체 출연진 목록."""

    movie_id: int
    cast: list[CharacterWithActorDto]

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_characters_schema import CastListSchema

        return CastListSchema(
            movie_id=self.movie_id,
            cast=[c.to_schema() for c in self.cast],
        )


if __name__ == "__main__":
    from types import SimpleNamespace

    mock_char = SimpleNamespace(id=10, movie_id=1, actor_id=5)
    mock_actor = SimpleNamespace(id=5, name="전지현", role_type="actor", profile_photo_url="")
    dto = CharacterWithActorDto.from_orm(mock_char, mock_actor)
    assert dto.actor_name == "전지현"
    assert dto.role_type == "actor"

    cast_dto = CastListDto(movie_id=1, cast=[dto])
    assert len(cast_dto.cast) == 1
    print("studio_characters_dto OK")
