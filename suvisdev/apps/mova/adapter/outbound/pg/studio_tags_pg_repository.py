"""태그 PgRepository — TagsRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_tags_orm import MovaTag
from mova.app.dtos.studio_tags_dto import TagDto, TagGroupDto
from mova.app.ports.output.studio_tags_repository import TagsRepositoryPort

logger = logging.getLogger(__name__)


class TagsPgRepository(TagsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_movie(self, movie_id: int) -> TagGroupDto:
        rows = await self._session.execute(
            select(MovaTag)
            .where(MovaTag.movie_id == movie_id)
            .order_by(MovaTag.tag_kind, MovaTag.label)
        )
        tags = [TagDto.from_orm(t) for t in rows.scalars().all()]

        logger.debug("[TagsPgRepository] movie_id=%d tags=%d", movie_id, len(tags))
        return TagGroupDto.from_tag_list(movie_id, tags)
