from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viewer.adapter.outbound.orm.user_identity_orm import UserIdentity
from viewer.adapter.outbound.orm.user_orm import User
from viewer.app.dtos.admin_users_dto import UserAdminDto
from viewer.app.ports.output.admin_users_repository import AdminUsersRepository

_ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}


class AdminUsersPgRepository(AdminUsersRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_users(self) -> list[UserAdminDto]:
        users_result = await self._session.execute(
            select(User.id, User.email, User.nickname, User.created_at).order_by(
                User.created_at.desc()
            )
        )
        users = users_result.all()
        if not users:
            return []

        user_ids = [u.id for u in users]
        identities_result = await self._session.execute(
            select(UserIdentity.user_id, UserIdentity.provider).where(
                UserIdentity.user_id.in_(user_ids)
            )
        )
        providers_map: dict[int, list[str]] = {}
        for row in identities_result.all():
            providers_map.setdefault(row.user_id, []).append(row.provider)

        return [
            UserAdminDto(
                id=u.id,
                email=u.email,
                nickname=u.nickname,
                role="admin" if u.email.lower() in _ADMIN_EMAILS else "user",
                providers=providers_map.get(u.id, []),
                created_at=u.created_at,
            )
            for u in users
        ]
