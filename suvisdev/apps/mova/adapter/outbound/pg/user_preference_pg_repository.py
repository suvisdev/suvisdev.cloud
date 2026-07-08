"""사용자 취향 조회 PgRepository — UserPreferenceQueryPort 구현체."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.app.dtos.user_preference_dto import UserPreferenceDto
from mova.app.ports.output.user_preference_query_port import UserPreferenceQueryPort
from viewer.adapter.outbound.orm.user_orm import User


class UserPreferencePgRepository(UserPreferenceQueryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_preferences(self, user_id: int) -> UserPreferenceDto:
        row = (
            await self._session.execute(
                select(User.nickname, User.preferred_genres).where(User.id == user_id)
            )
        ).one_or_none()
        if not row:
            return UserPreferenceDto.empty()
        return UserPreferenceDto(
            nickname=row.nickname or None,
            preferred_genres=list(row.preferred_genres or []),
        )
