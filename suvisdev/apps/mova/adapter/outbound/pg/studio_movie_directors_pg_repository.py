"""영화↔감독 연결 PgRepository — MovieDirectorsRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_movie_directors_orm import MovaMovieDirector
from mova.app.dtos.studio_movie_directors_dto import MovieDirectorUpsertCommand
from mova.app.ports.output.studio_movie_directors_repository import MovieDirectorsRepositoryPort

logger = logging.getLogger(__name__)


class MovieDirectorsPgRepository(MovieDirectorsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_director(self, command: MovieDirectorUpsertCommand) -> int:
        existing_q = await self._session.execute(
            select(MovaMovieDirector).where(
                MovaMovieDirector.movie_id == command.movie_id,
                MovaMovieDirector.actor_id == command.actor_id,
            )
        )
        existing = existing_q.scalar_one_or_none()
        if existing is not None:
            return int(existing.id)

        director = MovaMovieDirector(movie_id=command.movie_id, actor_id=command.actor_id)
        self._session.add(director)
        await self._session.commit()
        await self._session.refresh(director)
        logger.debug(
            "[MovieDirectorsPgRepository] insert movie_id=%d actor_id=%d id=%d",
            command.movie_id,
            command.actor_id,
            director.id,
        )
        return int(director.id)
