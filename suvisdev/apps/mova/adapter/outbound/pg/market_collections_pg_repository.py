"""컬렉션 PgRepository — CollectionRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_collections_orm import MovaCollection
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.market_collections_dto import (
    CollectionCreateCommand,
    CollectionDetailDto,
    CollectionListDto,
    CollectionListItemDto,
    CollectionMoviesDto,
)
from mova.app.dtos.studio_movies_dto import MovieListItemDto
from mova.app.ports.output.market_collections_repository import CollectionRepositoryPort
from mova.domain.entities.market_collections_entity import CollectionEntity

logger = logging.getLogger(__name__)


class CollectionsPgRepository(CollectionRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_entity_by_slug(self, slug: str) -> CollectionEntity | None:
        row = (
            await self._session.execute(select(MovaCollection).where(MovaCollection.slug == slug))
        ).scalar_one_or_none()
        if row is None:
            return None
        return CollectionEntity.from_orm(row)

    async def _movie_count_by_collection_id(self, collection_id: int) -> int:
        count_stmt = select(func.count(MovaMovie.id)).where(
            MovaMovie.collection_id == collection_id
        )
        return (await self._session.execute(count_stmt)).scalar_one()

    async def create(self, command: CollectionCreateCommand) -> CollectionDetailDto:
        row = MovaCollection(
            slug=str(command.slug),
            name=str(command.name),
            description=str(command.description),
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError(f"Collection slug already exists: {str(command.slug)}") from exc

        await self._session.refresh(row)
        entity = CollectionEntity.from_orm(row)
        return CollectionDetailDto.from_entity(entity, movie_count=0)

    async def list_collections(self, *, limit: int, offset: int) -> CollectionListDto:
        total = (await self._session.execute(select(func.count(MovaCollection.id)))).scalar_one()
        rows = (
            await self._session.execute(
                select(MovaCollection, func.count(MovaMovie.id))
                .outerjoin(MovaMovie, MovaMovie.collection_id == MovaCollection.id)
                .group_by(MovaCollection.id)
                .order_by(MovaCollection.name.asc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        items = [
            CollectionListItemDto.from_entity(
                CollectionEntity.from_orm(collection_row),
                movie_count=movie_count,
            )
            for collection_row, movie_count in rows
        ]

        return CollectionListDto(items=items, total=total, limit=limit, offset=offset)

    async def get_by_slug(self, slug: str) -> CollectionDetailDto | None:
        entity = await self._get_entity_by_slug(slug)
        if entity is None:
            return None

        movie_count = await self._movie_count_by_collection_id(entity.id)

        logger.debug(
            "[CollectionsPgRepository] get_by_slug=%s movie_count=%d",
            slug,
            movie_count,
        )
        return CollectionDetailDto.from_entity(entity, movie_count=movie_count)

    async def list_movies_by_slug(
        self,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> CollectionMoviesDto | None:
        entity = await self._get_entity_by_slug(slug)
        if entity is None:
            return None

        base_cond = MovaMovie.collection_id == entity.id
        count_stmt = select(func.count(MovaMovie.id)).where(base_cond)
        total = (await self._session.execute(count_stmt)).scalar_one()

        movies_stmt = (
            select(MovaMovie)
            .where(base_cond)
            .order_by(MovaMovie.release_year.desc(), MovaMovie.id.desc())
            .limit(limit)
            .offset(offset)
        )
        movies = list((await self._session.execute(movies_stmt)).scalars().all())

        logger.debug(
            "[CollectionsPgRepository] list_movies_by_slug=%s total=%d returned=%d",
            slug,
            total,
            len(movies),
        )
        return CollectionMoviesDto.from_entity_and_movies(
            entity,
            items=[MovieListItemDto.from_orm(movie) for movie in movies],
            total=total,
            limit=limit,
            offset=offset,
        )
