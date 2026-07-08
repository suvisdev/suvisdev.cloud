"""@see suvisdev/_claude/ENTITY_RULE.md — 일반 사용자 계정 (`users`)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory
from viewer.adapter.outbound.orm.admin_orm import seed_admin_if_empty
from viewer.adapter.outbound.orm.base_orm import ViewerModel
from viewer.adapter.outbound.orm.group_orm import Group, get_group_id_by_code, seed_groups_if_empty
from viewer.app.dtos.role import UserRole
from viewer.app.dtos.user_profile import UserAgeGroup, UserGender


class User(ViewerModel):
    """일반 사용자 계정 + Mova 프로필 — `groups.code=user`."""

    __tablename__ = "users"

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gender: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=UserGender.UNDISCLOSED,
        index=True,
    )
    age_group: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=UserAgeGroup.UNDISCLOSED,
        index=True,
    )
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_genres: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    bio: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def viewer_user_exists(user_id: int) -> bool:
    factory = get_viewer_session_factory()
    async with factory() as session:
        result = await session.execute(select(User.id).where(User.id == user_id))
        return result.scalar_one_or_none() is not None


async def get_viewer_user_nicknames(user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}

    factory = get_viewer_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(User.id, User.nickname).where(User.id.in_(user_ids)),
        )
        return {row.id: row.nickname for row in result.all()}


async def get_viewer_user_profile(user_id: int) -> dict:
    factory = get_viewer_session_factory()
    async with factory() as session:
        row = (
            await session.execute(
                select(User, Group.code)
                .join(Group, User.group_id == Group.id)
                .where(User.id == user_id),
            )
        ).one_or_none()
        if row is None:
            raise ValueError(f"회원 ID {user_id}를 찾을 수 없습니다.")

        user, group_code = row
        return {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "group": group_code,
            "preferred_genres": list(user.preferred_genres or []),
            "gender": user.gender,
            "age_group": user.age_group,
        }


async def seed_viewer_if_empty() -> None:
    """Viewer 시드 — groups + admin."""
    await seed_groups_if_empty()
    await seed_admin_if_empty()


async def resolve_user_group_id() -> int:
    await seed_groups_if_empty()
    return await get_group_id_by_code(UserRole.USER)
