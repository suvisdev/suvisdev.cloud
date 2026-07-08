"""컬렉션 DTO — 앱 레이어와 HTTP 레이어를 분리한다."""

from __future__ import annotations

from dataclasses import dataclass

from mova.app.dtos.studio_movies_dto import MovieListItemDto
from mova.domain.entities.market_collections_entity import CollectionEntity
from mova.domain.value_objects.market_collections_vo import (
    CollectionDescription,
    CollectionName,
    CollectionSlug,
)


@dataclass(frozen=True)
class CollectionDetailDto:
    id: int
    slug: str
    name: str
    description: str
    movie_count: int

    @classmethod
    def from_entity(cls, entity: CollectionEntity, *, movie_count: int) -> CollectionDetailDto:
        return cls(
            id=entity.id,
            slug=entity.path_segment(),
            name=entity.display_label(),
            description=str(entity.description),
            movie_count=movie_count,
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_collections_schema import (
            CollectionDetailSchema,
        )

        return CollectionDetailSchema(
            id=self.id,
            slug=self.slug,
            name=self.name,
            description=self.description,
            movie_count=self.movie_count,
        )


@dataclass(frozen=True)
class CollectionMoviesDto:
    collection_id: int
    collection_slug: str
    collection_name: str
    items: list[MovieListItemDto]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_entity_and_movies(
        cls,
        entity: CollectionEntity,
        *,
        items: list[MovieListItemDto],
        total: int,
        limit: int,
        offset: int,
    ) -> CollectionMoviesDto:
        return cls(
            collection_id=entity.id,
            collection_slug=entity.path_segment(),
            collection_name=entity.display_label(),
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_collections_schema import (
            CollectionMoviesSchema,
        )

        return CollectionMoviesSchema(
            collection_id=self.collection_id,
            collection_slug=self.collection_slug,
            collection_name=self.collection_name,
            items=[item.to_schema() for item in self.items],
            total=self.total,
            limit=self.limit,
            offset=self.offset,
        )


@dataclass(frozen=True)
class CollectionListItemDto:
    id: int
    slug: str
    name: str
    description: str
    movie_count: int

    @classmethod
    def from_entity(cls, entity: CollectionEntity, *, movie_count: int) -> CollectionListItemDto:
        return cls(
            id=entity.id,
            slug=entity.path_segment(),
            name=entity.display_label(),
            description=str(entity.description),
            movie_count=movie_count,
        )

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_collections_schema import (
            CollectionListItemSchema,
        )

        return CollectionListItemSchema(
            id=self.id,
            slug=self.slug,
            name=self.name,
            description=self.description,
            movie_count=self.movie_count,
        )


@dataclass(frozen=True)
class CollectionListDto:
    items: list[CollectionListItemDto]
    total: int
    limit: int
    offset: int

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_collections_schema import (
            CollectionListSchema,
        )

        return CollectionListSchema(
            items=[item.to_schema() for item in self.items],
            total=self.total,
            limit=self.limit,
            offset=self.offset,
        )


@dataclass(frozen=True)
class CollectionCreateCommand:
    slug: CollectionSlug
    name: CollectionName
    description: CollectionDescription

    @classmethod
    def from_payload(
        cls,
        *,
        slug: str,
        name: str,
        description: str | None,
    ) -> CollectionCreateCommand:
        return cls(
            slug=CollectionSlug(slug.strip()),
            name=CollectionName(name.strip()),
            description=CollectionDescription((description or "").strip()),
        )


if __name__ == "__main__":
    from types import SimpleNamespace

    entity = CollectionEntity.from_orm(
        SimpleNamespace(
            id=1,
            slug="dark-knight-trilogy",
            name="다크 나이트 트릴로지",
            description="배트맨 시리즈",
        )
    )
    detail = CollectionDetailDto.from_entity(entity, movie_count=3)
    assert detail.slug == "dark-knight-trilogy"
    assert detail.movie_count == 3
    print("market_collections_dto OK")
