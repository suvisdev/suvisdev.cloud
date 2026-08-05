"""배우 PgRepository — ActorsRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.studio_actors_dto import ActorDetailDto, ActorUpsertCommand
from mova.app.ports.output.studio_actors_repository import ActorsRepositoryPort

logger = logging.getLogger(__name__)


class ActorsPgRepository(ActorsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, actor_id: int) -> ActorDetailDto | None:
        actor_q = await self._session.execute(select(MovaActor).where(MovaActor.id == actor_id))
        actor = actor_q.scalar_one_or_none()
        if not actor:
            return None

        movie_q = await self._session.execute(
            select(MovaCharacter, MovaMovie)
            .join(MovaMovie, MovaCharacter.movie_id == MovaMovie.id)
            .where(MovaCharacter.actor_id == actor_id)
            .order_by(MovaMovie.release_year.desc(), MovaMovie.id.desc())
        )
        movie_rows = movie_q.all()

        logger.debug("[ActorsPgRepository] get_by_id=%d filmography=%d", actor_id, len(movie_rows))
        return ActorDetailDto.from_orm(actor, movie_rows)

    async def upsert_actor(self, command: ActorUpsertCommand) -> int:
        existing_q = await self._session.execute(
            select(MovaActor).where(MovaActor.tmdb_person_id == command.tmdb_person_id)
        )
        existing = existing_q.scalar_one_or_none()
        if existing is None:
            actor = MovaActor(
                tmdb_person_id=command.tmdb_person_id,
                name=command.name,
                role_type=command.role_type,
                profile_photo_url=command.profile_photo_url,
            )
            self._session.add(actor)
            await self._session.commit()
            await self._session.refresh(actor)
            logger.debug(
                "[ActorsPgRepository] insert tmdb_person_id=%d id=%d",
                command.tmdb_person_id,
                actor.id,
            )
            return int(actor.id)

        existing.name = command.name
        existing.role_type = command.role_type
        if command.profile_photo_url:
            existing.profile_photo_url = command.profile_photo_url
        await self._session.commit()
        await self._session.refresh(existing)
        logger.debug(
            "[ActorsPgRepository] update tmdb_person_id=%d id=%d",
            command.tmdb_person_id,
            existing.id,
        )
        return int(existing.id)

    async def rollback(self) -> None:
        await self._session.rollback()
