"""컬렉션 PgRepository — CollectionRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_collections_orm import MovaCollection
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.market_collections_dto import (
    CollectionAssignResultDto,
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

    async def assign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        entity = await self._get_entity_by_slug(slug)
        if entity is None:
            return None
        if not movie_ids:
            return CollectionAssignResultDto(
                collection_id=entity.id,
                collection_slug=str(entity.slug),
                affected=0,
                skipped_ids=[],
                moved_from_other_collection=0,
            )

        unique_ids = list(dict.fromkeys(int(m) for m in movie_ids))
        # 존재 확인 + 현재 collection_id 대조 (한 쿼리) — 부분 성공 응답 근거.
        existing_rows = (
            await self._session.execute(
                select(MovaMovie.id, MovaMovie.collection_id).where(MovaMovie.id.in_(unique_ids))
            )
        ).all()
        existing_map = {int(mid): (cid if cid is None else int(cid)) for mid, cid in existing_rows}
        found_ids = list(existing_map.keys())
        skipped_ids = [m for m in unique_ids if m not in existing_map]
        moved_from_other = sum(
            1 for m in found_ids if existing_map[m] is not None and existing_map[m] != entity.id
        )

        if found_ids:
            await self._session.execute(
                update(MovaMovie).where(MovaMovie.id.in_(found_ids)).values(collection_id=entity.id)
            )
            await self._session.commit()

        logger.info(
            "[CollectionsPgRepository] assign slug=%s affected=%d skipped=%d moved=%d",
            slug,
            len(found_ids),
            len(skipped_ids),
            moved_from_other,
        )
        return CollectionAssignResultDto(
            collection_id=entity.id,
            collection_slug=str(entity.slug),
            affected=len(found_ids),
            skipped_ids=skipped_ids,
            moved_from_other_collection=moved_from_other,
        )

    async def unassign_movies(
        self, slug: str, movie_ids: list[int]
    ) -> CollectionAssignResultDto | None:
        entity = await self._get_entity_by_slug(slug)
        if entity is None:
            return None
        if not movie_ids:
            return CollectionAssignResultDto(
                collection_id=entity.id,
                collection_slug=str(entity.slug),
                affected=0,
                skipped_ids=[],
                moved_from_other_collection=0,
            )

        unique_ids = list(dict.fromkeys(int(m) for m in movie_ids))
        # 이 컬렉션에 실제로 속한 movie_id만 골라 NULL 처리. 나머지는 skipped.
        in_collection_rows = (
            await self._session.execute(
                select(MovaMovie.id).where(
                    MovaMovie.id.in_(unique_ids), MovaMovie.collection_id == entity.id
                )
            )
        ).all()
        in_collection_ids = [int(r[0]) for r in in_collection_rows]
        skipped_ids = [m for m in unique_ids if m not in set(in_collection_ids)]

        if in_collection_ids:
            await self._session.execute(
                update(MovaMovie)
                .where(MovaMovie.id.in_(in_collection_ids))
                .values(collection_id=None)
            )
            await self._session.commit()

        logger.info(
            "[CollectionsPgRepository] unassign slug=%s affected=%d skipped=%d",
            slug,
            len(in_collection_ids),
            len(skipped_ids),
        )
        return CollectionAssignResultDto(
            collection_id=entity.id,
            collection_slug=str(entity.slug),
            affected=len(in_collection_ids),
            skipped_ids=skipped_ids,
            moved_from_other_collection=0,
        )
