"""영화↔배우 연결 PgRepository — CharactersRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter
from mova.app.dtos.studio_characters_dto import (
    CastListDto,
    CharacterUpsertCommand,
    CharacterWithActorDto,
)
from mova.app.ports.output.studio_characters_repository import CharactersRepositoryPort

logger = logging.getLogger(__name__)


class CharactersPgRepository(CharactersRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cast_by_movie(self, movie_id: int) -> CastListDto:
        rows = await self._session.execute(
            select(MovaCharacter, MovaActor)
            .join(MovaActor, MovaCharacter.actor_id == MovaActor.id)
            .where(MovaCharacter.movie_id == movie_id)
            .order_by(MovaActor.role_type, MovaActor.name)
        )
        pairs = rows.all()

        logger.debug("[CharactersPgRepository] movie_id=%d cast=%d", movie_id, len(pairs))
        return CastListDto(
            movie_id=movie_id,
            cast=[CharacterWithActorDto.from_orm(char, actor) for char, actor in pairs],
        )

    async def upsert_character(self, command: CharacterUpsertCommand) -> int:
        existing_q = await self._session.execute(
            select(MovaCharacter).where(
                MovaCharacter.movie_id == command.movie_id,
                MovaCharacter.actor_id == command.actor_id,
                MovaCharacter.character_name == command.character_name,
            )
        )
        existing = existing_q.scalar_one_or_none()
        if existing is None:
            character = MovaCharacter(
                movie_id=command.movie_id,
                actor_id=command.actor_id,
                character_name=command.character_name,
                billing_order=command.billing_order,
            )
            self._session.add(character)
            await self._session.commit()
            await self._session.refresh(character)
            logger.debug(
                "[CharactersPgRepository] insert movie_id=%d actor_id=%d id=%d",
                command.movie_id,
                command.actor_id,
                character.id,
            )
            return int(character.id)

        if command.billing_order is not None:
            existing.billing_order = command.billing_order
        await self._session.commit()
        await self._session.refresh(existing)
        logger.debug(
            "[CharactersPgRepository] update movie_id=%d actor_id=%d id=%d",
            command.movie_id,
            command.actor_id,
            existing.id,
        )
        return int(existing.id)
