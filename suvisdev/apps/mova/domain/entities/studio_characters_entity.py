"""영화↔배우 연결 Entity."""

from __future__ import annotations

from dataclasses import dataclass

from mova.domain.value_objects.studio_characters_vo import CharacterLink


@dataclass(frozen=True)
class CharacterEntity:
    """movies ↔ actors 중간 테이블 한 행.

    PK `id`와 비즈니스 키 `link(movie_id, actor_id)` 두 가지 식별자를 가진다.
    tags.character_id가 이 Entity의 id를 참조한다.
    """

    id: int
    link: CharacterLink

    @classmethod
    def from_orm(cls, orm: object) -> CharacterEntity:
        return cls(
            id=orm.id,
            link=CharacterLink(movie_id=orm.movie_id, actor_id=orm.actor_id),
        )

    @property
    def movie_id(self) -> int:
        return self.link.movie_id

    @property
    def actor_id(self) -> int:
        return self.link.actor_id


if __name__ == "__main__":
    from types import SimpleNamespace

    mock = SimpleNamespace(id=7, movie_id=1, actor_id=3)
    entity = CharacterEntity.from_orm(mock)
    assert entity.id == 7
    assert entity.movie_id == 1
    assert entity.actor_id == 3
    print("studio_characters_entity OK")
