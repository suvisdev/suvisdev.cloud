"""태그 도메인 Entity."""

from __future__ import annotations

from dataclasses import dataclass

from mova.domain.value_objects.studio_tags_vo import TagKind, TagSlug


@dataclass(frozen=True)
class TagEntity:
    """영화에 붙은 감성·장르·등장인물 키워드."""

    id: int
    movie_id: int
    character_id: int | None
    kind: TagKind
    slug: TagSlug
    label: str
    description: str

    @classmethod
    def from_orm(cls, orm: object) -> TagEntity:
        return cls(
            id=orm.id,
            movie_id=orm.movie_id,
            character_id=getattr(orm, "character_id", None),
            kind=TagKind.from_str(getattr(orm, "tag_kind", None)),
            slug=TagSlug(orm.slug),
            label=orm.label,
            description=getattr(orm, "description", "") or "",
        )

    def is_cast_tag(self) -> bool:
        return self.kind == TagKind.CAST

    def kind_label(self) -> str:
        return self.kind.label_ko()


if __name__ == "__main__":
    from types import SimpleNamespace

    mock = SimpleNamespace(
        id=1,
        movie_id=10,
        character_id=None,
        tag_kind="genre",
        slug="genre-sf",
        label="SF",
        description="SF 장르",
    )
    entity = TagEntity.from_orm(mock)
    assert entity.kind == TagKind.GENRE
    assert str(entity.slug) == "genre-sf"
    assert entity.kind_label() == "장르"
    assert not entity.is_cast_tag()
    print("studio_tags_entity OK")
