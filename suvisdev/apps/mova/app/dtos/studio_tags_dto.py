"""태그 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TagDto:
    id: int
    movie_id: int
    character_id: int | None
    tag_kind: str
    slug: str
    label: str
    description: str

    @classmethod
    def from_orm(cls, orm: object) -> TagDto:
        return cls(
            id=orm.id,
            movie_id=orm.movie_id,
            character_id=getattr(orm, "character_id", None),
            tag_kind=getattr(orm, "tag_kind", "mood"),
            slug=orm.slug,
            label=orm.label,
            description=getattr(orm, "description", "") or "",
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_tags_schema import TagSchema

        return TagSchema(
            id=self.id,
            movie_id=self.movie_id,
            character_id=self.character_id,
            tag_kind=self.tag_kind,
            slug=self.slug,
            label=self.label,
            description=self.description,
        )


@dataclass(frozen=True)
class TagGroupDto:
    """영화의 태그를 kind별로 묶은 DTO."""

    movie_id: int
    mood: list[TagDto]
    genre: list[TagDto]
    cast: list[TagDto]

    @classmethod
    def from_tag_list(cls, movie_id: int, tags: list[TagDto]) -> TagGroupDto:
        return cls(
            movie_id=movie_id,
            mood=[t for t in tags if t.tag_kind == "mood"],
            genre=[t for t in tags if t.tag_kind == "genre"],
            cast=[t for t in tags if t.tag_kind == "cast"],
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.studio_tags_schema import TagGroupSchema

        return TagGroupSchema(
            movie_id=self.movie_id,
            mood=[t.to_schema() for t in self.mood],
            genre=[t.to_schema() for t in self.genre],
            cast=[t.to_schema() for t in self.cast],
        )


if __name__ == "__main__":
    from types import SimpleNamespace

    mock = SimpleNamespace(
        id=1,
        movie_id=10,
        character_id=None,
        tag_kind="genre",
        slug="genre-sf",
        label="SF",
        description="",
    )
    dto = TagDto.from_orm(mock)
    assert dto.tag_kind == "genre"

    group = TagGroupDto.from_tag_list(10, [dto])
    assert len(group.genre) == 1
    assert len(group.mood) == 0
    print("studio_tags_dto OK")
