from __future__ import annotations

import hashlib
import logging
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory
from viewer.adapter.outbound.orm.user_identity_orm import UserIdentity
from viewer.adapter.outbound.orm.user_orm import User, resolve_user_group_id
from viewer.app.dtos.auth_command_dto import LoginResponseDto
from viewer.app.dtos.oauth_dto import OAuthIdentity
from viewer.app.dtos.user_profile import UserGender
from viewer.app.ports.output.oauth_identity_repository import OAuthIdentityRepository

logger = logging.getLogger(__name__)


def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


class OAuthIdentityPgRepository(OAuthIdentityRepository):
    """OAuth 신원을 users/user_identities에 연결(또는 신규 생성)하는 PostgreSQL 어댑터."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def find_linked_user(self, identity: OAuthIdentity) -> LoginResponseDto | None:
        if self._session is not None:
            return await self._find_linked_user(self._session, identity)

        factory = get_viewer_session_factory()
        async with factory() as session:
            return await self._find_linked_user(session, identity)

    async def create_linked_user(self, identity: OAuthIdentity) -> LoginResponseDto:
        if self._session is not None:
            return await self._create_linked_user(self._session, identity)

        factory = get_viewer_session_factory()
        async with factory() as session:
            result = await self._create_linked_user(session, identity)
            await session.commit()
            return result

    async def _find_linked_user(
        self, session: AsyncSession, identity: OAuthIdentity
    ) -> LoginResponseDto | None:
        linked = (
            await session.execute(
                select(UserIdentity).where(
                    UserIdentity.provider == identity.provider,
                    UserIdentity.provider_user_id == identity.provider_user_id,
                )
            )
        ).scalar_one_or_none()
        if linked is None:
            return None

        user = await session.get(User, linked.user_id)
        if user is None:
            raise ValueError(
                f"user_identities가 존재하지 않는 user_id={linked.user_id}를 참조합니다."
            )
        logger.info(
            "[OAuthIdentityPgRepository] %s 기존 연결 — user_id=%s",
            identity.provider, user.id,
        )
        return LoginResponseDto(user_id=user.id, username=user.username, nickname=user.nickname)

    async def _create_linked_user(
        self, session: AsyncSession, identity: OAuthIdentity
    ) -> LoginResponseDto:
        user = await self._find_or_create_local_user(session, identity)
        session.add(
            UserIdentity(
                user_id=user.id,
                provider=identity.provider,
                provider_user_id=identity.provider_user_id,
                email=identity.email,
            )
        )
        await session.flush()
        logger.info(
            "[OAuthIdentityPgRepository] %s 신규 연결(약관 동의 완료) — user_id=%s",
            identity.provider, user.id,
        )
        return LoginResponseDto(user_id=user.id, username=user.username, nickname=user.nickname)

    async def _find_or_create_local_user(
        self, session: AsyncSession, identity: OAuthIdentity
    ) -> User:
        # 이메일 검증이 확인된 경우에만 기존 계정에 자동 연결한다 — 검증 안 된
        # 이메일로 연결을 허용하면 타인의 계정에 무단으로 연결될 위험이 있다.
        if identity.email and identity.email_verified:
            # users.email에는 unique 제약이 없어(기존 스키마) 여러 건이 있을 수
            # 있다 — 가장 먼저 만들어진 계정 하나로 결정적으로 연결한다.
            existing = (
                await session.execute(
                    select(User).where(User.email == identity.email).order_by(User.id).limit(1)
                )
            ).scalars().first()
            if existing is not None:
                return existing

        user_group_id = await resolve_user_group_id()
        username = await self._unique_username(session, identity)
        user = User(
            group_id=user_group_id,
            username=username,
            # OAuth 전용 계정 — 비밀번호 로그인은 쓸 수 없게 무작위 값으로 채운다
            # (password_hash가 NOT NULL이라 비워둘 수 없음).
            password_hash=_hash_password(secrets.token_urlsafe(32)),
            nickname=(identity.name or username)[:50],
            email=identity.email or f"{username}@{identity.provider}.oauth.suvisdev.cloud",
            gender=UserGender.UNDISCLOSED,
            birth_year=None,
            preferred_genres=[],
            bio="",
        )
        session.add(user)
        try:
            await session.flush()
            await session.refresh(user)
        except IntegrityError as exc:
            raise ValueError("OAuth 사용자 생성 중 아이디 충돌이 발생했습니다.") from exc
        return user

    async def _unique_username(self, session: AsyncSession, identity: OAuthIdentity) -> str:
        base = (identity.email or "").split("@")[0]
        base = "".join(ch for ch in base if ch.isalnum())[:30] or f"{identity.provider}user"
        candidate = f"{base}_{identity.provider}"
        while (
            await session.execute(select(User.id).where(User.username == candidate))
        ).scalar_one_or_none() is not None:
            candidate = f"{base}_{identity.provider}_{secrets.token_hex(3)}"
        return candidate
