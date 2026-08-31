"""users/admins/user_identities/groups 테이블 접근.

테이블 소유권(DDL/Alembic 마이그레이션)은 100% apps/viewer에 남는다 — 여기 정의한
DeclarativeBase(AuthMirrorBase)는 절대 create_all/drop_all을 호출하지 않는다. 물리적으로는
viewer와 같은 DB에 붙는 core.matrix.grid_oracle_database_manager.get_viewer_session_factory()를
그대로 재사용한다.

signup(신규)은 users 테이블에 INSERT하므로 조회 전용이 아니게 됐다 — 다만 DDL은
여전히 건드리지 않는다(테이블 자체는 이미 viewer가 만들어둔 것을 그대로 씀).
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

import bcrypt
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from auth.rbac import Role
from core.matrix.grid_oracle_database_manager import get_viewer_session_factory

_DEFAULT_GENDER = "undisclosed"  # viewer.app.dtos.user_profile.UserGender.UNDISCLOSED와 동일한 값


class AuthMirrorBase(DeclarativeBase):
    """auth 전용 모델 베이스 — create_all/drop_all 호출 금지(DDL은 viewer 소유)."""


class UserMirror(AuthMirrorBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    # signup(INSERT)에 필요 — users 테이블에 NOT NULL 제약이 있어 반드시 채워야 함.
    nickname: Mapped[str] = mapped_column(String(50))
    gender: Mapped[str] = mapped_column(String(16), default=_DEFAULT_GENDER)
    preferred_genres: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    bio: Mapped[str] = mapped_column(String(255), default="")


class AdminMirror(AuthMirrorBase):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))


class UserIdentityMirror(AuthMirrorBase):
    __tablename__ = "user_identities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(16))
    provider_user_id: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class GroupMirror(AuthMirrorBase):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32))


@dataclass
class User:
    """auth 게이트웨이가 다루는 사용자 값 — 동등성 기준: user_id(비즈니스 키)."""

    user_id: int
    username: str
    roles: list[Role]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.user_id == other.user_id

    def __hash__(self) -> int:
        return hash(self.user_id)

    def role_values(self) -> list[str]:
        return [role.value for role in self.roles]


class EmailAlreadyExists(Exception):
    """signup 시 동일 email의 users row가 이미 존재함(409)."""


def _hash_password(raw_password: str) -> str:
    """auth 자체 신규 계정(signup) 전용 — bcrypt."""
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(raw_password: str, stored_password_hash: str) -> bool:
    """bcrypt(신규 signup 계정)와 레거시 sha256/평문(기존 viewer 계정) 둘 다 검증.

    apps/auth의 signup으로 만든 계정은 bcrypt 해시라 앞부분이 "$2b$"(bcrypt 식별자)로
    시작한다 — 그 경우만 bcrypt로 검증하고, 나머지는 기존 viewer
    login_pg_repository._verify_password와 동일한 규칙(sha256 다이제스트, 레거시
    평문 폴백)을 그대로 재현한다. 레거시 계정은 마이그레이션하지 않는다."""
    if stored_password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        return bcrypt.checkpw(raw_password.encode("utf-8"), stored_password_hash.encode("utf-8"))
    digest = hashlib.sha256(raw_password.encode("utf-8")).hexdigest()
    return stored_password_hash == raw_password or stored_password_hash == digest


class UserRepository:
    async def find_by_credentials(self, username: str, password: str) -> User | None:
        factory = get_viewer_session_factory()
        async with factory() as session:
            row = (
                await session.execute(
                    select(UserMirror, GroupMirror.code)
                    .join(GroupMirror, UserMirror.group_id == GroupMirror.id)
                    .where(UserMirror.username == username)
                )
            ).one_or_none()
            if row is not None:
                user, group_code = row
                if _verify_password(password, user.password_hash):
                    return User(user_id=user.id, username=user.username, roles=[Role(group_code)])
                return None

            admin_row = (
                await session.execute(
                    select(AdminMirror, GroupMirror.code)
                    .join(GroupMirror, AdminMirror.group_id == GroupMirror.id)
                    .where(AdminMirror.username == username)
                )
            ).one_or_none()
            if admin_row is not None:
                admin, group_code = admin_row
                if _verify_password(password, admin.password_hash):
                    return User(user_id=admin.id, username=admin.username, roles=[Role(group_code)])
            return None

    async def find_by_oauth_identity(self, provider: str, provider_user_id: str) -> User | None:
        factory = get_viewer_session_factory()
        async with factory() as session:
            identity = (
                await session.execute(
                    select(UserIdentityMirror).where(
                        UserIdentityMirror.provider == provider,
                        UserIdentityMirror.provider_user_id == provider_user_id,
                    )
                )
            ).scalar_one_or_none()
            if identity is None:
                return None  # 미연동 identity — OAuth는 여전히 회원가입/자동연동 없음

            row = (
                await session.execute(
                    select(UserMirror, GroupMirror.code)
                    .join(GroupMirror, UserMirror.group_id == GroupMirror.id)
                    .where(UserMirror.id == identity.user_id)
                )
            ).one_or_none()
            if row is None:
                return None
            user, group_code = row
            return User(user_id=user.id, username=user.username, roles=[Role(group_code)])

    async def create_user(self, *, email: str, password: str, username: str) -> User:
        """비밀번호 회원가입 — users 테이블에 INSERT(bcrypt 해시). email 중복이면
        EmailAlreadyExists. 새로 만든 계정은 항상 Role.USER."""
        factory = get_viewer_session_factory()
        async with factory() as session:
            existing = (
                await session.execute(select(UserMirror.id).where(UserMirror.email == email))
            ).scalar_one_or_none()
            if existing is not None:
                raise EmailAlreadyExists(f"이미 가입된 이메일입니다: {email}")

            group_id = (
                await session.execute(select(GroupMirror.id).where(GroupMirror.code == "user"))
            ).scalar_one_or_none()
            if group_id is None:
                raise RuntimeError(
                    "groups 테이블에 'user' 코드가 없습니다 — viewer 시드 확인 필요."
                )

            new_user = UserMirror(
                group_id=group_id,
                username=username,
                password_hash=_hash_password(password),
                email=email,
                nickname=username,
                gender=_DEFAULT_GENDER,
                preferred_genres=[],
                bio="",
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return User(user_id=new_user.id, username=new_user.username, roles=[Role.USER])

    async def find_or_create_by_kakao(
        self, *, provider_user_id: str, email: str | None, nickname: str | None
    ) -> User:
        """카카오 모바일 로그인 전용 upsert. 웹 OAuth(find_by_oauth_identity)는 미연동
        identity를 자동 생성하지 않지만(OAuthIdentityNotLinked — viewer에서 먼저 연동
        필요), 모바일은 첫 로그인 시점에 바로 계정을 만든다(하네스 R2)."""
        factory = get_viewer_session_factory()
        async with factory() as session:
            identity = (
                await session.execute(
                    select(UserIdentityMirror).where(
                        UserIdentityMirror.provider == "kakao",
                        UserIdentityMirror.provider_user_id == provider_user_id,
                    )
                )
            ).scalar_one_or_none()

            if identity is not None:
                row = (
                    await session.execute(
                        select(UserMirror, GroupMirror.code)
                        .join(GroupMirror, UserMirror.group_id == GroupMirror.id)
                        .where(UserMirror.id == identity.user_id)
                    )
                ).one_or_none()
                if row is not None:
                    user, group_code = row
                    return User(user_id=user.id, username=user.username, roles=[Role(group_code)])

            group_id = (
                await session.execute(select(GroupMirror.id).where(GroupMirror.code == "user"))
            ).scalar_one_or_none()
            if group_id is None:
                raise RuntimeError(
                    "groups 테이블에 'user' 코드가 없습니다 — viewer 시드 확인 필요."
                )

            # 카카오는 email/닉네임 동의 스코프가 없으면 값을 안 줄 수 있다 — users
            # 테이블 NOT NULL 제약을 만족시키기 위한 폴백. password_hash는 OAuth 전용
            # 계정이라 실제로 쓰이지 않으므로 무작위 값을 해시해 채운다.
            resolved_nickname = nickname or f"kakao_{provider_user_id}"
            new_user = UserMirror(
                group_id=group_id,
                username=resolved_nickname,
                password_hash=_hash_password(secrets.token_urlsafe(32)),
                email=email or f"kakao_{provider_user_id}@kakao.local",
                nickname=resolved_nickname,
                gender=_DEFAULT_GENDER,
                preferred_genres=[],
                bio="",
            )
            session.add(new_user)
            await session.flush()

            session.add(
                UserIdentityMirror(
                    user_id=new_user.id,
                    provider="kakao",
                    provider_user_id=provider_user_id,
                    email=email,
                )
            )
            await session.commit()
            await session.refresh(new_user)
            return User(user_id=new_user.id, username=new_user.username, roles=[Role.USER])
