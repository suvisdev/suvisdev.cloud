from __future__ import annotations

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory
from viewer.adapter.outbound.orm.admin_orm import Admin
from viewer.adapter.outbound.orm.user_orm import User
from viewer.app.dtos.auth_command_dto import LoginResponseDto, LoginUserCommand
from viewer.app.ports.output.login_repository import LoginRepository

logger = logging.getLogger(__name__)


class LoginRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _verify_password(raw_password: str, stored_password_hash: str) -> bool:
    digest = hashlib.sha256(raw_password.encode("utf-8")).hexdigest()
    return stored_password_hash == raw_password or stored_password_hash == digest


class LoginPgRepository(LoginRepository):
    """Viewer 로그인 PostgreSQL 아웃바운드 어댑터 — users 우선, 없으면 admins."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def login_user(self, command: LoginUserCommand) -> LoginResponseDto:
        if self._session is not None:
            return await self._login_user(self._session, command)

        factory = get_viewer_session_factory()
        async with factory() as session:
            return await self._login_user(session, command)

    async def _login_user(self, session: AsyncSession, command: LoginUserCommand) -> LoginResponseDto:
        username = command.username
        password = command.password
        logger.info("[LoginPgRepository] login_user 진입 — username=%s", username)

        user = (
            await session.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()
        if user is not None and _verify_password(password, user.password_hash):
            logger.info("[LoginPgRepository] login_user 완료 — user_id=%s", user.id)
            return LoginResponseDto(user_id=user.id, username=user.username)

        admin = (
            await session.execute(select(Admin).where(Admin.username == username))
        ).scalar_one_or_none()
        if admin is not None and _verify_password(password, admin.password_hash):
            logger.info("[LoginPgRepository] login_user 완료 — admin_id=%s", admin.id)
            return LoginResponseDto(user_id=admin.id, username=admin.username)

        raise LoginRepositoryError(
            "아이디 또는 비밀번호가 올바르지 않습니다.",
            status_code=401,
        )
