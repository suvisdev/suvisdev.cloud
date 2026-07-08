"""컬렉션 도메인 Entity."""

from __future__ import annotations

from dataclasses import dataclass

from mova.domain.value_objects.market_collections_vo import (
    CollectionDescription,
    CollectionName,
    CollectionSlug,
)


@dataclass(frozen=True)
class CollectionEntity:
    """시리즈·컬렉션 도메인 객체. ORM·Pydantic에 의존하지 않는다."""

    id: int
    slug: CollectionSlug
    name: CollectionName
    description: CollectionDescription

    @classmethod
    def from_orm(cls, orm: object) -> CollectionEntity:
        return cls(
            id=orm.id,
            slug=CollectionSlug(orm.slug),
            name=CollectionName(orm.name),
            description=CollectionDescription(getattr(orm, "description", "") or ""),
        )

    def has_description(self) -> bool:
        return not self.description.is_empty()

    def display_label(self) -> str:
        """UI·로그용 표시 라벨."""
        return str(self.name)

    def path_segment(self) -> str:
        """URL 경로 세그먼트."""
        return str(self.slug)


if __name__ == "__main__":
    from types import SimpleNamespace

    mock = SimpleNamespace(
        id=1,
        slug="dark-knight-trilogy",
        name="다크 나이트 트릴로지",
        description="크리스토퍼 놀란 감독 배트맨 3부작",
    )
    entity = CollectionEntity.from_orm(mock)
    assert entity.path_segment() == "dark-knight-trilogy"
    assert entity.has_description()
    assert entity.display_label() == "다크 나이트 트릴로지"

    empty = CollectionEntity.from_orm(
        SimpleNamespace(id=2, slug="solo", name="단편", description="")
    )
    assert not empty.has_description()
    print("market_collections_entity OK")
