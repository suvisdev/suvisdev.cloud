from __future__ import annotations

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gildle.adapter.outbound.orm.push_token_orm import PushTokenOrm
from gildle.app.ports.output.push_token_repository import PushTokenRepositoryPort
from gildle.domain.entities.push_token_entity import PushToken


class PushTokenPgRepository(PushTokenRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, token: PushToken) -> PushToken:
        row = (
            await self._session.execute(
                select(PushTokenOrm).where(PushTokenOrm.token == token.token)
            )
        ).scalar_one_or_none()
        if row is None:
            row = PushTokenOrm(user_id=token.user_id, token=token.token, platform=token.platform)
            self._session.add(row)
        else:
            row.user_id = token.user_id
            row.platform = token.platform
        await self._session.flush()
        await self._session.commit()
        return PushToken(id=row.id, user_id=row.user_id, token=row.token, platform=row.platform)

    async def delete(self, user_id: int, token: str) -> None:
        await self._session.execute(
            sa_delete(PushTokenOrm).where(
                PushTokenOrm.user_id == user_id, PushTokenOrm.token == token
            )
        )
        await self._session.commit()
