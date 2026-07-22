"""users/admins/user_identities/groups 테이블에 대한 read-only 조회.

테이블 소유권(DDL/Alembic 마이그레이션)은 100% apps/viewer에 남는다 — 여기 정의한
DeclarativeBase(AuthMirrorBase)는 절대 create_all/drop_all을 호출하지 않는다. 물리적으로는
viewer와 같은 DB에 붙는 core.matrix.grid_oracle_database_manager.get_viewer_session_factory()를
그대로 재사용해 조회만 한다.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from auth.rbac import Role
from core.matrix.grid_oracle_database_manager import get_viewer_session_factory


class AuthMirrorBase(DeclarativeBase):
    """auth 전용 조회 모델 베이스 — create_all/drop_all 호출 금지."""


class UserMirror(AuthMirrorBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))


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


def _verify_legacy_sha256_password(raw_password: str, stored_password_hash: str) -> bool:
    """apps/viewer의 login_pg_repository._verify_password와 동일한 규칙을 재현한다
    (sha256 다이제스트, 레거시 평문 폴백 포함). bcrypt로 "고치면" 기존 계정 로그인이
    깨지므로 절대 바꾸지 않는다 — 향후 auth 자체 신규 계정에는 별도 bcrypt 경로를 쓸 것."""
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
                if _verify_legacy_sha256_password(password, user.password_hash):
                    return User(user_id=user.id, username=user.username, roles=[Role(group_code)])
                return None

            row = (
                await session.execute(
                    select(AdminMirror, GroupMirror.code)
                    .join(GroupMirror, AdminMirror.group_id == GroupMirror.id)
                    .where(AdminMirror.username == username)
                )
            ).one_or_none()
            if row is not None:
                admin, group_code = row
                if _verify_legacy_sha256_password(password, admin.password_hash):
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
                return None  # 미연동 identity — 이번 라운드는 회원가입/자동연동 없음

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
