from __future__ import annotations

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory
from viewer.adapter.outbound.orm.user_orm import User, resolve_user_group_id
from viewer.app.dtos.auth_command_dto import SignupCommand
from viewer.app.dtos.user_profile import UserAgeGroup, UserGender
from viewer.app.ports.output.signup_repository import SignupRepository

logger = logging.getLogger(__name__)


class SignupRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


class SignupPgRepository(SignupRepository):
    """viewer 회원가입 PostgreSQL 아웃바운드 어댑터."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def save_user(self, command: SignupCommand) -> int:
        if self._session is not None:
            return await self._save_user(self._session, command)

        factory = get_viewer_session_factory()
        async with factory() as session:
            user_id = await self._save_user(session, command)
            await session.commit()
            return user_id

    async def _save_user(self, session: AsyncSession, command: SignupCommand) -> int:
        user_payload = command.user
        username = user_payload.username
        logger.info("[SignupPgRepository] save_user 진입 — username=%s", username)

        user_group_id = await resolve_user_group_id()
        existing = await session.execute(
            select(User.id).where(User.username == username),
        )
        if existing.scalar_one_or_none() is not None:
            raise SignupRepositoryError("이미 사용 중인 아이디입니다.", status_code=409)

        user = User(
            group_id=user_group_id,
            username=username,
            password_hash=_hash_password(user_payload.password),
            nickname=user_payload.nickname,
            email=user_payload.email,
            gender=user_payload.gender or UserGender.UNDISCLOSED,
            age_group=user_payload.age_group or UserAgeGroup.UNDISCLOSED,
            birth_year=user_payload.birth_year,
            preferred_genres=list(user_payload.preferred_genres or []),
            bio=(user_payload.bio or "").strip(),
        )
        session.add(user)
        try:
            await session.flush()
            await session.refresh(user)
        except IntegrityError as exc:
            raise SignupRepositoryError("이미 사용 중인 아이디입니다.", status_code=409) from exc

        logger.info("[SignupPgRepository] save_user 완료 — user_id=%s", user.id)
        return user.id
