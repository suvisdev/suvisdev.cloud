from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory
from viewer.adapter.outbound.orm.user_identity_orm import UserIdentity
from viewer.adapter.outbound.orm.user_orm import (
    get_viewer_user_profile,
    update_user_nickname,
    update_user_preferred_genres,
)
from viewer.app.dtos.profile_dto import ProfileDto
from viewer.app.ports.output.profile_repository import ProfileRepository


class ProfilePgRepository(ProfileRepository):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def get_profile(self, user_id: int) -> ProfileDto | None:
        try:
            raw = await get_viewer_user_profile(user_id)
        except ValueError:
            return None

        providers = await self._get_linked_providers(user_id)
        return ProfileDto(
            id=raw["id"],
            username=raw["username"],
            nickname=raw["nickname"],
            email=raw["email"],
            gender=raw["gender"],
            preferred_genres=raw["preferred_genres"],
            providers=providers,
        )

    async def update_nickname(self, user_id: int, nickname: str) -> ProfileDto | None:
        updated = await update_user_nickname(user_id, nickname)
        if not updated:
            return None
        return await self.get_profile(user_id)

    async def update_preferred_genres(
        self, user_id: int, genres: list[str]
    ) -> ProfileDto | None:
        updated = await update_user_preferred_genres(user_id, genres)
        if not updated:
            return None
        return await self.get_profile(user_id)

    async def _get_linked_providers(self, user_id: int) -> list[str]:
        if self._session is not None:
            return await self._query_providers(self._session, user_id)

        factory = get_viewer_session_factory()
        async with factory() as session:
            return await self._query_providers(session, user_id)

    async def _query_providers(self, session: AsyncSession, user_id: int) -> list[str]:
        rows = await session.execute(
            select(UserIdentity.provider).where(UserIdentity.user_id == user_id)
        )
        return [r[0] for r in rows.all()]
